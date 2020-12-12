![](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Artwork/master/PseudoTV%20Live/Flat/PTVL%20-%20Metro%20-%20Fanart%20(1).png)

## PseudoTV Live:

PseudoTV Live acts similar to normal broadcast or cable TV, complete with multiple preset, user-defined channels and advanced channel management.

PseudoTV Live can integrate with all Kodi sources including various Kodi plugins ie. Plex, Netflix, etc.
Create rich, in-depth channels with the added feature to import existing M3U/XMLTV pairs.

[Forum](https://forum.kodi.tv/showthread.php?tid=355549)


[Discussion](https://forum.kodi.tv/showthread.php?tid=346803)


[Channel Configuration Example](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/channels.json)


#Settings:

Playback Method: 
1) PVR Callback - This method keeps Kodi believing you're using a Live feed from the PVR backend. Pros| Kodi PVR UI and Widget updates. Near infinite channel playback. Cons| Slower channel content changes. (1-60secs. depending on your system). If "Overlay" is enabled in settings; and active during content change you'll be met with a custom background. (Currently static).
2) Playlist - Standard Kodi playlist queue (not to be confused with a smart playlist). Pros| Channel content changes quickly. Cons| Kodi does not treat playback as PVR channel, Playlist queues are finite.

Seek tolerance (Smart Seeking):
Adjusting seek tolerance (in seconds) adds a buffer at the beginning of media that is currently selected to play and which includes an offset for a "Pseudo" Live effect. The greater the number the more it ignores the time differential between "live" and "load" times.
ex. If after a show ends your next show which should start at the beginning starting a few seconds into the future; due to a lag in loading time. Raising the seek tolerance well remedy this...

Seek Threshold(Smart Seeking):
Adjusting seek threshold(in seconds) adds a buffer at the end of media that is currently selected to play and which includes an offset for a "Pseudo" Live effect. The content you select to play maybe near the end instead of loading two seconds of credits; PseudoTV Live will tune the next show automatically.


#General Information:

For "Multi-Room", Select an instance of Kodi/PseudoTV Live that will act as your primary "server". Under PseudoTV Live's settings "Options" change the file location to a shared path. Client-side, install PseudoTV Live, Under PseudoTV Live's settings "Options" change the file location to a shared path. Enable "Client Mode" *Optional, PseudoTV can automatically detect client mode however, if you'd like to force the mode, select in options. *All instances of Kodi must be configured for sharing. ie. Shared/Mapped Drives and Central Database. You can configure channel lineups from any instance of PseudoTV Live, however only your "Server" will build/update channels. *https://kodi.wiki/view/MySQL **https://kodi.wiki/view/Path_substitution
After creating channels you'll find a folder called "logos" in the same directory selected in settings. Place custom logos here!! They will override logos PseudoTV Live has found for you. The image must be *.png and is case sensitive to the channel name. ex. Channel "Foo Bar" search's for a matching logo "Foo Bar.png"