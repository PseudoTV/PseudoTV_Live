# Web Channel Manager

The Web Channel Manager is PseudoTV Live's channel editor in a browser. It is a single page (`remotes/manager.html`) served by the add-on's own HTTP server, so any phone, tablet or PC on your network can edit the lineup of any enabled instance — no Kodi window needed.

## Opening it

| Entry point | Where | Notes |
|---|---|---|
| **Remote UI** (action button) | Settings → Miscellaneous → Documents | Runs the QR dialog headed **Remote UI**, showing `Utilities: http://<host>/remote.html`. Enabled only while **Server Status** is `[COLOR=green][B]Online[/B][/COLOR]`. Help text: "Show a QR to open the remote web UI. **Tip:** Control PseudoTV from a browser." |
| **Show Welcome** (action button) | Settings → Miscellaneous → Documents | Shows a QR for `http://<host>/manager.html` after updates. |
| Direct URL | Browser | The server answers `/` and any path ending in `.html` with the manager page (the exception is `payload.html`, the raw payload editor). |

Requirements:

- The HTTP server must be running — **Server Status** (`Remote_Status`, default `[COLOR=red][B]Offline[/B][/COLOR]`) shows it.
- The port comes from **TCP Port** (`TCP_PORT`, default `50001`, help: "Port for the HTTP server").
- **M3U URL**, **XMLTV URL** and **Genre URL** in the same Multi-room group are the playlist/guide/genre endpoints IPTV Simple uses; the manager page does not need them.

## Page layout

1. Splash banner image.
2. **Row 1 — server bar**: one tab per instance. Built from `/api/servers.json` plus the local instance from `/api/bonjour.json`; enabled instances first, local first, the rest sorted by name. The tab tooltip shows the host; clicking selects that instance.
3. **Row 2 — content tab bar**: ten tabs — **Channels**, **Library**, **Resume**, **Guide**, **INFO**, then a spacer, **Seasons**, **Settings**, **Imports**, **Backups**, **Groups**.
4. Content area: one panel per tab, plus a status line (`Instance: <name> | Host: <host> | Channels: <n> (autotuned)`).

Selecting an instance probes its reachability (`/api/bonjour.json`, 2.5 s). If it is offline, the **Channels**, **Library**, **Guide** and **INFO** tabs are dimmed and disabled, an "*name* is OFFLINE" banner explains "Showing last cached data — edits are disabled until the instance is reachable.", and the last good response is served from `localStorage` instead of the network.

Switching instances or tabs while the channel form has edits prompts for confirmation ("OK discards them and switches instance." / "OK discards them and continues.").

## Tabs

| Tab | Loads | Key controls |
|---|---|---|
| **Channels** | `/api/settings` (autotune check), `/api/channels` | Instance status line, autotune banner, channel selector + **+ New**, channel form, logo, rules, **Clear** / **Move** / **Cancel** / **Save** |
| **Library** | `/api/library.json` | Collapsible per-type sections with item counts; collapse state persists in `localStorage` |
| **Resume** | `/api/resume` | Cards with a progress bar and a **▶ Resume** link; the tab is greyed out when there are no entries |
| **Guide** | `/remotes/genres.xml`, `/api/guide?page=N` | Scrollable EPG grid with a 48-slot day header, a moving "now" timebar, infinite scroll (10 channels per page), and a detail panel with a **▶ Play** link |
| **INFO** | `/api/bonjour.json`, `/api/system`, `/api/pvr.json`, `/api/logs.json` | Key/value info grid, **PVR Status** panel (Overview / M3U / XMLTV / Log / Notifications), **Kodi Log** panel (Summary / Errors / Project Logs / System), Remote Endpoints, collapsible README and Changelog, External Links |
| **Seasons** | `/api/seasons`, `/api/holidays` (same-origin) | Month calendar with **◀** / **▶** / **Today**, day editor (**Name**, **Tagline**, **Keyword**, **Logo URL**), **Holiday Library Rules** with **+ Add Episode Query** / **+ Add Movie Query**, **Cancel** / **Save** |
| **Settings** | `/api/settings` | **Global Settings** panel, **Filter settings...** box, **Save Settings** button |
| **Imports** | `/api/imports` | "Importable Channel Files" list with a channel count, date and **Import** button per file |
| **Backups** | `/api/backups` | "Channel Backups" list (read-only entries) plus **Backup Now** |
| **Groups** | `/api/groups` | "Channel Groups": **New group name...** input + **Add**, built-in and custom group chips |

## Editing a channel

1. **Select Channel** dropdown (`-- Select Channel --`) or **+ New** to start from the blank template (`/api/template`).
2. The form opens as `Ch <number>: <name>` with a logo tile and a **Search** button.
3. Fields are rendered from the channel object with their raw key as the label (`name`, `group`, `path`, and any other non-hidden keys); `path` and `group` span the full width. `type`, `catchup`, `catchup-source`, `url`, `id`, `holiday`, `rules`, `logo`, `number` and `changed` are never rendered as inputs.
4. **Logo** — click the tile for the prompt "Logo URL (image://, http://, or local path):", or press **Search** for "Search logo for:" which queries `/api/logo_select` and opens the **Select Logo** grid.
5. **Paths** — the `path` row is a select of the channel's current paths with **+ Add** (path browser) and **Manual**.
   - **+ Add** opens **Browse Path** with **↑ Up**, **Select This Folder** and a directory listing fed by `/api/browse?path=...`.
   - **Manual** prompts "Enter path (plugin://, multipath, http, or filesystem):" for anything the browser cannot reach.
6. **Toggles** — `Enable: ON/OFF`, `Radio: ON/OFF`, `Favorite: ON/OFF` buttons.
7. **Rules** — see below.
8. **Save** validates first: name 2–127 characters and at least one path, then `/api/channel/validate` and `POST /api/channels` with the full channel array. Success shows "Channel Saved" and reloads the form.
9. **Cancel** discards edits, **Clear** resets the channel to a blank template (after "Clear this channel to a blank template?"), **Move** assigns a free number (1–999, rejected when already in use).

### Rules

- The **Rules** row holds a `-- Select Rule --` dropdown and an **+ Add** button.
- **+ Add** opens the **Add Rule** list from `/api/rules`; every row reads `Rule <id> — <name>` and already-assigned rules carry a **set** badge.
- Picking a rule seeds its default values (`0`–`3`) and loads them into **Value 0**, **Value 1**, … text inputs holding the JSON-encoded value.
- Values are collected back into the channel's `{ruleId: {values: {...}}}` map when saving.

### Multi-room behaviour

Saving posts to the selected instance's host, not to the page's own host, so one browser can manage every instance in the server bar. Seasons edits are local-first and synced to all enabled instances (the tab says so).

## Floating widgets

- **WORKING...** overlay while a request is in flight, with the status text for the operation (e.g. `LOADING LIBRARY...`, `SAVING SETTINGS...`).
- **Now Playing** (bottom right) polls `/api/playback` every 3 seconds; dismissible with ✕.
- **Building** polls `/api/build` every 3 seconds; dismissible with ✕. Both widgets reset when the instance changes.

## Requests

- GETs go to the selected instance's host.
- POSTs send `Authorization: Bearer <uuid>`; the server also accepts a legacy `uuid` body field.
- Tab data is fetched through an offline-aware wrapper that caches each successful response and falls back to the cache when the host is unreachable.

## Confirmations and alerts

| Message | When |
|---|---|
| "You have unsaved channel edits. OK discards them and continues." | Leaving the Channels tab with edits |
| "You have unsaved channel edits. OK discards them and switches instance." | Switching instance with edits |
| "Continue and save settings? Your unsaved changes will carry over to the selected channel (not posted to the server)." | Changing channel with edits |
| "Discard unsaved changes to the current channel?" | **+ New** with edits |
| "Clear this channel to a blank template?" | **Clear** |
| "Channel name must be 2-127 characters." / "Channel must have at least one path - use the "+ Add" path browser." | **Save** validation |
| "Disable automatic channels and switch to your custom channel set? PseudoTV will restart to apply the change." | **Disable Autotune** on the autotune banner |
| `Replace your current channels with "<file>"?` | **Import** |
| "Channel Saved", "Settings saved", "Import complete", "Backup created" | Successful operations |

## See also

- [Channel Manager](Channel-Manager) — the same workflow inside Kodi
- [Rules](Rules) — every per-channel rule and its options
- [Settings](Settings) — the settings edited on the Settings tab
