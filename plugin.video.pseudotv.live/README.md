![](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Artwork/master/PseudoTV%20Live/Flat/PTVL%20-%20Metro%20-%20Fanart%20(1).png)

# PseudoTV Live for Kodi™ (Matrix):

## What is it?:

PseudoTV Live transforms your Kodi Library and Sources (Plugins, UPnP, etc...) into a broadcast or cable TV emulator, complete with configurable channels. UI Provided by Kodis PVR frontend via IPTV Simple.

[Changelog](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/changelog.txt)

[Forum: Kodi.TV](https://forum.kodi.tv/showthread.php?tid=355549)

[Discussion: Kodi.TV](https://forum.kodi.tv/showthread.php?tid=346803)

[![License](https://img.shields.io/github/license/PseudoTV/PseudoTV_Live?style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/blob/master/LICENSE)
[![Codacy Badge](https://img.shields.io/codacy/grade/efcc007bd689449f8cf89569ac6a311b.svg?style=flat-square)](https://www.codacy.com/app/PseudoTV/PseudoTV_Live/dashboard)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/PseudoTV/PseudoTV_Live.svg?color=red&style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/commits?author=Lunatixz)
[![Kodi URL](https://img.shields.io/badge/Supports-Kodi%2019-blue.svg?style=flat-square)](https://kodi.tv/download)
[![Kodi Donate](https://img.shields.io/badge/Donate-Kodi-blue.svg?style=flat-square)](https://kodi.tv/contribute/donate)
[![Lunatixz Donate](https://img.shields.io/badge/Donate-Lunatixz-blue.svg?style=flat-square)](https://www.buymeacoffee.com/Lunatixz)
[![Twitter URL](https://img.shields.io/twitter/follow/PseudoTV_Live.svg?color=blue&label=%40PseudoTV_Live&style=flat-square)](https://twitter.com/PseudoTV_Live)

# Special Thanks:
- @xbmc If you are enjoying this project please donate to Kodi!
- @phunkyfish for his continued work and help with IPTV Simple.
- @IAmJayFord for awesome PseudoTV Live Icon/Fanart sets.
- @preroller for fantastic PseudoTV Live Bumpers.

------------

# Features:
- Predefined Channels based on your Kodi library content; categorized by: 


- Automatic Channel logos, sourced from Kodi resource packs.

- Optional video overlay to display channel bug and other pending features.

- IPTV-Simple VOD support. Watch any EPG event (Past/Present/Future) directly via "Play Programme" context menu option.

- "Play from here" context menu  option queues channel as a playlist from any starting position.

- "More Info..." context menu option, displays detailed media information.

- Custom Channel grouping & genre colors.

- Third-Party M3U/XMLTV Importing with channel number collision logic.

- Efficient meta parsing & pagination.

- Media metadata parsing for "accurate" duration/runtime values.

- Option to save "accurate" (Parsed) duration meta to your Kodi database.

- "on the fly" channel creation, with automated background building.

- Ease of use; User Interface provided by Kodis PVR frontend.

- Music Genre PVR "Radio" Channels.

- Multi-Room channel configurations w/Automatic client detection.

- "Auto Tuning" Automatic channel creation from "Pre-Defined" configurations.

- Your choice of "Playback Methods". See post below for details.

- Smart Seeking. See below for details.

- "User-Defined" Channel Manager, create custom channels from any source available to Kodi. ie. Plugins, UPNP, Nodes, Smart playlists.

- Seasonal Holiday Channel, See changelog above for details.

- "Recommended Channels" & "Recommended Services" Plugins preconfigured for easy import into PseudoTV Live.

- Many more...

------------

# Supported Plugins:
*All plugins are supported by PseudoTV Live through the channel manager. The list below contains configuration free channels.

[PlutoTV](https://forum.kodi.tv/showthread.php?tid=315513)

[ChannelsDVR](https://forum.kodi.tv/showthread.php?tid=334947)

[Locast](https://forum.kodi.tv/showthread.php?tid=357406)

[HDhomerun Simple](https://forum.kodi.tv/showthread.php?tid=327117)

[AiryTV](https://forum.kodi.tv/showthread.php?tid=361486)

[Discovery+](https://forum.kodi.tv/showthread.php?tid=340055)

------------

# Settings:

## Playback Method: 

1. PVR Callback - This method keeps Kodi believing you are using a Live feed from the PVR backend. Pros| Kodi PVR UI and Widget updates. Near infinite channel playback. Cons| Slower channel content changes. (1-60secs. depending on your system). If "Overlay" is enabled in settings; and active during content change you will be met with a custom background. (Currently static).

2. Playlist - Standard Kodi playlist queue (not to be confused with a smart playlist). Pros| Channel content changes quickly. Cons| Kodi does not treat playback as PVR channel, Playlist queues are finite.

## Seek tolerance (Smart Seeking):

Adjusting seek tolerance (in seconds) adds a buffer at the beginning of media that is currently selected to play and which includes an offset for a "Pseudo" Live effect. The greater the number the more it ignores the time differential between "live" and "load" times.
ex. If after a show ends your next show which should start at the beginning starting a few seconds into the future; due to a lag in loading time. Raising the seek tolerance well remedy this... 0 disables tolerance.

## Seek Threshold(Smart Seeking):

Adjusting seek threshold(percentage). threshold to which the current content can be played back before dismissing for the next queue. Ex. The content you select to play maybe near the end instead of loading two seconds of credits; PseudoTV Live will tune the next show automatically. 100% disables threshold (content played till the end).

## Parse for Accurate Duration Meta:

1. "Prefer Kodi Library" - Duration meta collected from the values provided by your metadata provider. ie. TVDB, TMDB, etc... Pros: Faster background channel building, Cons: Usually inaccrate, rounded values.

2. "Prefer File Metadata" - Media files are parsed individually for real runtimes. Pros: Accurate EPG guide times, Cons: Slower background channel building. File extensions supported `.avi,.mp4,.m4v,.3gp,.3g2,.f4v,.mov,.mkv,.flv,.ts,.m2ts,.strm`

	`.strm` files require matching `.nfo` sharing the same name. ex. `foobar movie,the.strm` & `foobar movie,the.nfo` Supported nfo parameters `runtime,duration,durationinseconds`. *note `runtime,duration` in minutes.

	*see "Save Accurate Duration to Kodis Library"

## Save Accurate Duration to Kodis Library:

- Inorder to reduce parsing times when using "Prefer File Metadata" PseudoTV Live can store the new accurate duration meta to Kodis library, there are no downsides to this process except for extra cpu usage. If you notice performance penalties when enabled, disable it... There is a fallback 28 day cache to avoid unnecessary file parsing. 

## Imports:

Imports are considered "third-party" and are not treated as "PseudoTV" channels. Channel configurations, channel numbering, onscreen overlays are all disabled. Imports are 1:1 m3u/xmltv imports with the exception of channel numbers which maybe altered as described below.

### M3U
- Supports all [common m3u paramters](https://github.com/kodi-pvr/pvr.iptvsimple#m3u-format-elements "common m3u paramters") including KODIPROP. File or URL must meet minimum requirements: 

`#EXTINF:0 tvg-id="" tvg-name="" tvg-chno="" ,ChannelName`

`http://path-to-stream/live/channel-feed`


- "Filter channels using a common id (Optional)." - Inorder for this feature to work the provided m3u/xmltv must contain channel `tvg-id` formated with source indicators. ex. `NBC4@zap2it.com`,`CBS2@tvguide.com`. If you would like to import only `zap2it.com` sources, enter `@zap2it.com`.

### XMLTV 
- requires one of the two timestamps:
	1. `%Y%m%d%H%M%S` - Local Time 

	1. `%Y%m%d%H%M%S +%z` - UTC Time with Offset

------------

# General Information:

## - Channel Sharing (Multi-Room):

For "Multi-Room", Select an instance of Kodi/PseudoTV Live that will act as your primary "server". Under PseudoTV Lives settings "Options" change the file location to a shared path. Client-side, install PseudoTV Live, Under PseudoTV Lives settings "Options" change the file location to a shared path. Enable "Client Mode" *Optional, PseudoTV can automatically detect client mode however, if you would like to force the mode, select in options. *All instances of Kodi must be configured for sharing. ie. Shared/Mapped Drives and Central Database. You can configure channel lineups from any instance of PseudoTV Live, however only your "Server" will build/update channels. 

1. https://kodi.wiki/view/MySQL 

2. https://kodi.wiki/view/Path_substitution 

After creating channels you will find a folder called "logos" in the same directory selected in settings. Place custom logos here!! They will override logos PseudoTV Live has found for you. The image must be *.png and is case sensitive to the channel name. ex. Channel "Foo Bar" searchs for a matching logo "Foo Bar.png"

## - Channel Ordering (Numbering):

### - Number Assignment:

For full control of channel numbering it is recommend users create "Custom" user-defined channels. Channels 1-999 are reserved to users, anything higher is reserved and auto assigned to pre-defined channels.

Pre-defined channels yield no control over numbering; numbers are auto assign by type (ranging from channels 1000-9999), using lowest available number by type.

Imported M3Us and "Recommend Services" auto assigned by a multiplier based on the amount of imports staring at channel 10000, then appending the imports channel number. 

For example importing two M3Us/services. Import one will start at 10000, the other 20000. ex. If you are importing a m3u that contains channel 4.1, and 11. They will appear as 10004.1 and 10011. 

Each import is limited to 9999 (assuming each channel is an interger. Sub-Numbering, ie. floats ex. 4.1 extend the amount of possible imports) channels per import with a total of 9 total imports allowed.

- Channel Range:
-- `1-999` User-defined
-- `1000-9999` Pre-defined
-- `10000-99999` Imports (Third-party m3u and recommend services)

### - EPG Ordering:

#### - IPTV Simple Settings:

"only number by order" must be disbled if you would like to respect the channel numbers assigned in PseudoTV Live.
*NOTE: PseudoTV Live automatically applies the optimal settings to IPTV Simple in-order to maximize the user experience.

#### - Kodi PVR & LiveTV Settings:

If you want the exact channel numbers from PseudoTV Live to reflect onscreen, you will have to enable "Use channel order from backend". While in settings "Synchronize channel groups with backend" should also be enabled.
*NOTE: changes will require users to clear data from the same PVR settings menu

------------

# FYI & Known Issues:

- If content is ignored/not added to the guide or episodes start/end before their assigned EPG time ie. guide times are off. Under "Parse for Accurate Duration Meta" select "Prefer File Metadata". Kodis library usually contain rounded duration/runtime values which will yield inaccurate guide times. Parsing the file directly grabs the actual duration value. If content is ignored, it is usually because Kodis library contains no duration/runtime information. Again, parsing the file resolves this problem. If however both your library and file contain no duration meta content will remain be ignored.

- Multiple PVR backends supported; However, you must set "Client Priorities"  under Kodis "PVR & LiveTV" settings. Follow the directions below to clear guide data after setting priority.

- Blank EPG cells; Kodis EPG data is malformed; Enter Kodis "PVR & LiveTV" settings, navigate to "Guide" and click "Clear data".

- Context Menu may be unavailable while viewing EPG.  To enable go do Kodis "PVR & LiveTV" then "Guide" and changing the default select action to "show context menu".

- Some video sources (i.e. plugins, UPnP) do not support seeking, which could cause playback to fail. Try loading the content via Context Menu ("Play Programme","Play from here").

- All content must include duration details either embedded into the file or via Kodis Library.

- Settings are dim and unelectable. Some settings require content to operate (ex. Selecting TV Networks require your library have TV Content). There are also actions that can not simultaneously run while PseudoTV background tasks are performed (ie. If you wait for tasks to finish, settings will become selectable). If you experience an error message and your settings are now unselectable. Either reboot Kodi, or disable/enable PseudoTV Live to temporarily fix, and be sure to report your error with a log.

- Enable "Channel surfing" (Only available in PVR Playback mode). Navigate Kodis settings, find PVR Live TV settings and Playback then disabled confirm channel switches by pressing "ok".

- "One Click" channel playback... Navigate to Kodis PRV & Live TV settings and change selection action.

- Channel Manager Colors, Dim = Unused, White = User-defined, Orange = Pre-defined, Red = Failed (Channel may not have content / appear in the guide and/or PseudoTV hasn't built the channel yet.)

- You can not skip during playback... unless you are using the "Playlist" playback mode.
  However, you can play any single show from the guide at any time or start playlist playback from any given position in the guide using the available context menu items.
  Play programme == Play single show from the start.
  Play from here == Queues guide content from this position and starts playback.

  ![Play Programme](https://i.imgur.com/ykLfzu6.png "Play Programme")
  ![Play From Here](https://i.imgur.com/ZSZzpmy.png "Play From Here")

------------

# Plugin Developer Integration.
- PseudoTV Live features two integration methods. 

1. "Recommend Services" which is a full m3u/xmltv import provide by [IPTV Manager](https://github.com/add-ons/service.iptv.manager) or a local generated m3u/xmltv set. *see imports

2. "Recommend Channels" allows VOD content to fully intergrate into PseudoTV Live.
Inorder for a plugin to announce itself to PseudoTV Live it must run a "Beacon" service. Examples can be found below. 

[Beacon Asset Example](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/asset.json)

[Pluto TV Example](https://github.com/Lunatixz/KODI_Addons/blob/master/plugin.video.plutotv/pseudotv_recommended.py)

[Locast Example](https://github.com/Lunatixz/KODI_Addons/blob/master/plugin.video.locast/pseudotv_recommended.py)
