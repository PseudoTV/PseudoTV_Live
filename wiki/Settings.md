# Settings

PseudoTV Live's settings live in the addon's standard Kodi settings dialog (Add-ons → PseudoTV Live → Configure), defined by `resources/settings.xml` in the Kodi 19+ (`version="1"`) format. These are global defaults: most everyday options are mirrored by per-channel rules in the Channel Manager, which override the globals for individual channels — see [Rules](Rules).

## Settings sections

| Section | What it is for |
|---|---|
| Channels | Autotune, the Channel Manager, backup/restore, and links to Kodi editors |
| Options | Cache folder, artwork packs, guide window, and build behaviour |
| Global | Playback, on-screen overlays, and parser defaults for all channels |
| Fillers | Pre-roll (bumpers/ratings) and post-roll (adverts/trailers) |
| Multi-room | HTTP server status and ZeroConf discovery of other instances |
| Integrations | AI (OpenRouter) models for contextual data and artwork |
| Miscellaneous | Utilities, document links, debugging, and expert options |

## Channels

| Setting | Type | Default | Description |
|---|---|---|---|
| **Update Status** (`Update_Status`) | action button | (empty) | Shows whether a newer PseudoTV Live build is available. Default: Auto - set by the addon. Status display only (no action). |
| **Autotune Channels** (`Enable_Autotune`) | bool | `false` | Automatically create a channel lineup from your video library. Default: OFF - recommended: ON for a quick start. |
| **Channel Manager** (`Open_Manager`) | action button | (empty) | Opens the Channel Manager (`context_create.py open_manager`). Open the Channel Manager to add, edit, and organize your channels. Tip: Most settings here mirror the manager. |
| **Channel List** (`Default_Channels`) | action button | `Auto` | Opens the channel list selector (`utilities.py select`). Which channel list loads when the Channel Manager opens. Default: Auto. |
| **Backup Channels** (`Export_Channels`) | action button | (empty) | Runs the channel export (`backup.py Export_Channels`). Save your channels and rules as a backup file. Tip: Keep a copy before major changes. |
| **Restore Channels** (`Import_Channels`) | action button | (empty) | Runs the channel import (`backup.py Import_Channels`). Load channels and rules from a previous backup. Tip: Restoring replaces your current setup. |
| **Smartplaylist Editor** (`Launch_SmartplaylistEditor`) | action button | (empty) | Opens Kodi's video playlists window (`ActivateWindow(10025,"library://video/playlists.xml/")`). Open Kodi's SmartPlaylist editor to build custom playlists. Tip: Playlists can be used as channel paths. |
| **Node Editor** (`Launch_NodeEditor`) | action button | (empty) | Opens the Node Editor addon (`ActivateWindow(10001,plugin://plugin.library.node.editor)`). Open Kodi's node editor for advanced smartplaylist creation. Tip: Nodes bundle multiple playlists. |
| **PVR & Live TV Settings** (`Launch_LiveSettings`) | action button | (empty) | Opens Kodi's PVR settings window (`ActivateWindow(10021)`). Open Kodi's PVR & Live TV settings. Tip: Where IPTV Simple is configured. |
| **IPTV Simple Settings** (`Launch_IPTVSimple`) | action button | (empty) | Opens IPTV Simple settings (`Addon.OpenSettings(pvr.iptvsimple)`). Open the IPTV Simple Client addon settings directly. Tip: Check the active M3U/XMLTV URLs here. |

## Options

| Setting | Type | Default | Description |
|---|---|---|---|
| **Shared Cache Folder** (`User_Folder`) | folder | `special://profile/addon_data/plugin.video.pseudotv.live/cache` | Store the addon cache in a shared location. Default: OFF - recommended: ON to reduce SSD wear. (Help text reads like a toggle; the setting is a path.) |
| **Logo Resource Packs** (`Resource_Logos`) | addon multiselect | `resource.images.pseudotv.logos\|resource.images.studios.white\|resource.images.studios.coloured\|resource.images.moviegenreicons.white\|resource.images.moviegenreicons.transparent\|resource.images.musicgenreicons.text` | Choose the logo packs used for channel artwork. Default: PseudoTV + studio logos. |
| **EPG Artwork** (`EPG_Artwork`) | select | `0` (0 = Prefer Landscape, 1 = Prefer Poster) | Prefer landscape or poster artwork in the TV guide. Default: Prefer Landscape. |
| **Idle Timer** (`Idle_Timer`) | select | `0` (0 = Disabled, 1 = 3 Hours, 2 = 6 Hours, 3 = 12 Hours, 4 = 24 Hours) | Stop playback after the system is idle for this long. Default: OFF - 0 disables; recommended: leave OFF unless you schedule automated stops. |
| **Detect Compatible Addons** (`Enable_Recommended`) | bool | `true` | Scan for addons that can provide channel content. Default: ON - recommended: ON so AutoTune can discover plugin sources. |
| **Nearest Holiday** (`Nearest_Holiday`) | bool | `true` | Advance seasonal holiday channels to the nearest upcoming holiday. Default: ON - recommended: ON so holiday channels stay current. |
| **Build Filler Folders** (`Build_Filler_Folders`) | bool | `false` | Create per-channel filler folders under the cache folder. Default: OFF - recommended: leave OFF unless you use per-channel filler folders. |
| **Guide Grouping** (`Enable_Grouping`) | bool | `true` | Group guide entries by category in the XMLTV output. Default: ON. |
| **Detect Playlist Changes** (`Enable_Changed`) | bool | `true` | Rebuild channels when a playlist file changes. Default: ON - recommended: ON so playlist edits rebuild automatically. |
| **Clean Up Recordings** (`Clean_Recordings`) | bool | `true` | Remove stale or orphaned recording entries from the guide. Default: ON. |
| **Build During Playback** (`Run_While_Playing`) | bool | `true` | Keep building channels while media is playing. Default: ON - disable if playback stutters. |
| **Playback Notifications** (`Notify_While_Playing`) | bool | `true` | Show popup notifications while media plays. Default: ON. |
| **Client Only** (`Enable_Client`) | bool | `false` | Run this instance as a client with no local channels. Default: OFF - recommended: ON only on dedicated client boxes. |
| **YouTube Cookies File** (`Youtube_Cookies`) | text | `special://profile/addon_data/plugin.video.pseudotv.live/www.youtube.com_cookies.txt` | Path to a YouTube cookies.txt exported from a logged-in browser session (Netscape format). Default: profile www.youtube.com_cookies.txt. Tip: A valid session cookie avoids yt-dlp bot checks so durations resolve. |
| **Guide History (Past Days)** (`Min_Days`) | slider | `1` (range 1–3, step 1) | How many days of past guide to keep. Default: 1. Always greyed out (hard-disabled). |
| **Guide Ahead (Future Days)** (`Max_Days`) | slider | `3` (range 1–31, step 1) | How many days of future guide to build. Default: 3. Always greyed out (hard-disabled). |
| **OSD Display Time** (`OSD_Timer`) | slider | `5` (range 0–15, step 1) | Seconds the channel info overlay stays visible. Default: 5. Always greyed out (hard-disabled). |

## Global

| Setting | Type | Default | Description |
|---|---|---|---|
| **Playback Method** (`Playback_Method`) | select | `0` (0 = PVR Callback, 1 = Playlist) | How channels are sent to the player. Default: PVR Callback - plays via PVR; Playlist: queues a playlist instead. |
| **Seek Tolerance (sec)** (`Seek_Tolerance`) | slider | `60` (range 0–900, step 5) | Seconds to ignore when live timing differs from the offset. Default: 60. |
| **Seek Threshold (%)** (`Seek_Threshold`) | slider | `98` (range 85–100, step 1) | Skip content near the end past this percent. Default: 98% - 100% disables. |
| **Disable Trakt Scrobbling** (`Disable_Trakt`) | bool | `false` | Don't send PseudoTV playback to Trakt. Default: OFF - scrobbling active; recommended: leave OFF. |
| **Rollback Watched** (`Rollback_Watched`) | bool | `true` | Restore playcount and resume point when playback ends. Default: ON - recommended: ON so PseudoTV playback never alters library playcounts. |
| **Enable Overlay** (`Overlay_Enable`) | bool | `true` | Show overlay visuals (channel bug, vignette, OSD). Default: ON. |
| **Show OnNext** (`OnNext_Mode`) | select | `2` (0 = Disabled, 1 = Text, 2 = Artwork, 3 = OSD, 4 = UpNext) | Show what's up next near the end of a program. Default: Artwork - built-in. UpNext: requires the Up-Next addon. |
| **OnNext Position** (`OnNext_Position_XY`) | action button | `Auto` | Opens the OnNext position mover (`utilities.py Move_OnNext`). Where the OnNext popup appears. Default: Auto. |
| **Show OSD on Change** (`Enable_OnInfo`) | bool | `true` | Display the OSD when the channel changes. Default: ON. |
| **Restart Prompt (%)** (`Replay_Percentage`) | slider | `55` (range 0–95, step 5) | Offer to restart when progress passes this percent. Default: 55% - 0 disables. |
| **Show Channel Bug** (`Enable_ChannelBug`) | bool | `true` | Show the channel logo in a corner during playback. Default: ON. |
| **Channel Bug Transparency** (`ChannelBug_Transparency`) | slider | `25` (range 15–50, step 5) | Opacity of the channel bug logo. Default: 25%. |
| **Channel Bug Diffuse Color** (`ChannelBug_Color`) | color button | `FFFFFFFF` | Tint applied to the channel bug. Default: White (#FFFFFFFF). Only enabled when Kodi's build version contains 20. |
| **Force Diffuse Color** (`Force_Diffuse`) | bool | `false` | Apply the tint even to full-color logos. Default: OFF. |
| **Channel Bug Position** (`Channel_Bug_Position_XY`) | action button | `Auto` | Opens the channel bug position mover (`utilities.py Move_Channelbug`). Where the channel bug appears. Default: Auto. |
| **Pagination Size** (`Page_Limit`) | slider | `25` (range 0–1000, step 5) | Items requested per library scan call. Default: 25 - 0 = unlimited; recommended: keep 25 on low-power devices. |
| **Folder Depth** (`Recursive_Depth`) | slider | `1` (range 1–25, step 1) | Subfolder levels to scan. Default: 1 - 0 = root only. |
| **Duration Source** (`Duration_Type`) | select | `0` (0 = Prefer Kodi Metadata, 1 = Prefer File Metadata) | Where runtime comes from. Default: Kodi metadata - faster; File metadata: precise but slower. |
| **Save Durations to Library** (`Store_Duration`) | bool | `false` | Write file-parsed runtimes to Kodi's database. Default: OFF - recommended: ON for accurate EPG. |
| **Include Fillers** (`Enable_Fillers`) | bool | `true` | Insert bumpers, ratings, adverts, and trailers between programs. Default: ON. |
| **Include Specials/Extras** (`Enable_Extras`) | bool | `false` | Include Season 00 and movie extras. Default: OFF - recommended: OFF so specials don't pad the guide. |
| **Include .strm Files** (`Enable_Strms`) | bool | `false` | Include .strm stream files in channels. Default: OFF - recommended: OFF unless you rely on .strm links. |
| **Include 3D Media** (`Enable_3D`) | bool | `false` | Include 3D content when building channels. Default: OFF - recommended: OFF unless you have 3D content. |
| **Extra Metadata Details** (`Enable_Details`) | bool | `false` | Parse additional media metadata during builds. Default: OFF - recommended: OFF; enable only when runtimes are missing. |
| **Interleave Set Size** (`Interleave_Set`) | slider | `1` (range 0–25, step 1) | Interleave paths in groups of this size. Default: 1 - 0 disables. |
| **Interleave Repeats** (`Interleave_Repeat`) | bool | `true` | Allow repeats when interleaving paths. Default: ON. |
| **Even Show Distribution** (`Enable_Even`) | slider | `0` (range 0–25, step 1) | Group episodes in blocks for even scheduling. Default: OFF - recommended: ON for balanced show rotation. |
| **Force Episode Order** (`Enable_Even_Force_Episode`) | bool | `true` | Prefer episode order over playlist sorting. Default: ON - recommended: ON for episodic channels; OFF to keep playlist order. |
| **Force Random Order** (`Enable_Even_Force_Random`) | bool | `false` | Shuffle channel content randomly. Default: OFF. |

## Fillers

| Setting | Type | Default | Description |
|---|---|---|---|
| **Enable Pre-Roll** (`Enable_Preroll`) | select | `-1` (-1 = Auto, 0 = Disabled) | Play ratings and bumpers before programs. Default: OFF. (XML default is actually -1 = Auto, not 0 = Disabled.) |
| **Random Pre-Roll Chance** (`Random_Pre_Chance`) | slider | `25` (range 0–100, step 1) | Chance a random video is used when none matches. Default: 25%. |
| **Bumper Resources** (`Resource_Bumpers`) | addon multiselect | `resource.videos.bumpers.pseudotv\|resource.videos.bumpers.kodi` | Addons that provide bumper videos. Default: PseudoTV + Kodi bumpers. |
| **Rating Resources** (`Resource_Ratings`) | addon multiselect | `resource.videos.ratings.mpaa.classic` | Addons providing rating card videos. Default: MPAA classic. |
| **Enable Post-Roll** (`Enable_Postroll`) | select | `0` (-1 = Auto, 0 = Disabled, 1 = One Insert, 2 = Two Inserts, 3 = Three Inserts) | Play adverts and trailers after programs. Default: OFF. |
| **Random Post-Roll Chance** (`Random_Post_Chance`) | slider | `25` (range 0–100, step 1) | Chance a random video is used when none matches. Default: 25%. |
| **Advert Resources** (`Resource_Adverts`) | addon multiselect | (empty) | Addons providing advert videos. Default: None. |
| **Trailer Resources** (`Resource_Trailers`) | addon multiselect | (empty) | Addons providing trailer videos. Default: None. |
| **Include Kodi Trailers** (`Include_Trailers_KODI`) | bool | `true` | Use trailers from your Kodi library. Default: ON. |
| **Include Kodi Extras** (`Include_Extras_KODI`) | bool | `true` | Use extras/specials as post-roll fillers. Default: ON. |

## Multi-room

| Setting | Type | Default | Description |
|---|---|---|---|
| **Server Status** (`Remote_Status`) | action button | `[COLOR=red][B]Offline[/B][/COLOR]` | Current status of this instance's HTTP server. Default: Shows live status. Status display only (no action). |
| **TCP Port** (`TCP_PORT`) | number | `50001` | Port for the HTTP server. Default: 50001 - recommended: keep 50001 unless the port is in use. |
| **Instance Name** (`Remote_NAME`) | text | (empty) | Name shown for this instance on the network. Default: Set at startup. Always greyed out (read-only). |
| **M3U URL** (`Remote_M3U`) | text | (empty) | Playlist URL served by this instance. Default: Generated at startup. Tip: Used by IPTV Simple. Always greyed out (read-only). |
| **XMLTV URL** (`Remote_XMLTV`) | text | (empty) | Guide URL served by this instance. Default: Generated at startup. Tip: Used by IPTV Simple. Always greyed out (read-only). |
| **Genre URL** (`Remote_GENRE`) | text | (empty) | Genre mapping URL served by this instance. Default: Generated at startup. Tip: Enables EPG colors. Always greyed out (read-only). |
| **ZeroConf Status** (`ZeroConf_Status`) | action button | `[COLOR=red][B]Offline[/B][/COLOR]` | Toggles ZeroConf (`multiroom.py Enable_ZeroConf`). Discovery status of this instance. Default: Shows live status. |
| **Select server** (`Select_server`) | action button | (empty) | Opens the server picker (`multiroom.py Select_Servers`). Choose which discovered servers to use. Default: Auto. |
| **Auto-Add Servers** (`Auto_Allow_Servers`) | bool | `true` | Add discovered instances without asking. Default: ON - recommended: leave ON on trusted networks. |
| **Install Bonjour (QR)** (`Show_ZeroConf_QR`) | action button | (empty) | Shows a QR to install Bonjour (`utilities.py Show_ZeroConf_QR`). Show a QR to install Bonjour on Windows. Tip: Needed for zero-config discovery. |

## Integrations

| Setting | Type | Default | Description |
|---|---|---|---|
| **Allow AI Integration** (`Allow_Artificial_Intelligence`) | bool | `false` | Warning: AI features may incur API costs. Default: OFF - enable at your own discretion. |
| **OpenRouter API Key** (`Open_Router_APIKEY`) | text (hidden input) | (empty) | Key for OpenRouter AI services. Default: None (required for AI). Tip: Get one at openrouter.ai. |
| **Contextual Model** (`Generative_Contextual_Model`) | action button | `google/gemma-4-26b-a4b-it:free` | Opens the contextual model picker (`intergration.py getContextModels`). AI model used for contextual logo generation. Default: gemma 4 (free). |
| **Generate Artwork** (`Enable_Generative_Artwork`) | bool | `false` | Use AI to generate channel artwork. Default: OFF. |
| **Image Model** (`Generative_Image_Model`) | action button | `google/gemini-3.1-flash-lite-image` | Opens the image model picker (`intergration.py getImageModels`). AI model used for image generation. Default: gemini flash lite image. |
| **Artwork Style** (`Generative_Image_Style`) | text | `"Design a clearlogo for this channel: a distinctive, uncluttered logo built around a bold, iconic typeface that reads instantly at small sizes and overlays cleanly on video with minimal visual impact."` | Describes how you want your generated logos to look - style, colors, and mood. These attributes shape each logo the AI creates. Default: Built-in clearlogo prompt. Tip: The channel name, theme, and rendering format are handled automatically, so just describe the look you want. |

## Miscellaneous

| Setting | Type | Default | Description |
|---|---|---|---|
| **Utility Menu** (`Utility_MENU`) | action button | (empty) | Opens the utilities menu (`utilities.py Show_Menu`). Open the utilities menu. Tip: Access tools and helpers. |
| **Show Welcome** (`Show_Welcome_QR`) | action button | (empty) | Shows the welcome QR (`utilities.py Show_Welcome_QR`). Show the welcome QR after updates. Default: ON. |
| **Show Changelog** (`Show_Changelog`) | action button | (empty) | Shows the changelog (`utilities.py Show_Changelog`). Show what's new after an update. Default: ON. |
| **Support Forum** (`Show_Support_QR`) | action button | (empty) | Shows a support-forum QR (`utilities.py Show_Support_QR`). Show a QR to the support forum. Tip: Get help from the community. |
| **Project Wiki** (`Show_Wiki_QR`) | action button | (empty) | Shows a wiki QR (`utilities.py Show_Wiki_QR`). Show a QR to the PseudoTV Live wiki. Tip: Full documentation. |
| **Remote UI** (`Show_Remote_UI`) | action button | (empty) | Shows a remote-UI QR (`utilities.py Show_Remote_UI`). Show a QR to open the remote web UI. Tip: Control PseudoTV from a browser. |
| **Enable Debug Logging** (`Debug_Enable`) | bool | `true` | Notice: Writes detailed debug info to kodi.log. Default: ON - disable unless troubleshooting. |
| **Debug Level** (`Debug_Level`) | select | `0` (0 = LOGDEBUG, 1 = LOGINFO, 2 = LOGWARNING, 3 = LOGERROR, 4 = LOGFATAL) | Minimum level logged. Default: LOGERROR - use LOGDEBUG when reporting bugs. (Help claims LOGERROR; the XML default is 0 = LOGDEBUG.) |
| **Submit Log** (`Run_Logger`) | action button | (empty) | Submits the log (`utilities.py Logger`). Upload a debug log for review. Tip: Sends to paste.kodi.tv. |
| **Submit Snapshot** (`Debug_Snapshot`) | action button | (empty) | Submits a debug snapshot (`utilities.py Debug_QR`). Upload a debug snapshot for review. Tip: Sends to paste.kodi.tv. |
| **Access Kodi Settings** (`Enable_Kodi_Access`) | bool | `true` | Allow PseudoTV to adjust Kodi settings. Default: ON - recommended: ON. |
| **Keep Debug Enabled** (`Debug_Keep_Enable`) | bool | `false` | Leave debug logging on after restart. Default: OFF - recommended: OFF except while collecting logs. |
| **Auto PVR Refresh** (`Enable_PVR_RELOAD`) | bool | `false` | Reload IPTV Simple after channel changes. Default: OFF - recommended: ON. |
| **Disable Cache** (`Disable_Cache`) | bool | `false` | Important: Turns off caching. Only for experts. Default: OFF. |
| **Export M3U/XMLTV/genres** (`Enable_File_Export`) | bool | `false` | Write pseudotv.m3u, pseudotv.xml, and genres.xml to the cache folder. Default: OFF - the guide is served from SQLite cache. Enable only for local-file PVR configs or external tools. |
| **Parallel Processing** (`Enable_Executor`) | bool | `false` | Speeds up builds and menu loading by running several tasks at once. Uses more CPU and memory. Enable on desktop PCs with 4+ cores and plenty of RAM. Keep off on low-power devices (Shield, Fire Stick, SoC boxes) - it can cause lockups and crashes there. Default: OFF - recommended: OFF on low-power devices, ON on desktop PCs with 4+ cores. |
| **Playback Timeout** (`Playback_Timeout`) | slider | `90` (range 30–120, step 15) | Seconds before retrying failed playback. Default: 90. |
| **Kodi API Delay** (`API_Delay`) | slider | `2` (range 0–30, step 1) | Seconds between Kodi API calls. Default: 2 - higher = more stable, slower; recommended: keep 2 unless API errors appear. |
| **API Timeout** (`API_Timeout`) | slider | `90` (range 15–120, step 1) | Seconds to wait for a Kodi API reply. Default: 90. |

## Settings that are hidden until something else is on

46 of the 101 settings carry `<dependencies>` and only appear (or only become editable) when another setting or system condition holds:

| Setting | Visible/enabled only when |
|---|---|
| `Update_Status` | Visible: `Update_Status` is not the plain string `None` |
| `Open_Manager` | Visible: `Enable_Autotune` = false |
| `Default_Channels` | Visible: `Enable_Autotune` = false AND window property `plugin.video.pseudotv.live.has.Enabled_Servers` contains `true` |
| `Export_Channels` | Visible: window property `plugin.video.pseudotv.live.has.Channels` contains `true` |
| `Import_Channels` | Visible: window property `plugin.video.pseudotv.live.has.Backup` contains `true` |
| `Launch_NodeEditor` | Enabled: `plugin.library.node.editor` installed AND enabled |
| `Launch_IPTVSimple` | Enabled: `pvr.iptvsimple` installed AND enabled |
| `Build_Filler_Folders` | Enabled: `Enable_Fillers` = true |
| `Disable_Trakt` | Visible: `script.trakt` installed AND enabled |
| `OnNext_Mode` | Visible: `Overlay_Enable` = true |
| `OnNext_Position_XY` | Visible: `Overlay_Enable` = true AND `OnNext_Mode` > 0 AND `OnNext_Mode` < 3 |
| `Enable_OnInfo` | Visible: `Overlay_Enable` = true |
| `Replay_Percentage` | Visible: `Overlay_Enable` = true |
| `Enable_ChannelBug` | Visible: `Overlay_Enable` = true |
| `ChannelBug_Transparency` | Visible: `Overlay_Enable` = true AND `Enable_ChannelBug` = true |
| `ChannelBug_Color` | Visible: `Overlay_Enable` = true AND `Enable_ChannelBug` = true; Enabled: `System.BuildVersion` contains `20` |
| `Force_Diffuse` | Visible: `Overlay_Enable` = true AND `Enable_ChannelBug` = true (note: its `parent` is `ChannelBug_Color`, but the visibility check is on `Enable_ChannelBug`) |
| `Channel_Bug_Position_XY` | Visible: `Overlay_Enable` = true AND `Enable_ChannelBug` = true |
| `Store_Duration` | Visible: `Duration_Type` = 1 |
| `Interleave_Repeat` | Visible: `Interleave_Set` > 0 |
| `Enable_Even_Force_Episode` | Visible: `Enable_Even` > 0 AND `Enable_Even_Force_Random` = false |
| `Enable_Even_Force_Random` | Visible: `Enable_Even` > 0 AND `Enable_Even_Force_Episode` = false |
| `Enable_Preroll` | Enabled: `Enable_Fillers` = true |
| `Random_Pre_Chance` | Enabled: `Enable_Preroll` != 0 |
| `Resource_Bumpers` | Enabled: `Enable_Preroll` != 0 |
| `Resource_Ratings` | Enabled: `Enable_Preroll` != 0 |
| `Enable_Postroll` | Enabled: `Enable_Fillers` = true |
| `Random_Post_Chance` | Enabled: `Enable_Postroll` != 0 |
| `Resource_Adverts` | Enabled: `Enable_Postroll` != 0 |
| `Resource_Trailers` | Enabled: `Enable_Postroll` != 0 |
| `Include_Trailers_KODI` | Enabled: `Enable_Postroll` != 0 |
| `Include_Extras_KODI` | Enabled: `Enable_Postroll` != 0 |
| `TCP_PORT` | Visible: `Debug_Enable` = true |
| `Select_server` | Enabled AND visible: window property `plugin.video.pseudotv.live.has.Servers` contains `true` |
| `Auto_Allow_Servers` | Enabled AND visible: window property `plugin.video.pseudotv.live.has.Servers` contains `true` |
| `Show_ZeroConf_QR` | Visible: `ZeroConf_Status` = `[COLOR=red][B]Offline[/B][/COLOR]` AND `System.Platform.Windows` |
| `Open_Router_APIKEY` | Visible: `Allow_Artificial_Intelligence` = true |
| `Generative_Contextual_Model` | Visible: `Allow_Artificial_Intelligence` = true |
| `Enable_Generative_Artwork` | Visible: `Allow_Artificial_Intelligence` = true |
| `Generative_Image_Model` | Visible: `Allow_Artificial_Intelligence` = true AND `Enable_Generative_Artwork` = true |
| `Generative_Image_Style` | Visible: `Allow_Artificial_Intelligence` = true AND `Enable_Generative_Artwork` = true |
| `Show_Remote_UI` | Enabled: `Remote_Status` = `[COLOR=green][B]Online[/B][/COLOR]` |
| `Debug_Level` | Visible: `Debug_Enable` = true |
| `Run_Logger` | Visible: `Debug_Enable` = true |
| `Debug_Snapshot` | Visible: `Debug_Enable` = true |
| `Enable_PVR_RELOAD` | Enabled: `pvr.iptvsimple` installed AND enabled |

Note that several status fields compare against coloured markup strings exactly — `Show_ZeroConf_QR` requires `ZeroConf_Status` to be `[COLOR=red][B]Offline[/B][/COLOR]` character for character, and `Show_Remote_UI` requires `Remote_Status` to be `[COLOR=green][B]Online[/B][/COLOR]`. These only appear when the runtime status matches those strings precisely; the runtime code writes the colour markup into the same setting fields.

## Read-only and locked settings

Always greyed out (`<enable>false</enable>`):

- `Min_Days`, `Max_Days`, `OSD_Timer` (Options → Guide & OSD)
- `Remote_NAME`, `Remote_M3U`, `Remote_XMLTV`, `Remote_GENRE` (Multi-room → Server Information)

Status-display buttons with an empty `<data/>` (they show live state and do nothing when pressed):

- `Update_Status` (Channels)
- `Remote_Status` (Multi-room → Server Information)

(`ZeroConf_Status` is also a status field, but its button is live: it runs `multiroom.py Enable_ZeroConf`.)

## Buttons that launch things

| Setting | What it runs |
|---|---|
| `Open_Manager` | Opens the Channel Manager (`context_create.py open_manager`) |
| `Default_Channels` | Opens the channel list selector (`utilities.py select`) |
| `Export_Channels` | Runs the channel export (`backup.py Export_Channels`) |
| `Import_Channels` | Runs the channel import (`backup.py Import_Channels`) |
| `Launch_SmartplaylistEditor` | Opens Kodi's video playlists window (`ActivateWindow(10025,"library://video/playlists.xml/")`) |
| `Launch_NodeEditor` | Opens the Node Editor addon (`ActivateWindow(10001,plugin://plugin.library.node.editor)`) |
| `Launch_LiveSettings` | Opens Kodi's PVR & Live TV settings (`ActivateWindow(10021)`) |
| `Launch_IPTVSimple` | Opens IPTV Simple settings (`Addon.OpenSettings(pvr.iptvsimple)`) |
| `OnNext_Position_XY` | Opens the OnNext position mover (`utilities.py Move_OnNext`) |
| `Channel_Bug_Position_XY` | Opens the channel bug position mover (`utilities.py Move_Channelbug`) |
| `ZeroConf_Status` | Toggles ZeroConf discovery (`multiroom.py Enable_ZeroConf`) |
| `Select_server` | Opens the server picker (`multiroom.py Select_Servers`) |
| `Show_ZeroConf_QR` | Shows a Bonjour install QR (`utilities.py Show_ZeroConf_QR`) |
| `Generative_Contextual_Model` | Opens the contextual model picker (`intergration.py getContextModels`) |
| `Generative_Image_Model` | Opens the image model picker (`intergration.py getImageModels`) |
| `Utility_MENU` | Opens the utilities menu (`utilities.py Show_Menu`) |
| `Show_Welcome_QR` | Shows the welcome QR (`utilities.py Show_Welcome_QR`) |
| `Show_Changelog` | Shows the changelog (`utilities.py Show_Changelog`) |
| `Show_Support_QR` | Shows a support-forum QR (`utilities.py Show_Support_QR`) |
| `Show_Wiki_QR` | Shows a wiki QR (`utilities.py Show_Wiki_QR`) |
| `Show_Remote_UI` | Shows a remote-UI QR (`utilities.py Show_Remote_UI`) |
| `Run_Logger` | Submits the log (`utilities.py Logger`) |
| `Debug_Snapshot` | Submits a debug snapshot (`utilities.py Debug_QR`) |

(`User_Folder`, `Resource_Logos`, `Resource_Bumpers`, `Resource_Ratings`, `Resource_Adverts`, and `Resource_Trailers` open Kodi's built-in path/addon pickers rather than addon scripts.)

## Notes

- `settings.xml` uses the Kodi 19+ (`version="1"`) format: one `<section>`, seven `<category>` tabs, nested `<group>`/`<setting>` elements.
- Platform-gated: `Show_ZeroConf_QR` is only visible on Windows (`System.Platform.Windows`).
- Kodi-version-gated: `ChannelBug_Color` is only enabled when `System.BuildVersion` contains `20` (Kodi Nexus).
- Dangling `parent` attributes (no setting with that id exists in the file):
  - `Import_Channels` has `parent="Backup_Channels"` — no setting id `Backup_Channels` exists; the nearest real id is `Export_Channels` (whose label is "Backup Channels").
  - `Launch_SmartplaylistEditor` has `parent="33138"` — that is a string id (its own help text), not a setting id.
- Help text whose stated default disagrees with the `default=` attribute:
  - `Debug_Level`: help (#33002) says "Default: LOGERROR", but `default="0"` = LOGDEBUG.
  - `Enable_Preroll`: help (#33017) says "Default: OFF", but `default="-1"` = Auto.
  - `User_Folder`: help (#33012) says "Default: OFF - recommended: ON", but the default is a path.
  - `Update_Status`: help (#33033) says "Default: Auto", but the default element is empty.
- The dialog `<heading>` for `TCP_PORT` references string id `40001`, which is not present in `strings.po`.
- The addon-pick dialog headings for `Resource_Bumpers`, `Resource_Adverts`, and `Resource_Trailers` all reuse label `30068` ("Nearest Holiday"), while `Resource_Ratings` uses `30069` ("Third-Party") — likely copy-paste in the XML.
- Setting levels 0–3 map to Kodi's settings-level filter (Standard/Advanced/Expert), so several options (e.g. `Min_Days`, `ChannelBug_Transparency`, `API_Timeout`) only show with a higher settings level selected.

## See also

- [Rules](Rules) — per-channel overrides of these global defaults
- [Channel Manager](Channel-Manager)
- [Web Channel Manager](Web-Channel-Manager)
