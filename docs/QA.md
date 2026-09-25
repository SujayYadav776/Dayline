# Manual QA Checklist (PRD §8.2)

Perform on the installed build (not dev tree) unless noted. Tick with date + build version.

> **Always do the "launch the installed Dayline.exe on a real desktop" smoke.** An
> offscreen/headless green build does NOT prove the tray/hotkey/DWM paths work:
> booting as `QGuiApplication` made `tray.show()` `abort()` (0xC0000409) only in a
> real interactive session — this shipped once and is now prevented by using
> `QApplication` + a regression test (see DECISIONS D-018).

- [ ] Double-click the installed `Dayline.exe` → the window opens and STAYS open (no crash), tray icon appears
- [ ] Sleep the machine across midnight → rollover runs on wake; correct logical day
- [ ] DST change (simulated by moving system clock) → no missed/double rollover
- [ ] Vault inside a OneDrive/Dropbox folder → edits sync both ways; no corruption
- [ ] Edit the same note simultaneously in Obsidian and Dayline → no lost edits (retry wins or warns)
- [ ] Obsidian closed and open while Dayline writes → writes succeed
- [ ] Note file locked by another process (hold handle) → backoff, non-blocking error banner, UI reloads from disk
- [ ] Vault moved/renamed → "vault not found" recovery flow, choose vault
- [ ] Display scaling 125 / 150 / 200 % → crisp layout, no clipping
- [ ] Switch Windows light/dark while running → theme follows live, no restart
- [ ] Hotkey conflict (register Ctrl+Alt+N elsewhere first) → friendly error in Settings
- [ ] Reboot → autostart launches minimized to tray (when enabled)
- [ ] Uninstall + reinstall → settings/backups survive; vault untouched
- [ ] Very long task text (≥ 500 chars) → wraps, no layout break
- [ ] 500 tasks in one day → add/scroll stays responsive
- [ ] Emoji-heavy tasks (📌🧪 flags, ZWJ sequences) → round-trip byte-exact, display correct

## M5/M6 items requiring an interactive Windows session (fake/unit-tested, not headless-verifiable)
- [ ] Tray icon appears; left-click toggles window; menu items work (Quick add · Open today in Obsidian · Show · Quit)
- [ ] Global hotkey Ctrl+Alt+N opens the quick-add popup from another app; Enter adds to today; conflict shows a friendly error
- [ ] Close-to-tray: clicking X hides to tray (when on); Quit via tray/Ctrl+Q exits (when off)
- [ ] Autostart toggle writes/clears HKCU Run; after reboot Dayline starts minimized to tray
- [ ] Dark title bar follows the theme live (DWM) on Win10 20H1+ and Win11
- [ ] Mica backdrop: on Windows 11 the window shows a subtle translucent wallpaper blur behind the cards/margins (Settings → Appearance → "Mica backdrop" toggles it; off by default on Win10 where the toggle is hidden)
- [ ] Updates (opt-in): with the repo public, Settings → Updates "Check now" reports the running version or a newer release; turning on "Auto-check (daily)" checks once at startup. "Install update" downloads over https and silently upgrades the running app (force-closes, then relaunches updated). Offline → "Couldn't check"; never falsely claims up-to-date.
- [ ] Crash dialog: force an error → dialog appears with "Open logs folder"; logs contain no task text
- [ ] 125/150/200% display scaling; light/dark switch while running

## v1.3.0 paper-design items (interactive Windows human check)
- [ ] Today screen: paper texture visible behind content; lowercase weekday + big pixel date + lowercase month; completed tasks show a red ticked circle + strike-through inline (no Done/Carried sections); empty day reads "No tasks on this day."
- [ ] Ribbon (top-left) opens the nav drawer; `‹ TODAY ›` steps days; person glyph → Settings.
- [ ] Bottom week-strip: red circle on today, hairline column dividers, gray completion fill; tapping a day opens it; the raised `⌃` tab slides up the Progress panel.
- [ ] Progress panel: "Progress"/"My week"/"Activity" in the typewriter serif; My-week card scrolls if the day is long; Day streak / Tasks done counts; 13-week Activity heat-map with one month label per month (no duplicates).
- [ ] Bundled fonts render (Varela Round body, Wallpoet date) — if a font is missing the layout falls back to Segoe UI without breaking.
- [ ] App/taskbar/tray icon + onboarding + About card all show the exact brand logo.
- [ ] Tray-first: with a vault configured, launching Dayline shows NO window — a "Running in the tray" toast appears instead; left-clicking the tray icon opens the small 360×600 widget; launching the exe a second time re-raises the running window; X hides to tray; "Start hidden in tray" toggle in Settings → General flips the boot behavior.
- [ ] Notification-centre placement: every tray summon (icon click, menu Show, second launch) opens the widget docked bottom-right, just above the taskbar; on a secondary monitor it uses that monitor's work area; resizing keeps the bottom-right corner pinned on next summon.
- [ ] Frameless title bar: traffic-light dots close/minimise/maximise (red honours close-to-tray), grey when unfocused, glyphs on hover; drag the strip (Aero Snap still works), resize from edges/corners; maximised fills the work area without covering the taskbar.
- [ ] Click-to-jump: double-click a task's text → Obsidian focuses and lands on that line (search highlights it, or scrolls to it if the line ends with a `^blockid`) WITHOUT opening the editor; single-click opens the inline editor after ~280 ms and does NOT summon Obsidian; completed tasks jump too; clicking before a vault is configured does nothing.
- [ ] Panel mode: with "Auto-hide when unfocused" ON, clicking another app (or alt-tab) makes the widget vanish to the tray instantly; tray click/hotkey/second-launch re-summons bottom-right; with it OFF the window behaves normally; onboarding never auto-hides.
- [ ] Recurrence: complete "gym 🔁 every monday  <mon>" → next Monday's note gains "- [ ] gym 🔁 every monday 📅 <mon+7>"; one Ctrl+Z removes the instance and unticks the original; overdue weekly completed today spawns AFTER today, never in the past; typing "gym every monday" in quick-add stores `gym 📅 <next mon> 🔁 every monday`.
- [ ] Move-to-day: hover a task → click 📆 → the week card appears with 7 day chips (today ringed red, current day dimmed/disabled); picking a day moves the task (📅 rewritten, app navigates to that day, one Ctrl+Z undoes it); click outside or press Esc to cancel.
- [ ] Due reminder: at 09:00 (or on next launch after migrating an existing config) a tray toast shows "N due today · M overdue"; toggling "Daily due reminder" off stops it; completing everything before 09:00 reads "Nothing due today — all clear."
- [ ] Week page (shadcn restyle): summary card shows COMPLETION eyebrow + big % headline, hairline, ring with 'N still open'; day rows form a bordered table with DAY/PROGRESS/DONE headers, hover wash, today tinted with a red dot, future days faded; heat-map card has a Less→More legend; page scrolls to fit everything; ‹ › are ghost buttons and 'This week' is an outline button; range label elides cleanly on narrow widths.
- [ ] Summon hotkey: with the app in the tray, press Ctrl+Shift+D anywhere → the widget pops up bottom-right and focused (it never hides when already visible); Ctrl+Alt+N still summons straight into the add-task field; Settings → General lists both keys; quitting releases both (rebindable by another app afterwards).
- [ ] Always-bottom-right start: move/resize the widget, quit, relaunch — it opens again small (360x600) docked bottom-right above the taskbar, never at the old spot or size; dragging within a session still works; tray summon behaves the same.
- [ ] Thin paper: with Mica on (Win11), toggling "Thin paper (translucent)" makes the wallpaper blur faintly visible through the paper; toggling off restores solid paper instantly; on Win10 the toggle is hidden; drag-to-reschedule: dragging a task onto another week-strip day moves it (📅 rewritten, source line removed) and the strip follows.
- [ ] Spring checkbox (no pulse ring anymore): checking a task swells the red fill from the centre with a small bounce, the tick draws in two strokes, the label dims and a strike wipes across it at true visual center (single-line tasks); pressing scales the box; unchecking reverses without animation; reduced-motion / Theme.animate off jumps straight to done state; white tick on red fill (never black).
- [ ] Staggered ribbon menu: clicking the hamburger sweeps two heat-map colour bands (salmon + bookmark red) in from the ribbon side, the paper panel follows, then TODAY/WEEK/SETTINGS/QUIT rise into place in the LEMON MILK font with red superscript numbers (~1 s total); picking a row navigates and closes; the ribbon (toggle) or a traffic light above the panel, Escape, or picking an item all close it with one synchronized fast slide-out; reduced-motion snaps open/closed; in dark theme the panel is dark with the warm red ramp.
- [ ] Rounded corners: the widget's four corners are rounded like native Win11 windows (matching radius), including while the staggered menu covers them; on Win10 the widget stays square with no errors in the log.
- [ ] Folder mode: onboarding step 1 shows "Obsidian vault | Any folder" chips; picking Any folder hides the vault list, a folder path (new or empty) finishes setup, and adding a task creates `<folder>/Daily/<today>.md` with the `## To-Do` section; double-clicking a task opens that file in the OS default editor (no Obsidian); restart keeps folder mode (config `vault_mode: "folder"`); "Use as folder" on the recovery screen works the same; switching back via Change vault → vault restores obsidian mode and jumps.
