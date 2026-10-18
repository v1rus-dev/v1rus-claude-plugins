# android CLI commands

Docs: https://developer.android.com/tools/agents/android-cli. Behaviour below was observed on a 1.0 release; re-check `--help` if a flag is rejected.

| Task | Command |
|---|---|
| Search Android / Jetpack / Compose / AGP / SDK docs | `android docs search "<query>"` |
| Fetch a doc page (url from search) | `android docs fetch <url>` |
| Project metadata (build targets, APK output paths) | `android describe --project_dir=.` |
| Live device UI tree | `android layout --pretty` |
| UI tree diff after an action | `android layout -d` |
| Device screenshot | `android screen capture -o <path>` |
| Visual targeting without a stable id | `android screen capture -a` then `android screen resolve --screenshot <p> --string "tap on #3"` |
| List AVDs | `android emulator list` |
| Start / stop / remove an AVD | `android emulator start <avd> [--cold]` / `stop` / `remove` |
| Create an AVD from a profile | `android emulator create <profile>` (`--list-profiles` to enumerate) |
| SDK packages | `android sdk install|update|remove|list` |
| Deploy a built APK | `android run --apks <p1,p2> --activity <name> --device <id> [--debug]` (`--type` is the component type, not the build variant) |
| Environment info | `android info` |
| New project scaffold (explicit request only) | `android create [template] --name <n> --minSdk <v>` |
| List / find bundled skills | `android skills list` / `android skills find <keyword>` |
| Read a bundled skill (no install) | Read `~/.android/cli/skills/**/<skill-name>/SKILL.md` |

## Never automatic
- `android init`, `android skills add` (they register skills in routing and duplicate existing ones): only on explicit request.
- `android update`: mention a new version once per session and ask first.

## Fallback when the CLI is missing
Tell the user once ("Android CLI not installed; install per the docs or proceeding with fallbacks"), then:

| Task | Fallback |
|---|---|
| Documentation | web search on developer.android.com, then fetch the page |
| Project metadata | read module `build.gradle*` / `settings.gradle*`; `ksrc` for dependency sources |
| Layout / screenshot | `adb shell uiautomator dump` + `adb pull /sdcard/window_dump.xml`; `adb exec-out screencap -p > shot.png` |
| SDK / emulator | `$ANDROID_HOME/cmdline-tools/latest/bin/sdkmanager`, `$ANDROID_HOME/emulator/emulator -list-avds`, `avdmanager` |
| Deploy | `./gradlew :app:installDebug`, then `adb shell am start -n <pkg>/<activity>` |

## Quirks
- `android skills list` and similar print a long progress bar before the result; when captured, treat trailing non-progress lines as the payload.
- `sdk`, `skills`, `info`, `init` and `screen capture` reject `--help` (still print a usage line); the `screen` group `--help` errors out, so call `screen capture` / `screen resolve` directly. `docs`, `emulator`, `create`, `describe`, `run`, `layout` accept `--help`. The first call per session may print unpacking noise.
