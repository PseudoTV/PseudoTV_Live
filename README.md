PseudoTV Live
==================

- Channel surfing for your Video, LiveTV, InternetTV and Plugin sources
 
- Find support @ "ORG" http://forum.xbmc.org/showthread.php?tid=169032

------------------
Special thanks to:
------------------

- XBMC - Foundation

- jason102, angrycamel, jtucker1972 - Original code and project inspiration.

- RagnaroktA - CE Intro Video, Visit http://www.cinemavision.org/

- Special Thanks to:
  ARYEZ,thedarkonaut, tman12, peppy6582, earlieb, Steveb1968, kurumushi, twinther, LordIndy, ronie, mcorcoran, 
  sphere, giftie, spoyser, Eldorados, lambda, kickin, bradvido88, Phil65, RagnaroktA, -bry
  
* All work is either original, or modified code from the properly credited creators.

------------------
What is it?
------------------

    It's channel-surfing for your mediacenter.  Never again will you have to actually pick what you want to watch.  
    Use an electronic program guide (EPG) to view what's on or select a show to watch.  This script will let you create
    your own channels and, you know, watch them.  Doesn't actually sound useful when I have to write it in a readme.  
    Eh, try it and decide if it works for you...

------------------
Features
------------------

    - Automatic channel creation based on your library, installed plugins and recommend online sources.
    - Optionally customize the channels you want with the in-app channel configuration tool.
    - Utilize the Kodi smartplaylist editor to create advanced channel setups.
    - Use an EPG and view what was on, is on, and will be on.  Would you rather
        see something that will be on later?  Select it and watch it now!
    - Extended show information including a OnDemand menu.
    - Missed the beginning of a show? use the "Start Over" feature.
    - Want to pause a channel while you watch another?  And then come back to
        it and have it be paused still?  Sounds like a weird request to me, but
        if you want to do it you certainly can.  It's a feature!
    - An idle-timer makes sure you aren't spinning a hard-drive needlessly all
        night.
    - Accidental left the EPG open? or screen paused? No need to worry a handy clock 
      screensaver displays when idle.
    - No need to wonder what's on next, toward the end of a program the "Coming Up Next" will display 
      information on the upcoming program.
    - Multi-Action sleep timer, Turn the TV off? Shutdown Kodi? it's up to you.
    - Discover the other features on your own (so that I don't have to list
        them all...I'm lazy).

------------------
Setup
------------------

    First, install it.  This is self-explanatory (hopefully).  Really, that's all that is necessary.  
    Default channels will be created without any intervention.  You can choose to setup channels (next step) 
    if you wish. Instructions to create your own channels.  Inside of the addon config, you may open the channel         
    configuration tool.  Inside of here you can select a channel to modify.  You may then select it's type and any 
    options. For a basic setup, that's all you need to do.  It's worth noting that you may create a playlist using the 
    smart playlist editor and then select that playlist in the channel config tool (Custom Playlist channel type). 
    Additionally, you may select to add advanced rules to a certain channel. There are quite a few rules that are 
    currently available, and hopefully they should be relatively self-explanitory.  This is a readme and should include 
    descriptions of them all...who knows, maybe it will some day.

------------------
Controls
------------------

    There are only a few things you need to know in order to control everything. First of all, the Close/Exit button 
    exits the script.  You may also press the Previous Menu ('Escape') button to do 
    this (don't worry, it will prompt you to verify first).  Scroll through channels using the arrow up and down 
    keys, or alternatively by pressing Page up or down. You can also jump through the EPG using page up and down.
    Switch directly to a channel by inputting the channel number, or navigate to it in the EPG.
    
    To open the EPG, press the Select key ('Enter'). Move around using the arrow keys. Start a program by pressing 
    Select.  Pressing Previous Menu ('Escape') will close the EPG. Pressing 'Context Menu' will reveal more options. 
    
    Press 'I' to display or hide the info window. When it is displayed, you can look at the next shows 
    on this channel using arrow right. Pressing the arrow left reveals the "Sidebar" menu. 
    Pressing the 'Context Menu' will show the "MoreInfo" bar.
 
    Additional controls: Use the keymap plugin to link these action to a remote key.
    --------------------
    Mute ('F8')
    Last Channel Recall ('ACTION_SHIFT')
    Favourite Channel Jump ('ACTION_SYMBOL')
    Subtitles ('ACTION_SHOW_SUBTITLES'), ('ShowSubtitles')
    Next Subtitle ('NextSubtitle')
    Show Codec ('ACTION_SHOW_CODEC')
    Sleep Timer ('ACTION_ASPECT_RATIO')
    Record ('ACTION_RECORD') -- To be used with future PVR features.
    
------------------
Settings
------------------

General Settings -

- Configure Channels: This is the channel configuration tool.  From here you can modify the settings for each individual channel.

- Auto-off Timer: The amount of time (in minutes) of idle time before the script is automatically stopped.

- Force Channel Reset: If you want your channels to be reanalyzed then you
can turn this on.

- Time Between Channel Resets: This is how often your channels will be reset.
Generally, this is done automatically based on the duration of the individual
channels and how long they've been watched.  You can change this to reset every
certain time period (day, week, month).

- Default channel times at startup: This affects where the channels start
playing when the script starts.  Resume will pick everything up where it left
off.  Random will start each channel in a random spot.  Real-Time will act like
the script was never shut down, and will play things at the time the EPG said
they would play.

- Background Updating: The script uses multiple threads to keep channels up-
to-date while other channels are playing.  In general, this is fine.  If your
computer is too slow, though, it may cause stuttering in the video playback.
This setting allows you to minimize or disable the use of these background
threads.

- Enable Channel Sharing: Share the same configuration and channel list
between multiple computers.  If you're using real-time mode (the default) then
you can stop watching one show on one computer and pick it up on the other.  Or
you can have both computers playing the same lists at the same time.

- Shared Channels Folder: If channel sharing is enabled, this is the location
available from both computers that will keep the settings and channel infor-
mation.


Visual Settings -

- Info when Changing Channels: Pops up a small window on the bottom of the
screen where the current show information is displayed when changing channels.

- Always show channel logo: Always display the current channel logo.

- Channel Logo Folder: The place where channel logos are stored.

- Clock Display: Select between a 12-hour or 24-hour clock in the EPG.

- Show Coming Up Next box: A little box will notify you of what's coming up
next when the current show is nearly finished.

- Hide very short videos: Don't show clips shorter than 60 seconds in the
EPG, coming up next box, or info box.  This is helpful if you use bumpers or
commercials.

------------------------------------
Key Features
------------------------------------

[  ] Online Channel configurations, Custom Skin's and Community Lists via Pseudotvlive.com website.
[½] Full Kodi integration including Context Menu, Hot keys and Artwork.
[✓] Overlay Sidebar ("On Now") Skinnable quick menu.
[✓] "Coming Up Next"  Skinable Overlay.
[  ] Enhanced EPG icon flags (rec, new, sickbeard, couchpotato, HD, PG rating).
[✓] Dynamic artwork for EPG and Overlay.
[✓] Enhanced Guide Data: "Find Missing Art/Info" using TVDB, TMDB, Fanart.TV
[✓] Donor Features.
[✓] Skin Selector.
[½] Music Channel Type.
[✓] Music Video Channels with Internet Streaming features.
[✓] EZ channel configuration ("Autotune").
[✓] EZ in-app channel configuration
[✓] Ability to add channels via Kodi favourites list.
[✓] EPG Guide Data Listings via PVR Backend
[✓] Hdhomerun Support (Dual/Prime).
[✓] USTVnow w/ EPG data(Auto Tune).
[✓] Automatic Bumpers, Commercials, and Trailers w/ Online support ("BCT's").
[✓] Youtube/RSS Channel types [size=xx-small]*parser core by peppy6582[/size]
[✓] TVDB/TMDB/IMDB/Fanart.TV Integration w/ trakt support
[½] Sickbeard / Couchpotato Integration (Map Record button to queue selected show for download, Visual indicators if show is managed by either program).
[✓] Error handling (dead link) filter.
[✓]  EPG Color Categories 
[✓] Autostart Service [size=xx-small]*core created by Steveb1968 [/size]
[✓] Channel Manager Tool (Windows Only)
[  ] Android Companion Tool
[  ] PVR (Recording Feature)
[  ] Virtual Movie Poster (Showtime) Integration.
[½] Kodi web interface w/EPG, Channel editor, Remote Control.
[✓] Direct Plugin directory channel building (ie. Mylibrary method without the need to build strms).
[✓] Direct Playon channel building (Requires Playon Software).
[✓] Direct UPNP channel building (Requires UPNP Software or Devices).
[✓] Kodi PVR Backend channel building.
[✓] Classic Coming Up Next dialog artwork.
[½] Vevo Music Video Channel w/ EPG Information
[✓] Settop Box mode, 24/7 Operation w/ self updating channels.
[✓] Multiroom Video Mirroring.
[✓] Multiroom Channel sharing.
[  ] EPG Guide data from Schedules Direct and zap2it.

✓ = Added to master
½ = Added to master, but may not be functional.

------------------------------------
Understanding Chtypes
------------------------------------

(0).  - Custom Smartplaylist
(1).  - TV networks
(2).  - Movie Studios
(3).  - TV Genre
(4).  - Movie Genre
(5).  - Mixed TV/Movie Genre
(6).  - TV Show
(7).  - Directory Channel
(8).  - LiveTV, Use with a single video source and matching xmltv EPG data.
(9).  - InternetTV, Use with a single video source and no matching EPG data. EPG data is provided manually via settings. 
(10). - Youtube Channels
(11). - RSS Feed
(12). - Music Genres
(13). - Music Videos
(14). - Donor Extras Content
(15). - Plugin generated channel (not for single source).
(16). - UPNP generated channel (not for single source).

----------------------------------------
Manual Configuration Examples - OUTDATED
----------------------------------------

[b][u]Configuration Examples:[/u][/b]
[size=x-small]# = PTV Channel Number[/size]

[list]
LiveTV:
Use this chtype to pair media sources with EPG data from xmltv listings.
[list]
[code]
<setting id="Channel_#_type" value="8" />
<setting id="Channel_#_1" value="I60159.labs.zap2it.com" />
<setting id="Channel_#_2" value="hdhomerun://xxxxxxxD-1/tuner1?channel=qam256:399000000&program=2" />
<setting id="Channel_#_3" value="xmltv" />
<setting id="Channel_#_4" value="" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_time" value="0" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="NY1 Live" />
[/code]

_type" value="8" --- LiveTV w/ XMLTV EPG Chtype
_1" value="I60159.labs.zap2it.com" --- Zapit XMLTV Channel ID found in your XMLTV file.
_2" ]value="hdhomerun://..." --- This is the source of your LiveTV stream; Examples include:
[list]
[*]_2" value="hdhomerun://..." --- Direct Hdhomerun
[*]_2" value="smb://XXX/Hdhomerun XBMC/NY1.strm" --- Direct strm file (currently only one tuner is supported).
[*]_2" value="pvr://channels/tv/All TV channels/##.pvr" --- Direct link to your XBMC LiveTV plugin
[*]_2" value="plugin://feedlink"
[*]_2" value="upnp://feedlink"
[*]_2" value="rtmp://feedlink"
[*]_2" value="http://feedlink"
[*]_2" value="mms://feedlink or rtsp://feedlink" --- VLC streaming"
[/list]
_3" value="xmltv" --- name of xmltv file used for this source. Example: if you use "listings", ptvl will look for listings.xml and parse data from that source. This allows multiple sources depending on the channel. "ustvnow" is reserved for USTVnow channels and can only be used with a USTVnow source.
_opt_1" value="NY1 Live"  --- Channel Name
[/list]

[hr]

InternetTV:
Similar to chtype 8, except that this chtype does not offer EPG data. Its designed for a single 24/7 type stream.
[list]
[code]    
<setting id="Channel_#_type" value="9" />
<setting id="Channel_#_1" value="5400" />
<setting id="Channel_#_2" value="smb://xxx/strms/VevoTV.strm" />
<setting id="Channel_#_3" value="VevoTV" />
<setting id="Channel_#_4" value="Sit back and enjoy a 24/7 stream of music videos on VEVO TV." />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_time" value="0" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="VevoTV" />
[/code]

_type value="9" --- InternetTV Chtype, meant for 24/7 type steams
_1" value="5400" --- 90min runtime; This is the default runtime for InternetTV EPG Data. You can chose whatever value you prefer.
_2" value="smb://xxx/strms/VevoTV.strm" --- This is the source of your InternetTV; Examples include:
[list]
[*]_2" value="smb://strmfile.strm"
[*]_2" value="rtmp://feedlink"
[*]_2" value="upnp://feedlink"
[*]_2" value="http://feedlink"
[*]_2" value="mms://feedlink"
[*]_2" value="rtsp://feedlink"
[*]_2" value="plugin://plugin.scriptname/feedlink"
[/list]
_3" value="VevoTV" --- Show Title
_4" value="Sit back and enjoy VEVO TV..." --- Show Description
_opt_1" value="VevoTV" --- Channel Name
[/list]
[/list]

[hr]

YoutubeTV:
[color=#FF0000]REQUIRES XBMC YOUTUBE ADDON[/color]
[list]
Channel/User Upload Example:
[code]
<setting id="Channel_#_type" value="10" />
<setting id="Channel_#_1" value="MotorTrend" />
<setting id="Channel_#_2" value="1" />
<setting id="Channel_#_3" value="#" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="MotorTrend - User Upload" />
[/code]

User Playlist Example:
[url=http://youtubeplaylist.net/]Useful YouTube playlist tool [/url]
[url=http://ctrlq.org/youtube/playlists/ Another ]Useful YouTube playlist tool [/url]
[code]
<setting id="Channel_#_type" value="10" />
<setting id="Channel_#_1" value="PL9bsPVRSg1sl0kSa99jrim69esS0lQrkF" />
<setting id="Channel_#_2" value="2" />
<setting id="Channel_#_3" value="" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="User Playlist" />
[/code]

New Subscription Example:
[code]
<setting id="Channel_#_type" value="10" />
<setting id="Channel_#_1" value="YOUR YOUTUBE USERNAME" />
<setting id="Channel_#_2" value="3" />
<setting id="Channel_#_3" value="#" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="User Playlist" />
[/code]

User Favorites Example:
[code]
<setting id="Channel_#_type" value="10" />
<setting id="Channel_#_1" value="YOUR YOUTUBE USERNAME" />
<setting id="Channel_#_2" value="4" />
<setting id="Channel_#_3" value="#" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="User Playlist" />
[/code]

Multi Youtube Example:
[code]
<setting id="Channel_#_type" value="10" />
<setting id="Channel_#_1" value="WatchMojo|HybridLibrarian" />
<setting id="Channel_#_2" value="8" />
<setting id="Channel_#_3" value="25" />
<setting id="Channel_#_4" value="1" />
<setting id="Channel_#_changed" value="False" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Top Tens" />
[/code]

value="10" ---YoutubeTV Chtype
_1" value="MotorTrend"  --- Channel info (Username, Playlist, Channel, Search term, Raw gdata url).
_2" value="1" --- Youtube Channel information; Examples include:
[list]
[*] "1" Channel/User Uploads = Channel or Username that has videos you want
[*] "2" User Playlist = Your username playlist (Log into your youtube account, click playlist, select a playlist... copy the url information ( http://www.youtube.com/playlist?list= COPYME  ))
[*] "3" New Subscription = USERNAME *Your youtube usernames newest subscriptions.
[*] "4" User Favorites = USERNAME *Your youtube usernames newest favorites.
[*] "5" Search Query w/SafeSearch = Search pattern or term, examples (Football+Soccer) & (Football Soccer). For SafeSearch use one of the two options (moderate or strict), No option disables SafeSearch ! Example: (strict|Dick+Cheney).
[*] "7" Multi Youtube Playlists = Multiple Playlists that has videos you want
[*] "8" Multi Youtube Channels = Multiple Channels or Usernames that has videos you want
[*] "9" Raw gdata url = [url=http://forum.xbmc.org/showthread.php?tid=169032&pid=1645272#pid1645272]Example:[/url]
[/list]
_3" value="1" --- Media limit: Set to one of these values (50|100|150|200|250|500|1000).
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value="MotorTrend" --- Channel Name
[/list]

[hr]

RSS:
[color=#FF0000]Feed must complie with RSS/Atom standards, [/color][url=http://validator.w3.org/feed/][color=#FF0000]Validator found here[/color][/url]
[list]
[code]
<setting id="Channel_#_type" value="11" />
<setting id="Channel_#_1" value="http://revision3.com/hdnation/feed/mp4-hd30" />
<setting id="Channel_#_2" value="1" />
<setting id="Channel_#_3" value="100" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="HD Nation" />
[/code]

_type" value="11" --- RSS Chtype
_1" value="http://revision3.com/hdnation/feed/mp4-hd30" --- RSS feed, must be RSS/Atom Compliant link
_2" value="1" --- Default value, Switch reserved for later development.
_3" value="100" --- Media limit: Set to one of these values (50|100|150|200|250|500|1000).
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value="HD Nation" --- Channel Name
[/list]

[hr]

Music Videos:
[color=#FF0000]LAST.FM REQUIRES XBMC YOUTUBE ADDON[/color]
[color=#FF0000]MyMusicTV REQUIRES XBMC MyMusicTV ADDON[/color]
[list]
[code]
<setting id="Channel_#_type" value="13" />
<setting id="Channel_#_1" value="1" />
<setting id="Channel_#_2" value="LastFM Username" />
<setting id="Channel_#_3" value="50" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="LastFM" />
[/code]

[code]
<setting id="Channel_#_type" value="13" />
<setting id="Channel_#_1" value="2" />
<setting id="Channel_#_2" value="Channel_#" />
<setting id="Channel_#_3" value="50" />
<setting id="Channel_#_4" value="1" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Music Videos" />
[/code]

_type" value="13" --- Music Videos
_1" value="1" --- 1 = Last.Fm, 2 = MyMusicTV 
_2" value="LastFM Username" --- LastFM Username, must have scrobbler data. or MyMusic Channel info (ie, Channel_1, Channel_2, etc...)
_3" value="100" --- Media limit: Set to one of these values (50|100|150|200|250|500|1000).
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value="LastFM" --- Channel Name
[/list]

[hr]

Extras:
[color=#FF0000]Donor Extras![/color]

Popcorn Movies
[list]
[code]
<setting id="Channel_#_type" value="14" />
<setting id="Channel_#_1" value="popcorn" />
<setting id="Channel_#_2" value="pop|action" />
<setting id="Channel_#_3" value="480" />
<setting id="Channel_#_4" value="2010-Now" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Popcorn Movies" />
[/code]

_type" value="14" --- Extras Chtype (Donor Exclusive Media aggregation).
_1" value="popcorn" --- 'popcorn' indicates Media Source "Popcorn Movies". More sources to coming soon!
_2" value="pop|action"  --- 'pop|' indicates filter by Popularity, "action" = Genre, [url=http://forum.xbmc.org/showthread.php?tid=169032&pid=1637449#pid1637449]examples include.[/url]
_3" value="480"  --- Resolution to parse, [url=http://forum.xbmc.org/showthread.php?tid=169032&pid=1637449#pid1637449]examples include.[/url]
_4" value="2010-Now" --- Year to parse movies by, [url=http://forum.xbmc.org/showthread.php?tid=169032&pid=1637449#pid1637449]examples include.[/url]
_opt_1" value="Popcorn Movies " --- Channel Name
[/list]

Cinema Experience
[list]
[code]
<setting id="Channel_#_type" value="14" />
<setting id="Channel_#_1" value="cinema" />
<setting id="Channel_#_2" value="special://profile/playlists/videos/myplaylist.xsp" />
<setting id="Channel_#_3" value="IMAX" />
<setting id="Channel_#_4" value="" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="5" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Cinema Experience" />
<setting id="Channel_#_rule_2_id" value="8" />
<setting id="Channel_#_rule_3_id" value="14" />
<setting id="Channel_#_rule_3_opt_1" value="No" />
<setting id="Channel_#_rule_4_id" value="17" />
<setting id="Channel_#_rule_4_opt_1" value="No" />
<setting id="Channel_#_rule_5_id" value="13" />
<setting id="Channel_#_rule_5_opt_1" value="1" />
[/code]

_type" value="14"" --- Extras Chtype (Donor Exclusive Media aggregation).
_1" value="cinema" --- 'cinema' indicates Media Source "Cinema Experience". More sources to coming soon!
_2" value=""  --- Custom XBMC Smartplaylist location and name.
_3" value=""  --- CE Theme, either "IMAX" or "Default", Custom themes are available @ http://www.cinemavision.org/
_4" value=""  --- Unused
_opt_1" value="Cinema Experience" --- Channel Name
[/list]

[hr]

[u]Direct Plugin:[/u]
[color=#FF0000]Gotham and up Only!![/color]
Use this chtype to automatically parse plugins for media, similar process to "xbmc.mylibrary".
In order for this chtype to work, the plugin must store it's "media" as "files" not "directories". From a users perspective there isn't a easy way to test for this. So you will have go through trial and error. Please report your success stories!
[list]
[code]
<setting id="Channel_#_type" value="15" />
<setting id="Channel_#_1" value="plugin://plugin.video.vevo_tv" />
<setting id="Channel_#_2" value="VEVO TV (US: Nashville),VEVO TV (Germany),Custom (All videos),Custom (Live videos),Custom (Playlists),Custom (Artists)" />
<setting id="Channel_#_3" value="25" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="VevoTV Plugin" />
[/code]

[code]
<setting id="Channel_#_type" value="15" />
<setting id="Channel_#_1" value="plugin://plugin.video.discovery_com/Animal Planet/Bad Dog!" />
<setting id="Channel_#_2" value="" />
<setting id="Channel_#_3" value="25" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Bad Dog!" />
[/code]

[code]
<setting id="Channel_#_type" value="15" />
<setting id="Channel_#_1" value="plugin://plugin.video.espn.video" />
<setting id="Channel_#_2" value="[ TV Shows ],[ Categories ],[ Search ]" />
<setting id="Channel_#_3" value="25" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="ESPN" />
<setting id="Channel_#_changed" value="True" />
[/code]

_type" value="15" --- Direct Plugin Chtype
_1" value="  --- plugin path; Requires a prefix "plugin://",  real pathname, then subfolders that contain media. or root level folder that contains media (ie. plugin://plugin.video.vevo_tv/). All folders must match what is seen on screen exactly. You need to match the appropriate strings but can ignore "bold", "color" code strings.. If you are unsure, add the folder as a xbmc favorite, then open favorite.xml with a text editor. Use the example found there!
_2" value= '' --- Exclude list, can be files or directories (No spaces, separate with ",")
_3" value="25" --- File limit, Example 25 will parse 25 files per 25 directories found.
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value=" --- Channel Name
[/list]

Super Favourite
[color=#FF0000]Gotham Only!! In Heavy Development, Check back for updates![/color]
[list]
[code]
    <setting id="Channel_#_type" value="15" />
    <setting id="Channel_#_time" value="0" />
    <setting id="Channel_#_1" value="plugin://plugin.program.super.favourites/PseudoTV_Live/Channel_#" />
    <setting id="Channel_#_2" value="'create new super folder,explore favourites,explore  favourites,explore xbmc favourites,explore kodi favourites,isearch,search" />
    <setting id="Channel_#_3" value="25" />
    <setting id="Channel_#_4" value="0" />
    <setting id="Channel_#_changed" value="False" />
[/code]

_type" value="15" --- Direct Plugin Chtype
_1" value=""plugin://plugin.program.super.favourites/PseudoTV_Live/Channel_#"  --- plugin path; Requires a prefix "plugin://",  You can either have the "Channel_#" folder in the root ie (plugin://plugin.program.super.favourites/Channel_1) or organized into one folder which has to be "PseudoTV_Live"
_2" value= '' --- Exclude list, can be files or directories (No spaces, separate with ",")
_3" value="25" --- File limit, Example 25 will parse 25 files per 25 directories found.
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value=" --- Channel Name
[/list]

[hr]

[u]Direct Playon:[/u]
[color=#FF0000]Gotham and up Only!![/color]
Use this chtype to automatically parse playon for media, similar process to "xbmc.mylibrary".
In order for this chtype to work, the plugin must store it's "media" as "files" not "directories". From a users perspective there isn't a easy way to test for this. So you will have go through trial and error. Please report your success stories!

For Playon to work either through manual configuration or autotune you will need to create a XBMC Video Source titled "PlayOn"
Add new source, navigate to upnp sources and select playon... it should appear as a source upnp://09324908320948230948320498.
Title it "PlayOn" <- Name is important! without PTVL will not know what source is actually playon.

Also don't forget to properly configure playons settings as well!! ie, Hulu login information, etc...
[list]
[code]
<setting id="Channel_#_type" value="16" />
<setting id="Channel_#_1" value="hulu/Recently Added/Recently Added Feature Films" />
<setting id="Channel_#_2" value="" />
<setting id="Channel_#_3" value="25" />
<setting id="Channel_#_4" value="0" />
<setting id="Channel_#_changed" value="True" />
<setting id="Channel_#_rulecount" value="1" />
<setting id="Channel_#_rule_1_id" value="1" />
<setting id="Channel_#_rule_1_opt_1" value="Hulu Recent Movies" />
[/code]

_type" value="16" --- Direct Playon Chtype
_1" value="  --- plugin path; Plugin path, paths match what you see when navigating the plugin.
_2" value= '' --- Exclude list, can be files or directories (No spaces, separate with ",")
_3" value="25" --- File limit, Example 25 will parse 25 files per 25 directories found.
_4" value="0" --- Sort Ordering: 0 = default, 1 = random, 2 = reverse.
_opt_1" value=" --- Channel Name
[/list]

------------------
Skinning Info
------------------

# Dynamic artwork types:
['banner', 'fanart', 'folder', 'landscape', 'poster', 'character', 'clearart', 'logo', 'disc']

# EPG Chtype/Genre COLOR TYPES
COLOR_RED_TYPE = ['10', '17', 'TV-MA', 'R', 'NC-17', 'Youtube', 'Gaming', 'Sports', 'Sport', 'Sports Event', 'Sports Talk', 'Archery', 'Rodeo', 'Card Games', 'Martial Arts', 'Basketball', 'Baseball', 'Hockey', 'Football', 'Boxing', 'Golf', 'Auto Racing', 'Playoff Sports', 'Hunting', 'Gymnastics', 'Shooting', 'Sports non-event']
COLOR_GREEN_TYPE = ['5', 'News', 'Public Affairs', 'Newsmagazine', 'Politics', 'Entertainment', 'Community', 'Talk', 'Interview', 'Weather']
COLOR_mdGREEN_TYPE = ['9', 'Suspense', 'Horror', 'Horror Suspense', 'Paranormal', 'Thriller', 'Fantasy']
COLOR_BLUE_TYPE = ['Comedy', 'Comedy-Drama', 'Romance-Comedy', 'Sitcom', 'Comedy-Romance']
COLOR_ltBLUE_TYPE = ['2', '4', '14', '15', '16', 'Movie']
COLOR_CYAN_TYPE = ['8', 'Documentary', 'History', 'Biography', 'Educational', 'Animals', 'Nature', 'Health', 'Science & Tech', 'Learning & Education', 'Foreign Language']
COLOR_ltCYAN_TYPE = ['Outdoors', 'Special', 'Reality', 'Reality & Game Shows']
COLOR_PURPLE_TYPE = ['Drama', 'Romance', 'Historical Drama']
COLOR_ltPURPLE_TYPE = ['12', '13', 'LastFM', 'Vevo', 'VevoTV', 'Musical', 'Music', 'Musical Comedy']
COLOR_ORANGE_TYPE = ['11', 'TV-PG', 'TV-14', 'PG', 'PG-13', 'RSS', 'Animation', 'Animation & Cartoons', 'Animated', 'Anime', 'Children', 'Cartoon', 'Family']
COLOR_YELLOW_TYPE = ['1', '3', '6', 'TV-Y7', 'TV-Y', 'TV-G', 'G', 'Classic TV', 'Action', 'Adventure', 'Action & Adventure', 'Action and Adventure', 'Action Adventure', 'Crime', 'Crime Drama', 'Mystery', 'Science Fiction', 'Series', 'Western', 'Soap', 'Soaps', 'Variety', 'War', 'Law', 'Adults Only']
COLOR_GRAY_TYPE = ['Auto', 'Collectibles', 'Travel', 'Shopping', 'House Garden', 'Home & Garden', 'Home and Garden', 'Gardening', 'Fitness Health', 'Fitness', 'Home Improvement', 'How-To', 'Cooking', 'Fashion', 'Beauty & Fashion', 'Aviation', 'Dance', 'Auction', 'Art', 'Exercise', 'Parenting', 'Food', 'Health & Fitness']
COLOR_ltGRAY_TYPE = ['0', '7', 'NR', 'Consumer', 'Game Show', 'Other', 'Unknown', 'Religious', 'Anthology', 'None']


OVERLAY/EPG info labels:
$INFO[Window(10000).Property()

EPG.Chtype
EPG.Mediapath
EPG.Playcount
EPG.Title
EPG.Mpath
EPG.Chname
EPG.SEtitle
EPG.Type
EPG.DBID
EPG.EPID
EPG.Description
EPG.Season
EPG.Episode
EPG.Year
EPG.ID
EPG.Genre
EPG.Rating
EPG.Managed
EPG.Tagline

OVERLAY/EPG info pictures:
EPG.isNew
EPG.Managed
OVERLAY.LOGOART
OVERLAY.type1ART
OVERLAY.type2ART
OVERLAY.type3ART - Onnow artwork
OVERLAY.type4ART

# Id's:
All Id's must remain in skin, but you can change their visibility without issue.

# EPG.xml:
99  - EPG focused text color
100 - EPG text color
105 - EPG text font
522 - TrendingNow Videowindow replacement (Hidden when 523 enabled)
523 - Videowindow
215 - EPG
216 - DVR
217 - Ondemand
218 - Apps
104 - Current Date
106 - EPG horizontal time button
101-103 - EPG grid times
311-316 - EPG grid channel numbers
301-306 - EPG grid channel names
321-326 - EPG grid channel icons
111-116 - EPG grid guide
118 - EPG future epg event fading
119 - EPG past epg event fading
120 - EPG vertical time bar
508 - Dynamic art1 image
510 - Dynamic art2 image
511 - SB/CP logo (SB.png,CP.png)
512 - Unaired/New logo (NEW.png,OLD.png)
516 - Now watching/Coming up label
500 - Show title
501 - episode/tagline
300 - Channel name
515 - seekbar hide
502 - show description/plot
503 - show channel icons

# TVOverlay.xml



------------------
Credits
------------------

PseudoTV Live: Lunatixz
PseudoTV: Jason102
TVTime: Jtucker1972
