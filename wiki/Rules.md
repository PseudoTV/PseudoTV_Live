# Rules

Rules are per-channel behaviour modifiers. Each rule is a small object with an id (`myId`), a set of options, and a set of actions it reacts to; the values are stored on the channel item itself (`citem['rules']`), so every channel carries its own copy with its own option values.

Rules are added and edited in the **Channel Manager** dialog inside Kodi, or in the **Web Channel Manager** running in a browser. A rule only fires for the channel it belongs to, and only for actions that channel's build or playback dispatches (`RulesList.runActions` in `resources/lib/rules.py`).

Enabling a rule does not change your global settings - it only changes what this channel does. Build rules push their values onto the builder for the duration of one channel build and pop them again when that build finishes, and playback rules do the same for one playback session.

## How rules are ordered

Rules dispatch in **ascending `myId` order**, regardless of the order they happen to be listed or shown in the UI. `runActions` sorts the channel's rules once per load (`sorted(rules.items())`, cached per channel) and walks the result, handing each rule the parameter the previous rule returned, so a rule can rewrite the file list, schedule or station list for the rules after it.

Ids are grouped into blocks:

| Block | Purpose |
|-------|---------|
| 100s | Player rules - run during a playback session (PLAYER_START / PLAYER_CHANGE / PLAYER_STOP) |
| 200s | Overlay rules - run while the fullscreen overlay is open (OVERLAY_OPEN / OVERLAY_CLOSE) |
| 300  | Pause rule - the resume/pause state engine, touches build *and* playback |
| 400  | Channel-item rules - persistent `citem` modifications at build time |
| 500s | Build source - what gets scanned: durations, file types, fillers, sort, limits, day/night source |
| 600s | Build selection - which files survive: seasonal, path, language, rating, duration, random |
| 700s | Scheduling - the order and shape of the final list and its time slots |
| 1100s | Served-guide filters - what appears in the M3U/XMLTV served to pvr.iptvsimple |
| 1200s | External feed - pulling content from a remote URL |

`BaseRule` (id 0) is the shared base class every rule inherits from - it provides the option editors, validators and the no-op `runAction`. It is popped off the list before user rules load (`loadRules`/`allRules`) and is **not** a user-selectable rule.

Every rule keeps a `storedValues` list. On entry (overlay open, player start, channel build start) it snapshots whatever it is about to overwrite; on exit it writes the snapshot back. That is why enabling a rule is generally safe and reversible - state is saved and restored around each build or playback session, and one channel's override does not leak into the next channel (several rules were repaired specifically because they aliased a shared dict instead of copying it).

Rule option values are JSON round-tripped when saved, so dict keys come back as strings; `loadRules` re-keys them to ints once so lookups by option index never silently miss.

## Rule reference

Rules are grouped by purpose below; ids ascend within each group.

## Player rules (100s)

### 100 — Show OnNext (ShowOnNext)

Shows the "up next" notification near the end of the current programme. On `PLAYER_START` it saves the player's current OnNext position and mode and applies this channel's values; on `PLAYER_STOP` it writes the saved values back. The `enabled` option gates the whole rule, and `storedValues[0]` doubles as an "already applied" flag so a STOP without a matching START never restores stale values.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Show OnNext | boolean | `True` / `False`; default = `bool(OnNext_Mode setting)` - on whenever a mode is configured |
| 1 | OnNext Position | select | `Auto`, `Move` (Move opens the overlay position tool); default = `OnNext_Position_XY` setting |
| 2 | Select OnNext Mode | select | `Disabled`=0, `Text`=1, `Artwork`=2, `OSD`=3, `UpNext`=4; default = `OnNext_Mode` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

**Notes:** The class docstring describes the modes as "0=off, 1=info, 2=thumb, 3=full, 4=UpNext", but the actual select labels are Disabled / Text / Artwork / OSD / UpNext (`30021/30193/30194/30197/30195`). Previously the `enabled` option was never read (toggling the rule off did nothing), the attribute was read as `onNextMode` (AttributeError killed the rule), and the position tool was focused on the vignette control (`Focus_IDX=0`) instead of the on-next control - all three are fixed in the current code. `optionDescriptions[0]` and `[2]` reuse the label ids (`30045`, `30196`) rather than the description ids.

### 101 — Enable Overlay (DisableOverlay)

Sets `player.enableOverlay` from this channel's option for the duration of playback: with the option off the fullscreen overlay (channel bug, vignette, OSD) is not drawn on this channel. On `PLAYER_START` it saves the previous value, on `PLAYER_STOP` it restores it.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Overlay | boolean | `True` / `False`; default = `Overlay_Enable` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

**Notes:** The class is named `DisableOverlay` but the option reads "Enable Overlay" (`30042`) and its value is assigned straight to `enableOverlay` - so the option behaves literally as shown, and disabling the rule's value is what turns the overlay off.

### 102 — Force Subtitles (ForceSubtitles)

Sets `player.lastSubState` for the session, forcing subtitles on or off while this channel plays, and restores the previous state when playback stops.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Force Subtitles? | boolean | `True` / `False`; default = current Kodi subtitle state (`builtin.isSubtitle()`) |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

**Notes:** Name, description and label are hardcoded English, not localised through `LANGUAGE()`.

### 103 — Trakt scrobbling (DisableTrakt)

Sets `player.disableTrakt` for the session so Trakt scrobbling is suppressed (or allowed) while this channel plays; restores the previous value on stop.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Disable Trakt Scrobbling | boolean | `True` / `False`; default = `Disable_Trakt` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

### 104 — Rollback Playcount (RollbackPlaycount)

Sets `player.rollbackPlaycount` for the session: when on, playback of this channel is passive and does not write playcount or resume progress back to the library. Restored on stop.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Rollback Watched | boolean | `True` / `False`; default = `Rollback_Watched` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

**Notes:** Rule name/description are hardcoded English; the option label/description are localised (`30132`/`33132`).

### 105 — Restart Button (DisableRestart)

Sets `player.replayPercentage` for the session - the progress percentage at which the restart/replay prompt is offered - and restores the previous value on stop.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Restart Prompt (%) | select | `25, 30, ... 95` (step 5); default = `Replay_Percentage` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

**Notes:** Rule name is hardcoded English ("Restart Button"); the description (`33153`) notes `0` disables - but `0` is not offered by this rule's select list.

### 106 — Show OSD on Change (DisableOnChange)

Sets `player.infoOnChange` for the session, controlling whether the OSD/info dialog pops up when the channel changes programme; restored on stop.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Show OSD on Change | boolean | `True` / `False`; default = `Enable_OnInfo` setting |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - save + apply), `RULES_ACTION_PLAYER_STOP` (playback stopped - restore)

### 107 — Pin Lock (PinLockRule)

Parental PIN. On `PLAYER_START`, if the channel is locked (option 1) or the playing item's rating is at/above the configured threshold (option 2, any rating system interpreted to MPAA via `ratings.rank()`), it prompts for the PIN: correct PIN grants approval for this channel, a wrong PIN while something is already playing does nothing, and a wrong PIN with nothing playing opens the channel list window. Approval is stored in `storedValues[0]` and reset on `PLAYER_STOP` and `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | PIN | text | `""` (empty) |
| 1 | Lock Channel | boolean | `False` |
| 2 | Lock Rating | select | `Off`=0, `G`=1, `PG`=2, `PG-13`=3, `R`=4, `NC-17`=5; default `0` (Off) |

**Runs on:** `RULES_ACTION_PLAYER_START` (playback started - prompt if locked), `RULES_ACTION_PLAYER_STOP` (playback stopped - clear approval), `RULES_ACTION_CHANNEL_STOP` (build complete - clear approval)

**Notes:** Approval used to reset only on `CHANNEL_STOP` (build time), so a channel that never rebuilt stayed unlocked forever after one PIN entry - `PLAYER_STOP` was added for that. The rule is "enabled" when either the lock-channel bool or a non-zero rating threshold is set.

## Overlay rules (200s)

### 200 — Channel Bug Rules (ShowChannelBug)

Draws this channel's channel bug/logo on the overlay. On `OVERLAY_OPEN` it saves the overlay's current bug enable/position/color/diffuse/fade state and applies this channel's options; on `OVERLAY_CLOSE` it restores the saved state.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Show Channel Bug | boolean | `True` / `False`; default = `Enable_ChannelBug` setting |
| 1 | Channel Bug Position | select | `Auto`, `Move` (Move opens the overlay position tool); default = `Channel_Bug_Position_XY` setting |
| 2 | Channel Bug Diffuse Color | colour | hex string; default = `ChannelBug_Color` setting |
| 3 | I/O Benchmark | boolean | `True` / `False`; default = `Force_Diffuse` setting |
| 4 | Opacity of the channel bug logo. Default: 25% | select | `15, 20, 25, 30, 35, 40, 45, 50`; default = `ChannelBug_Transparency` setting |

**Runs on:** `RULES_ACTION_OVERLAY_OPEN` (overlay opened - save + apply), `RULES_ACTION_OVERLAY_CLOSE` (overlay closed - restore)

**Notes:** Option 3 is the force-diffuse flag (docstring: "[3] force-diffuse bool", value comes from `Force_Diffuse`) but its label id `30208` resolves to the unrelated string "I/O Benchmark"; `optionDescriptions[3]` is likewise mis-pointed to `33209` (the opacity description) instead of a diffuse description. Option 4's label id `33209` is a description-style string ("Opacity of the channel bug logo. [B]Default:[/B] ... 25%"), used verbatim as the select dialog header. The applied position value is `literal_eval`'d from the stored `"(x, y)"` string.

### 201 — Vignette Rules (SetScreenVingette)

Applies a fullscreen vignette effect. On `OVERLAY_OPEN` it saves `enableVignette`/`vinImage`/`vinView`, applies this channel's image and view mode (zoom, vertical shift, pixel ratio, non-linear stretch), and auto-swaps a `_Day`/`_Night` filename variant by local hour (before 06:00 or after 18:00 prefers `_Night` if that file exists); on `OVERLAY_CLOSE` it restores the three saved values.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Vignette | boolean | `False` |
| 1 | Vignette Image | browse (picture file) | `' '` (a single space); picture mask, source menu entries 12-17 excluded |
| 2 | Vignette Zoom | select | `0.5 ... 2.0` in 0.1 steps; default `1.00` |
| 3 | Vignette V-Shift | select | `-2, -1, 0, 1, 2`; default `0.00` |
| 4 | Vignette Pixel Ratio | select | `0.5 ... 2.0` in 0.1 steps; default `1.00` |
| 5 | Vignette Non-Linear Stretch | boolean | `False` |

**Runs on:** `RULES_ACTION_OVERLAY_OPEN` (overlay opened - save + apply), `RULES_ACTION_OVERLAY_CLOSE` (overlay closed - restore)

**Notes:** `optionDescriptions[5]` uses id `34186`, which is **not present** in `resource.language.en_gb/strings.po` (resolves to an empty string). The class still carries a dead `getPosition()` helper that shows the "Unavailable" notification - it is not wired into `onAction`, and there is a `#todo vin utility to adjust zoom,vshift,pratio and nls` comment: options 2-4 are select-only, there is no on-screen adjuster. `getTitle` casts option 0 with `bool()` - the comment records it previously indexed the raw value, unlike every other rule.

### 202 — Mystery Science Theater 3K Silhouette (MST3k)

Replaces the vignette with an animated two-frame silhouette. On `OVERLAY_OPEN` it saves the vignette state, forces `enableVignette = True` (the gate `onInit` checks to create the control), paints frame 0, and arms a `SERVICE_INTERVAL` timer that re-enters through the fractional action `OVERLAY_OPEN + .1` (30.1) to swap between `MST3K_1.gif` and `MST3K_2.gif`; `OVERLAY_CLOSE` cancels the timer and restores the saved state.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable MST3K Silhouette | boolean | `False` |

**Runs on:** `RULES_ACTION_OVERLAY_OPEN` (overlay opened - save + apply + start cycle), `RULES_ACTION_OVERLAY_OPEN + .1` (timer tick - swap frame), `RULES_ACTION_OVERLAY_CLOSE` (overlay closed - stop timer + restore)

**Notes:** The silhouette *is* the vignette - both gifs are full-frame theatre images, so `overlay.vinView` is deliberately never touched (the default zoom/shift is wanted). The timer only re-arms once the previous tick has fired, so frames cannot stack up and double the frame rate. All strings on this rule are hardcoded English. The `optionImages` attribute lives on the instance, so per-channel copies still resolve the addon's media path.

## Pause and rebuild (300-400)

### 300 — Pause Channel (PauseRule)

The resume/pause state engine, and by far the broadest rule - it registers 13 actions across the build and playback lifecycle. It caches the channel's built filelist (84-day cache) and serves it again on later builds when it already covers `MIN_GUIDEDAYS`, truncates the cached list at the resume point on `PLAYBACK_RESUME`, persists resume progress on player change/stop, and (via `CHANNEL_CITEM`) writes its self-generated resume URL into its own option 1. During its build it forces `padScheduling = False` so the paused channel gets a single "Paused" entry instead of a padded guide, and on `BUILD_TIME_PRE` it replaces the schedule with that one entry (only if an xmltv handle is available to clear programmes).

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Pause | boolean | `True` |
| 1 | FileList | text | `""` - self generated, leave blank (filled with `http://<host>/filelist/<md5>.json` on `CHANNEL_CITEM`) |

**Runs on:** `RULES_ACTION_PLAYBACK_RESUME` (pre-resume - return the truncated resume file list), `RULES_ACTION_PLAYER_START` (playback started - reload cached list), `RULES_ACTION_PLAYER_CHANGE` (playback changed/ended - persist resume), `RULES_ACTION_PLAYER_STOP` (playback stopped - persist resume), `RULES_ACTION_CHANNEL_START` (build start - prune index, snapshot + disable padding), `RULES_ACTION_CHANNEL_STOP` (build complete - restore padding, drop cache), `RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE` (pre-build - return cached list if it is long enough), `RULES_ACTION_CHANNEL_BUILD_FILEARRAY_POST` (post-build - compare cached vs new), `RULES_ACTION_CHANNEL_BUILD_FILELIST_POST` (post-fillers - extend + save cache), `RULES_ACTION_CHANNEL_BUILD_FILELIST_RETURN` (final return - hand back the cached list), `RULES_ACTION_CHANNEL_BUILD_TIME_PRE` (pre-schedule - emit the single paused cell), `RULES_ACTION_CHANNEL_CITEM` (persistent citem - store the resume URL in option 1), `RULES_ACTION_CHANNEL_TEMP_CITEM` (temporary citem - registered, handler is commented out)

**Notes:** The description string (`33228`) says "Experimental. [Default: Disabled]" but the option defaults to `True` (enabled). Recent repairs: `inherited.xmltv.clrProgrammes()` raised AttributeError on every build and was swallowed by the dispatcher's blanket `except`, so the paused schedule never got built (now guarded); the resume `.get().get()` chain raised AttributeError on the first change/stop of a session; `onAction` was a bare return so option 0 could never be toggled off. Because `onAction` returns `onActionToggleBool(optionindex)` unconditionally, clicking option 1 in Kodi's UI would flip the FileList string to `True` rather than open a text box - it is meant to stay blank/self-generated.

### 400 — Force Rebuild (ForceRebuild)

Marks the channel as modified on every build cycle: on `CHANNEL_CITEM` it sets `parameter['changed'] = True`, so the builder rebuilds this channel's content even when nothing else changed.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Force Rebuild Channel | boolean | `False` |

**Runs on:** `RULES_ACTION_CHANNEL_CITEM` (persistent channel item - set the changed flag)

**Notes:** Name/description/label are hardcoded English. `getTitle` casts option 0 with `bool()` - the comment records it previously indexed the raw option list `'[False]'`, unlike every other rule.

## Build source rules (500s)

### 500 — Duration Options (DurationOptions)

Overrides the builder's duration handling for one channel build: where runtimes come from, whether parsed runtimes are written back to the library, and the minimum duration a file must have to be accepted (`builder.minDuration` - files at or below it are skipped, `builder.py:865`). Values are restored on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Duration Source | select | `Prefer Kodi Metadata`=0, `Prefer File Metadata`=1; default = `Duration_Type` setting |
| 1 | Save Durations to Library | boolean | default = `Store_Duration` setting |
| 2 | Minimum Duration | select | `0, 5, ... 895` (step 5, seconds); default = `Seek_Tolerance` setting |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** Option 2's label/description (`32233`, "Minimum Duration") is seeded from the global `Seek_Tolerance` setting and feeds `inherited.minDuration`; the description id is the same as the label id. `optionDescriptions` must be one-per-label - a 4th entry here was previously read against this 3-option rule. The inline comment on option 2 records that toggling it turned `150` into `False` - it is dispatched as a select from `selectBoxOptions` now, with `validateRange(0, 1, 0)` applied to option 0.

### 501 — Include Options (IncludeOptions)

Toggles which file types the builder accepts for this channel: specials/extras, `.strm` files, 3D media, and extra stream-detail metadata parsing. All four builder flags are saved on `CHANNEL_START` and restored on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Include Specials/Extras | boolean | default = `Enable_Extras` setting |
| 1 | Include .strm Files | boolean | default = `Enable_Strms` setting |
| 2 | Include 3D Media | boolean | default = `Enable_3D` setting |
| 3 | Extra Metadata Details | boolean | default = `Enable_Details` setting |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply `incExtras/incStrms/inc3D/incStrmDetails`), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

### 502 — Pre-Roll (PreRoll)

Configures pre-roll bumpers and ratings inserts for this channel: enable mode, random chance, and where filler content comes from (addon resources and/or local folders). Updates `builder.bctTypes['bumpers']` and `['ratings']` on `CHANNEL_START` and restores both on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Pre-Roll | select | `Auto`=-1, `Disabled`=0; default = `Enable_Preroll` setting |
| 1 | Random Pre-Roll Chance | select | `0 ... 100`; default = `Random_Pre_Chance` setting |
| 2 | Bumpers Resources | resources (multi-select) | default = `Resource_Bumpers` (pipe-separated resource ids) |
| 3 | Rating Resources | resources (multi-select) | default = `Resource_Ratings` (pipe-separated resource ids) |
| 4 | Bumpers Folder | browse (multi folder) | default `<cache>/fillers/Bumpers/` (`FILLER_LOC`) |
| 5 | Ratings Folder | browse (multi folder) | default `<cache>/fillers/Ratings/` (`FILLER_LOC`) |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** `optionDescriptions[2]` (`33029`, Bumper Resources) and `[3]` (`33028`, Rating Resources) are **not present** in `resource.language.en_gb/strings.po` and resolve to an empty string. The stored snapshot uses `dict(...)`: `.get()` hands back the live sub-dict, so the previous in-place snapshot made the STOP restore a no-op and per-channel pre-roll overrides leaked into every later channel of the same build.

### 503 — Post-Roll (PostRoll)

Configures post-roll adverts, trailers and extras for this channel: enable mode (auto/off/one-two-three inserts), random chance, filler resources/folders, and whether Kodi's own trailers/extras libraries are used. Updates `bctTypes['adverts']`, `['trailers']` and `['extras']` on `CHANNEL_START` and restores them on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Post-Roll | select | `Auto`=-1, `Disabled`=0, `One Insert`=1, `Two Inserts`=2, `Three Inserts`=3; default = `Enable_Postroll` setting |
| 1 | Random Post-Roll Chance | select | `0 ... 100`; default = `Random_Post_Chance` setting |
| 2 | Advert Resources | resources (multi-select) | default = `Resource_Adverts` |
| 3 | Adverts Folder | browse (multi folder) | default `<cache>/fillers/Adverts/` |
| 4 | Trailer Resources | resources (multi-select) | default = `Resource_Trailers` |
| 5 | Trailers Folder | browse (multi folder) | default `<cache>/fillers/Trailers/` |
| 6 | Include Kodi Trailers | boolean | default = `Include_Trailers_KODI` setting |
| 7 | Include Specials/Extras | boolean | default = `Include_Extras_KODI` setting |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** `optionDescriptions[2]` (`33030`) and `[4]` (`33031`) are **not present** in the en_gb strings file and resolve to an empty string. Same dict-copy repair as Pre-Roll; additionally `extras` used to have no snapshot at all, so its changes persisted for the rest of the build. Note the STOP path uses `dict.update(snapshot)` rather than assigning the key back, and `min`/`max` are re-derived from `builder.limit` on each START.

### 504 — Interleaving (InterleaveValue)

Overrides the builder's interleave settings for one build: how many items are taken per source pass (`interleaveSet`) and whether repeats are allowed (`interleaveRepeat`). Saved on `CHANNEL_START`, restored on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Interleave Set Size | select | `0 ... 25`; default = `Interleave_Set` setting |
| 1 | Interleave Repeats | boolean | default = `Interleave_Repeat` setting |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** The rule description and `optionDescriptions[0]` both use id `34179`, which resolves to the unrelated string "Change Vignette V-Shift" (it is a vignette label, not an interleave description). Option label `30192` is "Interleaving".

### 505 — Sort Methods (HandleMethodOrder)

Overrides the sort used while building this channel's file list: method, order, ignore-articles and artist-sort-name flags. `builder.sort` is snapshotted as a copy on `CHANNEL_START` and restored on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Method | select | `List.Sort` method enums from JSONRPC Introspect (class-cached); default `random` |
| 1 | Order | select | `List.Sort` order enums (class-cached); default `ascending` |
| 2 | Ignore Articles | boolean | `True` |
| 3 | Ignore Artist Sort Name | boolean | `True` |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** Option labels are hardcoded English. Enum lookups are cached at class level to avoid a JSONRPC Introspect call on every `allRules`/`copy`. The snapshot must be a `dict()` copy - `builder.sort` is shared across channels, and an in-place update would leak this override into every later build.

### 506 — Set Limits (HandleLimits)

Overrides the query pagination for this channel build: page limit plus the `end`/`start` window pushed into `builder.limits`. Saved on `CHANNEL_START`, restored on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Limit | select | `0, 10, 25, 50, 100, 250, 500, 1000`; default = `Page_Limit` setting |
| 1 | Limits End | number | default `-1`; description: `-1`=Auto, `0`=Unlimited; valid `-1`..`1000` (or the known total) |
| 2 | Limits Start | number | default `0`; description: `-1`=Unlimited, `0`=Auto; same range as above |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** Option labels/descriptions for 1 and 2 are hardcoded English. Out-of-range digits are rejected with a notification and reset to `25` (`validateDigitBox` default), while `0` is always preserved as the disabled/no-limit convention. `builder.limits` is snapshotted as a copy so the restore is not a no-op.

### 507 — Dayparting (Dayparting)

Swaps this channel's content source by local hour: on `CHANNEL_START` it saves `citem['path']` and replaces it with the night source when the current hour falls in the night window, otherwise with the day source; on `CHANNEL_STOP` it restores the original path.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Day Source | browse (folder) | `""` |
| 1 | Night Source | browse (folder) | `""` |
| 2 | Night Starts At (24h) | number | `0`-`23`; default `22` |
| 3 | Night Ends At (24h) | number | `0`-`23`; default `6` |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - pick source), `RULES_ACTION_CHANNEL_STOP` (build complete - restore path)

**Notes:** Wrap-around windows (e.g. 22 -> 6) must cover both sides of midnight; the old `(hour >= ns) if ns > ne else ...` expression left 00:00-05:59 classified as daytime. An empty path option leaves `citem['path']` untouched.

## Build selection rules (600s)

### 600 — Seasonal (SeasonalRule)

Builds the channel's file array from stored holiday queries instead of the channel path, and sets the channel logo to the holiday's logo (or the seasonal fallback logo). Each query is a JSONRPC file-list request (cached per path for one hour); for TV-type queries it adds `season > 0`/`episode > 0` filters when extras are excluded, or strips season-0/episode-0 entries when extras are included.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Holiday | internal (no editor) | list of query dicts `{path, method, enum, limits, sort, filter, holiday}`; default = one empty template dict |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE` (pre-build - return the holiday file array)

**Notes:** "INTERNAL USE ONLY!" - there is no `onAction` editor (`BaseRule.onAction` returns `''`); the value is injected by the addon when it creates or updates a seasonal channel. `RulesList.setChannelRules` exists specifically so callers that inject rule 600 mid-build (or a channel that never persisted it) dispatch against fresh values instead of a stale snapshot. On any exception it returns an empty array.

### 601 — Path Keyword Filter (PathKeywordFilter)

Keeps or drops files whose path contains one of the configured keywords, before any ordering rule runs.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Include / Exclude | select | `Exclude`=0, `Include`=1; default `0` (Exclude) |
| 1 | Keywords | text | `""` - pipe-separated, case-insensitive |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - filter the flat file list)

**Notes:** `selectBoxOptions` was `Disabled`/`Enabled` - the comment records that this is a mode, not a toggle: `1` keeps matches, `0` drops them. With no keywords configured the list is returned unchanged.

### 602 — Audio / Language Preference (AudioLangPreference)

Filters the list down to files that carry a language tag in the filename (`eng`, `[ENG]`, `.eng.`, `multi`) or in their stream details, matching either the audio or subtitle language. If nothing matches, the original list is returned rather than an empty channel.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Audio Language | text | current Kodi language as a 3-letter ISO 639-2 code (e.g. `eng`), else `""` |
| 1 | Subtitle Language | text | `""` |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - keep matching items)

**Notes:** With both options empty the filter is skipped. Stream matching requires the track language to equal the option or share its first three letters (`eng` matches `eng` and `english`, but not `en`); filename matching is a plain substring test on `lang`, `[lang]`, `.lang.` or `multi`.

### 603 — Content Rating Filter (RatingFilter)

Drops items rated above the configured threshold or whose genre is on the deny list. Ratings from any system (FSK, BBFC, ...) are interpreted to MPAA severity by `ratings.rank()`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Max MPAA Rating | select | `Off`=0, `G`=1, `PG`=2, `PG-13`=3, `R`=4, `NC-17`=5; default `0` (Off) |
| 1 | Blocked Genres | text | `""` - pipe-separated, case-insensitive |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - drop over-rated / denied items)

**Notes:** With both options at their defaults the list is returned unchanged.

### 604 — Programme Length (DurationRangeFilter)

Keeps only programmes whose runtime falls inside the configured minute range; `0` on either end means no limit.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Min Minutes | number | `0`-`600`; default `0` (no limit) |
| 1 | Max Minutes | number | `0`-`600`; default `0` (no limit) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - drop out-of-range items)

**Notes:** Uses `duration` or `runtime` in seconds, whichever the item carries. With both at `0` the filter is skipped.

### 605 — Force Random Order (ForceRandom)

Forces a random order: on `FILEARRAY_PRE` it snapshots `builder.sort` (copy, not alias) and sets `method = random`; on `FILELIST_PRE` it restores the saved sort and shuffles the list.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Force Random Order | boolean | `True` (on by default) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILEARRAY_PRE` (pre-build - set sort method), `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - restore sort + shuffle)

**Notes:** The description string (`33183`) advertises "[B]Default:[/B] OFF" but the option default is `True`. `onAction` was a bare return (the enabled bool could never be turned off) and `optionValues[0]` was never read in `runAction` - both fixed; the rule now no-ops when disabled.

## Schedule rules (700s)

### 700 — Force Episode Order (ForceEpisodeOrder)

Stable-sorts the interleaved list so every show's episodes land in season/episode order, then round-robin merges the shows with movies interleaved - composed from `EvenShowsRule`'s `_sortShows`/`_mergeShows` (chunk size 1) rather than reimplemented. It touches no builder state, so there is nothing to restore on `CHANNEL_STOP`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Force Episode Order | boolean | `False` (off by default) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - rewrite the list order)

**Notes:** Description `33181` claims "[B]Default:[/B] ON" but the option defaults to `False`. Dispatch is sorted by `myId`, so 700 always runs before 701 and 701 consumes 700's already-ordered output. Empty `season`/`episode` strings from scrapers are tolerated (`int(... or 0)`), otherwise a single bad item would abort the rule.

### 701 — Even Show Distribution (EvenShowsRule)

Distributes shows evenly across the schedule: episodes are cut into blocks of the configured chunk size and dealt round-robin, with movies interleaved by a fraction accumulator. On `CHANNEL_START` it saves/applies the builder's `enableEven/evenEpisode/evenShuffle` flags, on `FILELIST_PRE` it rewrites the list, on `CHANNEL_STOP` it restores the flags and clears its working state.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Group TV shows in blocks | select | `0 ... 25` (chunk size; `0` = off); default = `Enable_Even` setting |
| 1 | Force Episode Order | boolean | default = `Enable_Even_Force_Episode` setting |
| 2 | Force Random Order | boolean | default = `Enable_Even_Force_Random` setting |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply flags), `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - reorder the list), `RULES_ACTION_CHANNEL_STOP` (build complete - restore flags)

**Notes:** Options 1 and 2 are mutually exclusive - checking one clears the other. Option 1 deduplicates by item id (set-based, O(n)); option 2 shuffles the show and movie buckets before merging. With chunk size `0` the reorder is skipped (a zero step would otherwise divide by zero in `_chunkEpisodes`).

### 702 — Unwatched First (UnwatchedFirst)

Stable-partitions the list so items with `playcount == 0` play before already-watched items, preserving relative order inside each half.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Unwatched First | boolean | `False` |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - move unwatched to the front)

**Notes:** Docstring says it applies "after ordering rules" - it runs on the same `FILELIST_PRE` hook, and within that hook only after the lower-id rules (700/701) have already rewritten the list.

### 703 — Series Marathon (SeriesMarathon)

Caps how many consecutive episodes of the same show can play: any item past the cap is deferred to the end of the list instead of being dropped.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Episodes per Run | select | `Disabled`=0, `1 ... 25`; default `0` (off) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - batch series runs)

**Notes:** `Disabled` had to be added to the select list, otherwise a cap could be set but never cleared. Items are grouped by `showtitle` (falling back to `tvshowid`).

### 704 — Recent First (RecentFirst)

Moves items whose `dateadded` is within the last N days to the front of the list; items with an unparseable date are treated as not recent.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Recent Days | number | `0`-`365`; default `0` (off) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - move recent items to the front)

### 705 — Genre Boost (GenreWeighting)

Appends extra copies of every item whose genre list contains the keyword, so that genre gets more airtime. Copies are `dict(item)` clones, not aliases - the builder stamps `start`/`stop`/`idx` per list position, so appended aliases would overwrite each other's timestamps.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Genre | text | `""` - matched case-insensitively against `genre[]` |
| 1 | Boost | select | `1`, `2`, `3`; default `1` (no boost) |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_FILELIST_PRE` (mid-build - append weighted copies)

**Notes:** With an empty keyword or a boost of `1` the list is returned unchanged.

### 706 — Pad Scheduling (PadScheduling)

Pads the guide out to the minimum guidedays requirement by cycling the finished file list (`itertools.cycle`) and stamping sequential start/stop times until the schedule reaches `now + MIN_GUIDEDAYS`. On `CHANNEL_START` it saves/applies `inherited.padScheduling`, on `CHANNEL_STOP` it restores it.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Pad Scheduling | boolean | `True` |

**Runs on:** `RULES_ACTION_CHANNEL_START` (build start - save + apply), `RULES_ACTION_CHANNEL_BUILD_TIME_POST` (post-schedule - append duplicates), `RULES_ACTION_CHANNEL_STOP` (build complete - restore)

**Notes:** `onAction` was a bare return, so the enabled bool could never be toggled off (fixed). Reads `item.get('stop')` rather than `['stop']` - an item not yet time-stamped by an earlier rule raised KeyError and killed the whole build step. Rule 300 (Pause Channel) forces this off for its own build, which is why both rules snapshot the same `padScheduling` value.

### 707 — Programme Spacing (ProgrammeSpacing)

Re-stamps the schedule, inserting a 20-second bumper cell after every N minutes of content. Bumper cells are built through `buildCells` exactly like `fillers.py` does, so they render as a proper "Bumper" EPG entry pointing at the bumper folder.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Interval (minutes) | select | `0, 5, ... 120`; default `0` (off) |
| 1 | Bumper Folder | browse (folder) | `""` |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_TIME_POST` (post-schedule - re-stamp and insert bumpers)

**Notes:** The previous hand-rolled bumper dict had no label/type/genre/art and used the bumper *folder* as its file, so it rendered as a blank EPG entry pointing at something unplayable - now repaired. Zero-duration items are skipped (they would stamp `start == stop` and never advance the elapsed counter), and the inserted bumper's own 20 seconds count toward the interval so spacing does not drift.

### 708 — Prime Time (PrimeTimeBlock)

Reserves a time window for matching content: on `BUILD_TIME_PRE` it partitions the queue on the genre/title keyword and rotates the non-matching items so the match block begins at the first slot at-or-after the configured start time.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Start (HH:MM) | time | `20:00` |
| 1 | End (HH:MM) | time | `23:00` |
| 2 | Genre / Title | text | `""` - matched against `title` and `genre[]`, case-insensitive |

**Runs on:** `RULES_ACTION_CHANNEL_BUILD_TIME_PRE` (pre-schedule - reorder so matches land in the window)

**Notes:** The start time was previously read by the editor but never applied - the rule only keyword-front-moved, so the window was decoration; it is now used as the rotation anchor. The end time is informational: stop times are owned by the schedule re-stamp, not by a pre-reorder. With fewer than 2 items, no keyword, or no matches, the list is returned unchanged.

## Served-guide filters (1100s)

### 1100 — Channel Filter (ChannelFilter)

Excludes this channel from the served guide entirely: when enabled, the station whose `id` equals `citem['id']` is removed from the list handed to pvr.iptvsimple, so it appears in neither the M3U playlist nor the XMLTV guide.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Enable Channel Filter | boolean | `False` |

**Runs on:** `RULES_ACTION_M3U_FILTER` (post-M3U http filter - drop the station), `RULES_ACTION_XMLTV_FILTER` (post-XMLTV http filter - drop the station)

**Notes:** The docstring calls this the scaffold for per-channel serve filters.

### 1101 — Hide Groups (GroupHide)

Removes any station whose channel-group list intersects the configured groups from both the served M3U and XMLTV.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Groups | text | `""` - pipe-separated group names, case-insensitive |

**Runs on:** `RULES_ACTION_M3U_FILTER` (post-M3U http filter - drop matching stations), `RULES_ACTION_XMLTV_FILTER` (post-XMLTV http filter - drop matching stations)

### 1102 — Logo Override (LogoOverride)

Sets this channel's station logo to the chosen image in the served guide.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Logo Image | browse (picture file) | `""` |

**Runs on:** `RULES_ACTION_M3U_FILTER` (post-M3U http filter - apply logo), `RULES_ACTION_XMLTV_FILTER` (post-XMLTV http filter - apply logo)

**Notes:** Runs on both filters on purpose - M3U only would leave the playlist showing the original logo while the guide showed the override.

### 1103 — Renumber Channels (RenumberRule)

Rewrites the served channel numbers sequentially starting at the configured value (`s['number'] = start + idx`). M3U only - XMLTV is not touched.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Start Number | number | `0`-`999`; default `0` (0 = no renumbering) |

**Runs on:** `RULES_ACTION_M3U_FILTER` (post-M3U http filter - assign sequential `tvg-chno`)

**Notes:** `validateDigitBox(0, 999, 1)` uses `1` as the reset default, but `0` is preserved by the validator's "0 = disabled" convention and `runAction` treats `0` as "do nothing" - so the shipped default is effectively off.

### 1104 — Guide Name (GuideLabel)

Overrides this channel's display name in the served guide (`s['name']`).

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Display Name | text | `""` |

**Runs on:** `RULES_ACTION_M3U_FILTER` (post-M3U http filter - apply name), `RULES_ACTION_XMLTV_FILTER` (post-XMLTV http filter - apply name)

**Notes:** Runs on both filters for the same reason as LogoOverride - otherwise the playlist and guide would disagree.

## External feeds (1200s)

### 1200 — External Feed (ExternalFeed)

Pulls content from a remote URL into the channel. On `REQUEST_FILELIST_PRE` it fetches the feed (cached for the configured refresh interval) and returns the items - a JSON payload with `{"items":[{"file","title","duration"}]}` or a plain M3U-style list of `#EXTINF:` / file lines; on `REQUEST_FILELIST_POST` it de-duplicates the combined list by `file`.

**Options**

| # | Option | Type | Values / Default |
|---|--------|------|------------------|
| 0 | Feed URL | text | `""` (max 2000 characters) |
| 1 | Refresh Interval (minutes) | number | `1`-`1440`; default `60` |
| 2 | HTTP Headers | text | `""` |

**Runs on:** `RULES_ACTION_CHANNEL_REQUEST_FILELIST_PRE` (pre-request - fetch feed / return cached items), `RULES_ACTION_CHANNEL_REQUEST_FILELIST_POST` (post-request - dedupe by file)

**Notes:** Option 2 (HTTP Headers) is collected but **never applied** - `_fetch` calls `urllib.request.urlopen(url, timeout=30)` without passing them. The refresh option is in minutes; it used to be compared raw against epoch seconds, so the default `60` read as 60 seconds and refetched every minute. A failed fetch falls back to the cached items rather than discarding them, and the cache write is best-effort.

## See also

- [Settings](Settings) - global defaults these rules override
- [Channel Manager](Channel-Manager) - adding rules in Kodi
- [Web Channel Manager](Web-Channel-Manager) - adding rules in a browser
