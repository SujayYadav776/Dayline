# Manual QA Checklist (PRD §8.2)

Perform on the installed build (not dev tree) unless noted. Tick with date + build version.

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
