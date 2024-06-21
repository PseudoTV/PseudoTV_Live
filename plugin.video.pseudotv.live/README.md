![](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Artwork/master/PseudoTV%20Live/Flat/PTVL%20-%20Metro%20-%20Fanart%20(1).png)

# PseudoTV Live for Kodi™

## What is it?:

PseudoTV Live transforms your Kodi Library and Sources (Plugins, UPnP, etc...) into a broadcast or cable TV emulator, complete with configurable channels. UI Provided by Kodis PVR frontend via IPTV Simple.

[Changelog](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/changelog.txt)

[Forum: Kodi.TV](https://forum.kodi.tv/showthread.php?tid=355549)

[Discussion: Kodi.TV](https://forum.kodi.tv/showthread.php?tid=346803)

[![PseudoTV Live](https://opengraph.githubassets.com/b515e27858c045536f54116a571f79bda90cde077f4a9e87af8908cb0801b6a2/PseudoTV/PseudoTV_Live)](https://opengraph.githubassets.com/b515e27858c045536f54116a571f79bda90cde077f4a9e87af8908cb0801b6a2/PseudoTV/PseudoTV_Live)

[![License](https://img.shields.io/github/license/PseudoTV/PseudoTV_Live?style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/blob/master/LICENSE)
[![Codacy Badge](https://img.shields.io/codacy/grade/efcc007bd689449f8cf89569ac6a311b.svg?style=flat-square)](https://www.codacy.com/app/PseudoTV/PseudoTV_Live/dashboard)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/PseudoTV/PseudoTV_Live.svg?color=red&style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/commits?author=Lunatixz)
[![Kodi URL](https://img.shields.io/badge/Supports-Kodi%2019+-blue.svg?style=flat-square)](https://kodi.tv/download)
[![Kodi Donate](https://img.shields.io/badge/Donate%20to-Kodi-blue.svg?style=flat-square)](https://kodi.tv/contribute/donate)
[![Lunatixz Coffee](https://img.shields.io/badge/Buy%20%20Coffee-Lunatixz-blue.svg?style=flat-square)](https://www.buymeacoffee.com/Lunatixz)
[![Lunatixz Patreon](https://img.shields.io/badge/Patreon-Lunatixz-blue.svg?style=flat-square)](https://www.patreon.com/pseudotv)
[![Lunatixz Paypal](https://img.shields.io/badge/Paypal-Lunatixz-blue.svg?style=flat-square)](https://paypal.me/Lunatixz)

# Special Thanks:
- @xbmc If you are enjoying this project please donate to Kodi!
- @phunkyfish for his continued work and help with IPTV Simple.
- @IAmJayFord for awesome PseudoTV Live Icon/Fanart sets.
- @preroller for fantastic PseudoTV Live Bumpers.

### License

* [GNU GPL v3](http://www.gnu.org/licenses/gpl.html)
* Copyright 2009-2023


------------

# Features:
- "Autotuned" Channels based on your Kodi library; categorized by: `"TV Networks", "TV Shows", "TV Genres", "Movie Genres", "Movie Studios", "Mixed Genres", "Playlists", "Music Genres", "Mixed"`

- Automatic Channel logos, Rating, bumpers; sourced from Kodi resource packs.

- Optional video overlay to display channel bug and other informative information.

- IPTV-Simple VOD support. Watch any EPG event (Past/Present/Future) directly via "Play Programme" context menu option.

- "Play from here" context menu option; Queues channel content as a playlist from any starting position.

- "More Info context menu option, displays detailed media information.

- "Browse" context menu option, displays channel content through standard Kodi UI.

- "Find" context menu option, searches Kodi Library for matching media.

- Custom Channel grouping & genre colors.

- Efficient meta parsing & pagination.

- Media metadata parsing for "accurate" duration/runtime values.

- Option to save "accurate" (Parsed) duration meta to your Kodi database.

- Option to disable Trakt scrobbling and rollback media playcount and resume points for passive viewing.

- "on the fly" channel creation, with automated background building.

- Ease of use; User Interface provided by Kodi PVR frontend.

- Music Genre PVR "Radio" Channels.

- Multi-Room channel configurations w/Client pairing via bonjour network announcement.

- Your choice of "Playback Methods". See post below for details.

- Smart Seeking. See below for details.

- Channel Manager, create custom channels from any source available to Kodi. ie. Plugins, UPNP, Nodes, Smart playlists.

- Seasonal Holiday Channel, See changelog for details.

- "Recommended Channels" & "Recommended Services" Plugins preconfigured for easy import into PseudoTV Live.

- "Add to PseudoTV Live" Content option allows quick channel creation from any Kodi source.

- Much more...

------------

# Supported Plugins: (Temporarily unavailable)
*All plugins are supported by PseudoTV Live through the channel manager. The list below contains configuration free channels.

[PlutoTV](https://forum.kodi.tv/showthread.php?tid=315513)

[ChannelsDVR](https://forum.kodi.tv/showthread.php?tid=334947)

[HDhomerun Simple](https://forum.kodi.tv/showthread.php?tid=327117)

------------

# Settings:

## Playback Method: 

1. PVR Callback - This method keeps Kodi believing you are using a Live feed from the PVR backend. Pros| Kodi PVR UI and Widget updates. Near infinite channel playback. Cons| Slower channel content changes. (1-60secs. depending on your system). If "Overlay" is enabled in settings; and active during content change you will be met with a custom background. (Currently static).

2. Playlist - Standard Kodi playlist queue (not to be confused with a smart playlist). Pros| Channel content changes quickly. Cons| Kodi does not treat playback as PVR channel, Playlist queues are finite.

## Seek tolerance (Smart Seeking):

Adjusting seek tolerance (in seconds) adds a buffer at the beginning of media that is currently selected to play and which includes an offset for a "Pseudo" Live effect. The greater the number the more it ignores the time differential between "live" and "load" times.
ex. If after a show ends your next show which should start at the beginning starting a few seconds into the future; due to a lag in loading time. Raising the seek tolerance well remedy this... 0 disables tolerance.

## Seek Threshold(Smart Seeking):

Adjusting seek threshold(percentage). threshold to which the current content can be played back before dismissing for the next queue. Ex. The content you select to play maybe near the end instead of loading two seconds of credits; PseudoTV Live will tune the next show automatically. 100% disables threshold (content played till the end).

## Parse for Accurate Duration Meta:

1. "Prefer Kodi Library" - Duration meta collected from the values provided by your metadata provider. ie. TVDB, TMDB, etc... Pros: Faster background channel building, Cons: Usually inaccrate, rounded values.

2. "Prefer File Metadata" - Media files are parsed individually for real runtimes. Pros: Accurate EPG guide times, Cons: Slower background channel building. File extensions supported `.avi,.mp4,.m4v,.3gp,.3g2,.f4v,.mov,.mkv,.flv,.ts,.m2ts,.strm`

	`.strm` files require matching `.nfo` sharing the same name. ex. `foobar movie,the.strm` & `foobar movie,the.nfo` Supported nfo parameters `runtime,duration,durationinseconds`. *note `runtime,duration` in minutes.

	*see "Save Accurate Duration to Kodis Library"

## Save Accurate Duration to Kodis Library:

- In-order to reduce parsing times when using "Prefer File Metadata" PseudoTV Live can store the new accurate duration meta to the Kodi library, there are no downsides. If you notice performance penalties when enabled, disable it... There is a fallback 28 day cache to avoid unnecessary file parsing. 

## Recommended Services: (Temporarily unavailable)

Recommended Services are considered "third-party" and are not treated as "PseudoTV" channels. Channel configurations, channel numbering, onscreen overlays are all disabled. Imports are 1:1 m3u/xmltv imports with the exception of channel numbers which maybe altered as described below.

## Options:
    
- Centralized file location: Location to store PseudoTV Live M3U/XMLTV and other shared resources. ie. Playlists, Nodes and Channel Logos.
    
------------

# General Information:


## - Channel Logos:

Logo's are cached and may not be refreshed immediately....

Default Logo location - `/userdata/plugin.video.pseudotv.live/cache/logos`. *Location associated with Centralized File Location.

Filenames must match the channel name exactly as it appears in the guide. Supported formats `*.jpg,*.png,*.gif`

If no logo is found, PseudoTV Live will parse for a matching logo in the following folder order.

    `/addons/plugin.video.pseudotv.live/resources/images`, 

    `*resource.images.pseudotv.logos`, 

    ** [`resource.images.studios.white`, `resource.images.studios.coloured`], `resource.images.moviegenreicons.transparent`, `resource.images.musicgenreicons.text`

[Resource packs](https://github.com/PseudoTV/PseudoTV_Resources/blob/master/README.md) - Standard Kodi image resource packs. 

## - Channel Sharing (Multi-Room):

### Server:

For "Multi-Room", Select an instance of Kodi/PseudoTV Live that will act as your primary "server". *All instances of Kodi must be configured for sharing. ie. Shared/Mapped Drives and Central Database (mySQL). Only your "Server" instance of PseudoTV Live will build/update channels. 

	1 https://kodi.wiki/view/MySQL 

	1 https://kodi.wiki/view/Path_substitution 

### Client:

Enable under "Multi-Room", select between two options.

	1 Remote URL - Use a remote url hosted by your server instance which can be selected in settings. *http://localhost:50001/pseudotv.m3u **http://localhost:50001/pseudotv.xml ***http://localhost:50001/genres.xml

	1 Network Folder - Select a shared network path same as configure on the server instance.

## - Channel Ordering (Numbering):

### - Number Assignment:

For full control of channel numbering it is recommend users create "Custom" user-defined channels. Channels 1-999 are reserved to users, anything higher is reserved and auto assigned to "Autotuned" pre-defined channels.

Pre-defined channels yield no control over numbering; numbers are auto assign by type (ranging from channels 1000-9999), using lowest available number by type.

"Recommend Services" auto assigned by a multiplier based on the amount of imports staring at channel 11000, then appending the imports channel number. 

For example importing two M3Us/services. Import one will start at 11000, the other 21000. ex. If you are importing a m3u that contains channel 4.1, and 11. They will appear as 11004.1 and 11011. 

Each import is limited to 9999 (assuming each channel is an interger. Sub-Numbering, ie. floats ex. 4.1 extend the amount of possible imports) channels per import with a total of 9 total imports allowed.

- Channel Range:
-- `1-999` User-defined
-- `1000-9999` Pre-defined (Autotuned)
-- `10000-99999` Imports (Third-party m3u and recommend services)

### - EPG Ordering:

#### - IPTV Simple Settings:

"only number by order" must be disabled if you would like to respect the channel numbers assigned in PseudoTV Live.
*NOTE: PseudoTV Live automatically applies the optimal settings to IPTV Simple in-order to maximize the user experience.

#### - Kodi PVR & LiveTV Settings:

If you want the exact channel numbers from PseudoTV Live to reflect onscreen, you will have to enable "Use channel order from backend". While in settings "Synchronize channel groups with backend" should also be enabled.
*NOTE: changes will require users to clear data from the same PVR settings menu

## - Channel Manager:

### - Color Legend:
- In-use (White)       - Existing channel configuration.
- Unused (Dim-Grey)    - Available for configuration.
- Favorite (Yellow)    - User Favorites.
- Radio (Cyan)         - User-defined Radio/Music channel.
- Un-editable (Orange) - Pre-defined or Parental Locked channels are displayed as "un-editable" within the manager.
- Warnings (Red)       - Indicates either a new channel that hasn't populated or an existing channel without content.

## - Fillers:
"Auto" - Attempts to fill the gap between the nearest 15min time block with a mix of adverts and trailers depending on user configuration.
"Random Filler" - Add content that does not match channels name or subject genre at random in-order to fulfill users configuration. 

- Rating   - MPAA video before a movie.
- Bumpers  - Bumper video before tv content.
- Adverts  - Commercials after content.
    "iSpot" - Internet adverts injected randomly between channel content.
- Trailers - Trailers after context and shuffled with adverts when applicable. 
    "Kodi Trailers" - Local trailers curated by subject genre and later used in matching genre channels.
    "IMDB Trailers" - Internet trailers curated by subject genre and either used in matching genre channels.

### Custom Fillers:
- Root folders have a chance for random placement on any channel.
- Subfolders must match channel name or genre type exactly, not cap sensitive.
- See resources [README.md](https://github.com/PseudoTV/PseudoTV_Resources/raw/master/README.md)


------------

# FYI & Known Issues:

- .mp4 files are not recommend there is a high probability PseudoTV Live will not properly parse its runtime.

- If you experience poor performance using PseudoTV Live; Try disabling "Accurate Duration" parsing, and setting "Playback Method" to playlists. 
  It is recommend on low power devices like AndroidTV/AppleTV to outsource channel building to a "server" instance of Kodi running on a PC; then configure all other Kodi instances as a client.

- If content is ignored/not added to the guide or episodes start/end before their assigned EPG time ie. guide times are off. Navigate to "Parse for Accurate Duration Meta" settings and select "Prefer File Metadata". 
  Media Meta sites like TMDB, TVDB usually contain rounded duration/runtime values which will yield inaccurate guide times. Parsing the file directly grabs the actual duration value. 
  If content is ignored, it is usually due to no duration/runtime information. Parsing the file resolves this problem. If however both your library and file contain no duration meta content will remain ignored.

- Blank EPG cells; Either Kodi EPG data is malformed; Enter Kodi settings "PVR & LiveTV", navigate to "Guide" and click "Clear data". or
  The xmltv file is outdated and PseudoTV Live will updated in the background in time...

- Context Menu may be unavailable while viewing EPG.  To enable go do Kodi "PVR & LiveTV" then "Guide" and changing the default select action to "show context menu".

- Some video sources (i.e. plugins, UPnP) do not support seeking, which could cause playback to fail or always start at the beginning. Try loading the content via Context Menu ("Play Programme","Play from here").

- All content must include duration details either embedded in the file or via Kodi Library.

- Settings are dim and unelectable. Some settings require content to operate (ex. Selecting TV Networks require your library have TV Content). There are also actions that can not simultaneously run while PseudoTV background tasks are performed (ie. If you wait for tasks to finish, settings will become selectable).

- Enable "Channel surfing" (Only available in PVR Playback mode). Navigate Kodi settings, find "PVR Live TV" settings and "Playback" then disabled "confirm channel switches by pressing "ok"".

- "One Click" channel playback... Navigate to Kodi "PVR & Live TV" settings and change "selection action".

- Channel Manager Colors, Dim = Unused, White = User-defined, Orange = Pre-defined, Red = Failed (Channel may not have content / appear in the guide and/or PseudoTV hasn't built the channel yet.)

- You can not skip ahead or time shift during linear playback... unless in "Playlist" playback.
    However, you can play any single show from the guide at any time or start playlist playback from any given position in the guide using the available context menu items.
    Play programme == Play single show from the start.
    Play from here == Queues guide content from this position and starts playback.

    ![Play Programme](https://i.imgur.com/ykLfzu6.png "Play Programme")
    ![Play From Here](https://i.imgur.com/ZSZzpmy.png "Play From Here")

- Channel surfing only works while in PVR CallbacK mode and during linear playback; VOD & Playlist playback exits the PVR.
  Repeated Back-to-Back channel surfing when "confirm channel switches by pressing "ok"" is disabled may crash Kodi. 
  This is due to a long existing bug related to Kodis busy dialog. https://github.com/xbmc/xbmc/pull/21563

- Content ordering defaults to 'random' for all content except TV which defaults to 'episode' ordering. 'Mixed" content ordering defaults to 'year' for Movies. This only applies to channels configured without sort/order method. Multi-Path channels will default to using a standard interleaving distribution. *see below for details.
 
    `#interleave multi-paths, while preserving sequence order`
    
    `#input  = [[1,2,3,4],[a,b,c,d],[A,B,C,D]]`
 
    `#output = [1, 'a', 'A', 2, 'b', 'B', 3, 'c', 'C', 4, 'd', 'D']`

- "Mixed" Content ie. TV & Movie Smartplaylists are unsupported in Kodi and its given type was designed for "Music" media. PseudoTV Live can use the "Mixed" type to allow mixed content. Create a "Mixed" type smartplaylist and select the `path, playlist or virtual folder` you'd like to use.

    #### How-To Create Mixed Smartplaylist:
    ![How-To Create Mixed Smartplaylist](https://i.imgur.com/MY7CO2p.mp4)
    
    1. Open Smartplaylist editor, Select "Mixed" Type. Enter playlist name and when prompted save the file.

	1. While in the "Mixed" smartplaylist navigate to playlist type select "TV", Enter a rule to select a "Path", "Virtualfolder" or "Playlist" with an inclusive operator of "is" or "contains".

	1. Navigate again to playlist type select "Movie" and repeat the steps above. Before leaving the editor switch playlist type back to "Mixed" and save.

- Adding "pvr://" as a Kodi video source can improve channel changing times on certain platforms by whitelisting the path for jsonrpc access. Follow the directions below and select "None" as your media type.
  https://kodi.wiki/view/Adding_video_sources
  
------------

# Plugin Integration for Developers.
It is recommend developers disable pagination on content and turn off listitems onscreen ui render when `xbmcgui.Window(10000).getProperty("PseudoTVRunning") == 'True'`.

- PseudoTV Live features two integration methods. 

1. "Recommend Services" Full m3u/xmltv import provide by [IPTV Manager](https://github.com/add-ons/service.iptv.manager). *see imports

    ![Recommend Services](https://i.imgur.com/YDcFfAn.png "Recommend Services")

2. "Recommend Channels" Integrate plugin paths to PseudoTV Live.

    In-order for a plugin to announce itself to PseudoTV Live; it must first run a "Beacon" service. Examples can be found below. 

    ![Recommend Channels](https://i.imgur.com/AsCpirW.png "Recommend Channels")

[Beacon Asset Example](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/asset.json)

[Crackle Example (VOD)](https://github.com/Lunatixz/KODI_Addons/blob/master/plugin.video.crackle/pseudotv_recommended.py)

[Pluto TV Example (Live & VOD)](https://github.com/Lunatixz/KODI_Addons/blob/master/plugin.video.plutotv/pseudotv_recommended.py)

## M3U
- Supports all [common m3u paramters](https://github.com/kodi-pvr/pvr.iptvsimple#m3u-format-elements "common m3u paramters") including KODIPROP. File or URL must meet minimum requirements: 

`#EXTINF:0 tvg-id="" tvg-name="" tvg-chno="" ,ChannelName`

`http://path-to-stream/live/channel-feed`


- "Filter channels using the `provider` parameter (Optional)." - In-order for this feature to work the provided m3u must contain the following example:

1. `provider` ex. `provider=Locast`,`provider=PlutoTV`. If you would like to import only `PlutoTV` sources, enter `PlutoTV`. For multiples enter `Locast|PlutoTV`

## XMLTV 
- requires one of the two timestamps:
	1. `%Y%m%d%H%M%S` - Local Time 

	1. `%Y%m%d%H%M%S +%z` - UTC Time with Offset
    
    