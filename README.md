# PseudoTV Live

![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/icon.png)

- Channel surfing for your Video, LiveTV, InternetTV and Plugin sources. Cut the cord with ease, familair controls and functions of a standard settop box.
- [Official support forum](http://pseudotvlive.com/index.php/forum)
- [Kodi support forum](http://forum.kodi.tv/showthread.php?tid=244889)

![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/fanart.jpg)
![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/resources/skins/Default/screenshot01.png)
![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/resources/skins/Default/screenshot02.png)
![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/resources/skins/Default/screenshot03.png)
![screenshot](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/resources/skins/Default/screenshot04.png)


## What is it?

It's channel-surfing for your mediacenter.  Never again will you have to actually pick what you want to watch.  
Use an electronic program guide (EPG) to view what's on or select a show to watch.  This script will let you create your own channels and, you know, watch them.  Doesn't actually sound useful when I have to write it in a readme.  
Eh, try it and decide if it works for you...


## Features

- Automatic channel creation based on your library, installed plugins and recommend online sources.
- Optionally customize the channels you want with the in-app channel configuration tool.
- Utilize the Kodi smartplaylist editor to create advanced channel setups.
- Use an EPG and view what was on, is on, and will be on.  Would you rather see something that will be on later? Select it and watch it now!
- Extended show information including a OnDemand menu.
- Missed the beginning of a show? use the "Start Over" feature.
- Want to pause a channel while you watch another?  And then come back to it and have it be paused still?  Sounds like a weird request to me, but if you want to do it you certainly can.  It's a feature!
- An idle-timer makes sure you aren't spinning a hard-drive needlessly all night.
- Accidental left the EPG open? or screen paused? No need to worry a handy clock screensaver displays when idle.
- No need to wonder what's on next, toward the end of a program the "Coming Up Next" will display information on the upcoming program.
- Multi-Action sleep timer, Turn the TV off? Shutdown Kodi? it's up to you.
- Discover the other features on your own (so that I don't have to list them all...I'm lazy).


## Setup

- First, install the [Lunatixz repository](https://github.com/Lunatixz/XBMC_Addons/raw/master/zips/repository.lunatixz/repository.lunatixz-1.0.zip)
- Access the repository and look for add-on 'PseudoTV Live`, install the addon.
- By Default, channels will be created without any intervention. You can choose to setup channels (next step) 
    if you wish. Instructions to create your own channels.  Inside of the addon config, you may open the channel configuration tool. Inside of here you can select a channel to modify.  You may then select it's type and any 
    options. For a basic setup, that's all you need to do.  It's worth noting that you may create a playlist using the 
    smart playlist editor and then select that playlist in the channel config tool (Custom Playlist channel type). 
    Additionally, you may select to add advanced rules to a certain channel. There are quite a few rules that are 
    currently available, and hopefully they should be relatively self-explanitory.  This is a readme and should include 
    descriptions of them all...who knows, maybe it will some day.


## Controls

There are only a few things you need to know in order to control everything. First of all, the ``Close/Exit`` button exits the script.  

You may also press the Previous Menu ``Escape`` button to do this (don't worry, it will prompt you to verify first).  

Scroll through channels using the arrow up and down keys, or alternatively by pressing Page up or down. 

You can also jump through the EPG using ``page up`` and ``page down`` or by using a ''mouse scroll wheel''.

Switch directly to a channel by inputting the ``channel number``, or navigate to it in the EPG.

To open the EPG, press the ''Select/OK'' key or ``Enter``. 

Move around using the arrow keys. Start a program by pressing ''Select/OK''.  

Pressing Previous Menu ``Escape`` will close the EPG. Pressing ``Context Menu`` will reveal more options. 

Press ``I`` to display or hide the info window. 

When it is displayed, you can look at the next shows on this channel using ``arrow right``. 

Pressing the ``arrow left`` reveals the "Sidebar" menu.

Pressing the ``Context Menu`` will show the "MoreInfo" bar.

#### Additional controls: Use the keymap plugin to link these action to a remote key.

- Mute ``F8``
- Last Channel Recall ``ACTION_SHIFT``
- Favourite Channel Jump ``ACTION_SYMBOL``
- Subtitles ``ACTION_SHOW_SUBTITLES``, ``ShowSubtitles``
- Next Subtitle ``NextSubtitle``
- Show Codec ``ACTION_SHOW_CODEC``
- Sleep Timer ``ACTION_ASPECT_RATIO``
- Record ``ACTION_RECORD`` -- To be used with future PVR features.
- GREEN,BLUE,RED,YELLOW -- Future access to the 'EPG/ONDEMAND/DVR/APPS' menus  
    
### Touch/Mouse

- MOVE_LEFT ``ACTION_GESTURE_SWIPE_LEFT_TEN``
- MOVE_RIGHT ``ACTION_GESTURE_SWIPE_RIGHT_TEN``
- MOVE_UP ``ACTION_GESTURE_SWIPE_UP``
- MOVE_DOWN ``ACTION_GESTURE_SWIPE_DOWN``
- PAGEUP ``ACTION_GESTURE_SWIPE_UP_TEN``
- PAGEDOWN ``ACTION_GESTURE_SWIPE_DOWN_TEN``
- SELECT_ITEM ``ACTION_TOUCH_TAP``
- SHOW_INFO ``ACTION_TOUCH_LONGPRESS,ACTION_GESTURE_SWIPE_LEFT``
- CONTEXT_MENU ``ACTION_TOUCH_LONGPRESS_TEN``
- SHOW_EPG ``ACTION_GESTURE_SWIPE_RIGHT``


## Settings

### General Settings

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

### Visual Settings

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

## Understanding Chtypes

- (0).  - Custom Smartplaylist
- (1).  - TV networks
- (2).  - Movie Studios
- (3).  - TV Genre
- (4).  - Movie Genre
- (5).  - Mixed TV/Movie Genre
- (6).  - TV Show
- (7).  - Directory Channel
- (8).  - LiveTV, Use with a single video source and matching xmltv EPG data.
- (9).  - InternetTV, Use with a single video source and no matching EPG data. EPG data is provided manually via settings. 
- (10). - Youtube Channels
- (11). - RSS Feed
- (12). - Music Genres
- (13). - Music Videos
- (14). - Extra Content
- (15). - Plugin generated channel (not for single source).
- (16). - UPNP generated channel (not for single source).

------------------
[Skinning Info](https://github.com/PseudoTV/PseudoTV_Live/wiki/Developing-a-PseudoTV-Live-Skin)
------------------

# Dynamic artwork types:
- ['banner', 'fanart', 'folder', 'landscape', 'poster', 'character', 'clearart', 'logo', 'disc']

# EPG Chtype/Genre COLOR TYPES
- COLOR_RED_TYPE = ['10', '17', 'TV-MA', 'R', 'NC-17', 'Youtube', 'Gaming', 'Sports', 'Sport', 'Sports Event', 'Sports Talk', 'Archery', 'Rodeo', 'Card Games', 'Martial Arts', 'Basketball', 'Baseball', 'Hockey', 'Football', 'Boxing', 'Golf', 'Auto Racing', 'Playoff Sports', 'Hunting', 'Gymnastics', 'Shooting', 'Sports non-event']
- COLOR_GREEN_TYPE = ['5', 'News', 'Public Affairs', 'Newsmagazine', 'Politics', 'Entertainment', 'Community', 'Talk', 'Interview', 'Weather']
- COLOR_mdGREEN_TYPE = ['9', 'Suspense', 'Horror', 'Horror Suspense', 'Paranormal', 'Thriller', 'Fantasy']
- COLOR_BLUE_TYPE = ['Comedy', 'Comedy-Drama', 'Romance-Comedy', 'Sitcom', 'Comedy-Romance']
- COLOR_ltBLUE_TYPE = ['2', '4', '14', '15', '16', 'Movie']
- COLOR_CYAN_TYPE = ['8', 'Documentary', 'History', 'Biography', 'Educational', 'Animals', 'Nature', 'Health', 'Science & Tech', 'Learning & Education', 'Foreign Language']
- COLOR_ltCYAN_TYPE = ['Outdoors', 'Special', 'Reality', 'Reality & Game Shows']
- COLOR_PURPLE_TYPE = ['Drama', 'Romance', 'Historical Drama']
- COLOR_ltPURPLE_TYPE = ['12', '13', 'LastFM', 'Vevo', 'VevoTV', 'Musical', 'Music', 'Musical Comedy']
- COLOR_ORANGE_TYPE = ['11', 'TV-PG', 'TV-14', 'PG', 'PG-13', 'RSS', 'Animation', 'Animation & Cartoons', 'Animated', 'Anime', 'Children', 'Cartoon', 'Family']
- COLOR_YELLOW_TYPE = ['1', '3', '6', 'TV-Y7', 'TV-Y', 'TV-G', 'G', 'Classic TV', 'Action', 'Adventure', 'Action & Adventure', 'Action and Adventure', 'Action Adventure', 'Crime', 'Crime Drama', 'Mystery', 'Science Fiction', 'Series', 'Western', 'Soap', 'Soaps', 'Variety', 'War', 'Law', 'Adults Only']
- COLOR_GRAY_TYPE = ['Auto', 'Collectibles', 'Travel', 'Shopping', 'House Garden', 'Home & Garden', 'Home and Garden', 'Gardening', 'Fitness Health', 'Fitness', 'Home Improvement', 'How-To', 'Cooking', 'Fashion', 'Beauty & Fashion', 'Aviation', 'Dance', 'Auction', 'Art', 'Exercise', 'Parenting', 'Food', 'Health & Fitness']
- COLOR_ltGRAY_TYPE = ['0', '7', 'NR', 'Consumer', 'Game Show', 'Other', 'Unknown', 'Religious', 'Anthology', 'None']


## Credits

- PseudoTV Live: Lunatixz
- PseudoTV: Jason102
- TVTime: Jtucker1972


### Special thanks to:

- XBMC - Foundation
- jason102, angrycamel, jtucker1972 - Original code and project inspiration.
- RagnaroktA - CE Intro Video, Visit http://www.cinemavision.org/
- Special Thanks to:
  ARYEZ,thedarkonaut, tman12, peppy6582, earlieb, Steveb1968, kurumushi, twinther, LordIndy, ronie, mcorcoran, 
  sphere, giftie, spoyser, Eldorados, lambda, kinkin, bradvido88, Phil65, RagnaroktA, -bry

``All work is either original, or modified code from the properly credited creators.``
