# Channel Manager

The Channel Manager is PseudoTV Live's editor inside Kodi — a full-screen dialog where you add, edit, move and delete the 999 channel slots of your lineup. It edits a working copy of the channel list; nothing is written until you save.

## Opening the manager

| Entry point | Where | Notes |
|---|---|---|
| **Channel Manager** (action button) | Settings → Channels → Manager & Backup | Visible only while **Autotune** (`Enable_Autotune`) is off. Help text: "Open the Channel Manager to add, edit, and organize your channels. **Tip:** Most settings here mirror the manager." |
| **Channel Manager** (context menu) | Kodi's context menu on a folder/list item | Visible when Autotune is off and the item has no PseudoTV plot data. Opens on the first free channel slot. |
| **Edit Channel** (context menu) | Context menu on a PseudoTV entry (guide/search/channels windows) | Visible when the item's plot contains `item=` and Autotune is off. Opens the manager focused on that channel. |
| **Add to PseudoTV Live** (context menu) | Context menu on a playable folder | Adds the folder straight to the first free slot (channel type `Custom`, favourite on) after the prompt "Would you like to add: **name** to the first available PseudoTV Live channel?" — the manager itself is not shown. |
| **More** (first run) | The "Welcome to PseudoTV Live — No Channels found!" prompt | The **More** option lists **Channel Manager**, addon settings, and (when available) **Import Channels**, **Recover Channels** and **Select Server**. |

Related settings in the same group:

| Setting | Label | Purpose |
|---|---|---|
| `Open_Manager` | Channel Manager | Runs the manager (the action button above). |
| `Default_Channels` | Channel List | Which channel list loads when the manager opens — **Auto** (default), **Ask** ("Select Server for Channel Setup"), the local instance, or another multi-room instance. Shown only when Autotune is off and enabled servers exist. |
| `Export_Channels` | Backup Channels | Saves the current lineup as a backup file before you edit. |

## Window layout

Skin: `resources/skins/default/1080i/plugin.video.pseudotv.live.manager.xml`.

| Control id | Type | Role |
|---|---|---|
| `5` | list | **Channel List** — one row per slot. Default focus. |
| `6` | list | **Channel Items** — the editable fields of the selected channel (shown instead of the channel list). |
| `4` / `41` | group / image | Spinner overlay. While work is in progress the spinner image tints red (`setLocked`) and input is blocked. |
| `10` | button | **Channel Logo** button — 300×340 panel on the right, visible only in the editor view. |
| `50` | scrollbar | Scrolls the channel list. |
| `9000` | grouplist | Container for the four side buttons. |
| `9001`–`9004` | button | The four side buttons; their labels are set in code for each view/state (see below). |
| — | textbox | Description strip under each list, showing the focused row's `description` property. |
| — | image | Logo preview of the focused row (channel list or editor), from `ListItem.Art(icon)`. |

The title bar shows the add-on title and Kodi's localized window text; the add-on version sits top-right. The close button (top right) closes the dialog.

## Channel list view

Each row is `number|` on the left and the channel name on the right, plus the channel logo and a description line "Edit Channel *number* (*instance*)".

Colours tell you the state of a slot: an empty slot uses the unavailable colour; a filled slot uses the available colour for the name, and the number takes the locked, favourite, radio or available colour depending on the channel.

### Side buttons

| State | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| No changes, empty lineup | Close | AutoTune | Recover (only when backups exist) | Delete |
| No changes, channels exist | Close | Predefined | Move | Delete |
| Unsaved changes | Save | Cancel | Move | Delete |

- **AutoTune** and **Predefined** are enabled only when the focused slot is empty; **Recover** likewise.
- **Move** and **Delete** are enabled only when the focused slot has a channel.

## Channel editor view

Selecting a row in the channel list opens the editor for that channel. Rows are built from the channel template's editable keys:

| Row | Label | Description strip | Input |
|---|---|---|---|
| `name` | Name | Enter Channel Name | Text dialog "Enter Channel Name" |
| `path` | Paths | Build Channel Sources | Path list dialog (below) |
| `group` | Groups | Select Channel Groups | Multi-select dialog |
| `rules` | Rules | Create Advanced Channel Rules | Rule list dialog (below) |
| `radio` | Radio | Is this a Radio/Music Channel? | Toggle |
| `favorite` | Favorite | Is this a Favorite Channel? | Toggle |
| `enable` | Enabled | Enable channel building and compilation processes. | Toggle |
| `changed` | Changed | Mark this channel to be rebuilt on next update. Toggle ON to force a channel refresh. | Toggle |

`number`, `type`, `logo`, `id` and `catchup` are internal and never listed. Changing any row marks the channel `changed` and the editor dirty.

### Side buttons

| State | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| No changes | Close | Cancel | Preview | Clear |
| Unsaved changes | Confirm | Cancel | Preview | Clear |

**Confirm** needs a name and a path; **Preview** and **Clear** need a path; **Preview** is disabled for radio channels.

## Editing a channel

1. Select an empty or filled slot in the channel list and press the row (or the logo button) to open the editor.
2. **Name** — type a name (2–127 characters). It re-resolves the channel logo automatically.
3. **Paths** — open the path dialog and add at least one source.
4. **Groups** — pick one or more groups, optionally create custom groups.
5. **Rules** — add per-channel rules (see below).
6. Set **Radio**, **Favorite**, **Enabled** and **Changed** as needed.
7. **Preview** builds the channel's file list to check the result before saving.
8. **Confirm** writes the rows back to the working copy and returns to the channel list.
9. **Save** on the channel list persists everything.

### Paths dialog ("Build Channel Sources")

Entries, top to bottom: **Save** (with the label *Confirm Paths*, only shown once the list has changed), **- Add Path**, then each current path.

- **- Add Path** opens the browser dialog "Select Media Path" and validates the chosen path with a seek test. If the test fails you are asked "Failed to validate Path! Force Approval? *Forced channels may fail to build or playback properly." with a **Try Again (n)** button.
- Selecting an existing path asks "Delete Path?" with **Edit Path** as the third button — yes removes the path, **Edit Path** removes it and re-browses.
- Source types are filtered per channel: radio channels exclude source types `10, 12, 21, 22`, other channels exclude `11, 13, 21`.
- Leave the dialog with **Save** to commit the new list, or cancel to keep the previous list.

### Groups dialog ("Select Channel Groups")

A multi-select over the add-on's built-in group types plus your custom groups. The first entry, **- Add Custom Group**, opens the prompt "Enter Custom Groups Separate by '|' ex. Action|Comedy" and returns to the selection. Clearing every group falls back to **Custom**.

### Rules dialog ("Rules")

Entries: **- Add Rule**, **- Save Rules** (only once rules have changed), then each assigned rule with its rule name.

- **- Add Rule** opens "Select Channel Rule", listing rules not yet assigned to this channel with their description. Rules need a channel id and at least one path first — otherwise you get "Add Content Paths before adding channel rules."
- Selecting an assigned rule asks "Delete Rule?" with **Edit Rule** as the third button: yes removes it, **Edit Rule** opens it.
- The rule editor is titled "Edit Rule *id* - *name*" and lists each option as `label = value` with its description; selecting an option runs the rule's own input (toggle, text, number, time, colour, select, browse).
- **- Save Rules** stores the set on the channel; rule values are saved per rule id as `{id: {values: {...}}}`.

See [Rules](Rules) for the full list of rules and their options.

### Logo button

Clicking the logo button (editor view only) opens the logo dialog: heading "*PseudoTV Live* - Select Channel Logo", body "[B]Browse[/B] - Manually browse for logo / [B]Select[/B] - Choose a matching logo / [B]Auto[/B] - Automatically select best logo", with **Select**, **Browse** and **Auto** buttons (cancel shows "No Logo Found!").

- **Select** — shows "This may take a moment..." then a searchable list of matching logos; pick one.
- **Browse** — file browser for an image; the file is copied into the add-on's logo folder.
- **Auto** — looks the logo up by channel name.

Success shows "Channel logo updated" and marks the lineup as changed. A channel with no name cannot change its logo ("Channel Name Missing...").

### Preview

"Building preview for **name**, this may take a moment..." then a select dialog "*Preview*: **name** - Build Time: **n**s" listing the files the channel would play, in order. Empty result: "Failed to build preview or no content found."

### Move, Clear and Delete

- **Move** — numeric prompt "Input new channel number", then "Move *name* Channels from **X** to **Y**?" A number already occupied by a filled channel is refused ("Inputted channel number already in-use."); above the 999 limit you get the "Max Channels by Type" notification.
- **Delete** (channel list) and **Clear** (editor) both reset the slot after "Channel *n* / Clear Configurations?", keeping the channel number but replacing the contents with the blank template.

## Building a lineup

| Button | Action |
|---|---|
| **AutoTune** | Asks "Would you like to AutoTune sample channels?", then samples your library per category and fills free slots from the focused number (25 samples per category, music appended after the video block). |
| **Predefined** | Pick a content type, then multi-select predefined channels; they are shuffled into free slots starting at the focused number. |
| **Recover** | Asks "Would you like to Recover from the latest backup?", then lets you choose a stored backup and restores it into the slots. |

## Saving and closing

- **Confirm** (editor) applies the row edits to the working copy and marks the channel `changed`.
- **Save** (channel list) asks "Save All Channel Changes?", drops entries without a name or path, assigns ids, then writes locally (with a backup of the previous state) or posts to the selected multi-room instance. You get "Changes Applied!" and the channel/PVR refresh timers are queued.
- **Cancel** discards unsaved changes and closes.
- **Close** / back on the channel list closes the manager, prompting "Save All Channel Changes?" first if anything is dirty.
- Back on a channel asks "Save Current Channel Changes?" before returning to the list.
- While a task is running, clicks are refused with "Controls Temporarily Locked!".
- Opening the manager queues a backup of the current channel list, and blank slots are created from the channel template so new channels always carry the template's defaults.

## See also

- [Web Channel Manager](Web-Channel-Manager) — the same editing workflow in a browser
- [Rules](Rules) — every per-channel rule and its options
- [Settings](Settings) — the settings that drive the manager
