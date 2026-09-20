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
- [ ] Crash dialog: force an error → dialog appears with "Open logs folder"; logs contain no task text
- [ ] 125/150/200% display scaling; light/dark switch while running
