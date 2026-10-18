---
name: node-background-jobs
description: "Background work in a v1rus Node service with BullMQ: deciding what leaves the request path at all, queues and typed job payloads that carry ids rather than whole objects and are validated on the way in, at-least-once delivery making every handler idempotent, retries with exponential backoff and a dead-letter destination instead of infinite requeues, the transactional outbox for the write-then-publish problem that a publish inside a transaction does not solve, concurrency and rate limits, long jobs that block the event loop or lose their lock, scheduled and repeatable jobs with a single-instance guard, correlation ids carried into jobs, and draining workers on shutdown. Load when adding a queue or a job, writing a processor, sending an email or webhook after a write, scheduling recurring work, or diagnosing duplicated, stuck or lost jobs."
---

# Background Jobs and Queues

**BullMQ on Redis** is the default (see the plugin README design notes). The reasoning below holds
for any at-least-once queue; the API names are BullMQ's.

## What belongs in a job

Move work off the request path when it is slow, retryable, or not needed for the response: sending
mail, calling a third party, generating a document, syncing a downstream system, anything CPU-bound
(`node-runtime`). Keep it in the request when the caller needs the result or the failure.

The tell that something should have been a job: a handler whose p99 is dominated by an external call
it does not use the result of.

## Job payloads

```ts
export const SEND_INVOICE = 'invoice.send';
export const SendInvoicePayload = z.object({
  invoiceId: z.string().uuid(),
  correlationId: z.string(),
});
```

- **Pass ids, not objects.** The payload is serialised and may sit in Redis for hours: an embedded
  entity is stale by the time it runs, and it duplicates data that the handler should re-read under
  the current rules. Payloads also count against Redis memory.
- **Validate the payload in the processor**, on the same terms as an HTTP body. A queue is an I/O
  boundary: the payload may have been written by an older deploy, by a retry of a job enqueued
  before a schema change, or by hand during an incident.
- Carry the **correlation id** in the payload and re-open the request context at the top of the
  processor, so the job's logs join the request that caused it (`node-observability`).
- Never put a secret or PII in a payload — it is stored, and it is visible in every queue dashboard.

## Idempotency is not optional

Every at-least-once queue delivers a job twice eventually: a worker dies after the side effect and
before the ack, a retry fires on a timeout that actually succeeded, a deploy interrupts mid-job.
**Assume every handler runs more than once.**

- Make the effect naturally idempotent where you can: `upsert` rather than `create`, "set status to
  X" rather than "increment".
- Where the effect is external and not idempotent (charging a card, sending mail), use an
  idempotency key the third party honours, or record a `processed_jobs` row in the same transaction
  as the local effect and check it first.
- Use a deterministic `jobId` (derived from the entity and the operation) when you want BullMQ to
  deduplicate the *enqueue* — two requests producing the same job produce one job.
- A handler that reads state, decides, and writes must re-check the precondition inside the
  transaction. "I already decided when I enqueued this" is false by the time it runs.

## Retries and failure

```ts
{ attempts: 5, backoff: { type: 'exponential', delay: 1_000 }, removeOnComplete: 1_000, removeOnFail: false }
```

- **Exponential backoff with jitter**, and a finite `attempts`. Infinite retries against a broken
  downstream is a self-inflicted denial of service against it — and the queue fills behind it.
- Distinguish **retryable** from **terminal**. A 5xx or a timeout is retryable; a 4xx from a
  validation failure, or a missing entity, will fail identically forever — fail it immediately to
  the dead-letter rather than burning five attempts.
- Failures land somewhere a human looks: a failed-jobs set with retention, an alert on its depth,
  and enough context in the job log to replay it. A job that fails into nothing is a silently
  dropped business outcome.
- `removeOnComplete` is bounded — an unbounded completed set is a slow Redis memory leak.

## Write-then-publish: use an outbox

The common bug:

```ts
await this.prisma.$transaction(async (tx) => {
  await tx.order.update({ where: { id }, data: { status: 'PAID' } });
  await this.queue.add(SEND_INVOICE, { invoiceId });   // wrong: not in the transaction
});
```

Redis is not in the database transaction. If the transaction rolls back after the enqueue, the job
runs against an order that was never paid; if the process dies between commit and enqueue, the
invoice is never sent. Both happen.

**The outbox:** write the intent to an `outbox` table **in the same transaction** as the state
change, and have a relay (a poller, or a change-data-capture consumer) publish rows to the queue and
mark them sent. Publishing then inherits the transaction's atomicity, and the relay's at-least-once
delivery is covered by the handler idempotency you already have.

When the effect is genuinely allowed to be lost, publishing **after** commit — outside the
transaction — is acceptable, and that decision is written down rather than assumed. What is never
acceptable is a publish *inside* the transaction: it holds a pooled connection across a network call
(`node-persistence`).

## Concurrency, rate limits, and the event loop

- Worker `concurrency` is how many jobs one process runs at once — and they share the single event
  loop. Ten concurrent jobs each doing sync CPU work is one blocked process.
- A **long job blocks its own lock renewal** if it is synchronous: BullMQ renews the lock on the
  event loop, so a CPU-bound job that never yields loses the lock, and the queue hands the job to a
  second worker — which is how one job runs twice. Yield, chunk the work, or run it in a worker
  thread.
- Rate-limit at the queue for a downstream with a quota (`limiter: { max, duration }`), rather than
  sleeping inside the handler, which just holds a worker slot.
- Size worker concurrency against the **database pool**: N workers × M concurrency all querying at
  once is N×M connections wanted from a pool that has fewer.

## Scheduling

- Repeatable jobs are defined in one place at startup, and the definition is **removed and re-added**
  when its cron changes — a changed cron with the same key leaves the old schedule registered.
- A cron job in a service with three replicas fires three times unless the queue deduplicates by
  key. BullMQ's repeatable jobs do; an in-process `@Cron` from `@nestjs/schedule` does **not** —
  with `@Cron` you need a leader election or a distributed lock, and that is a good reason to prefer
  the queue.
- Specify the timezone explicitly. A cron expression with no timezone runs against whatever the
  container's is, which is UTC in production and the developer's in testing.

## Deployment shape and shutdown

- **Prefer a separate worker process** from the API in anything but the smallest service: the API's
  latency stops depending on a batch job's CPU, and the two scale independently. Same image,
  different entrypoint, same modules.
- On SIGTERM a worker stops taking new jobs, finishes what it holds within the drain timeout, and
  closes its connections **before** the database is closed (`node-runtime`). Jobs that do not finish
  are returned to the queue — which is exactly why the handlers are idempotent.
- Instrument queue depth, job duration, and failure rate; a queue that is growing is the earliest
  signal that something downstream broke (`node-observability`).
