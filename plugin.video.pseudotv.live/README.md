![PseudoTV Live](https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/plugin.video.pseudotv.live/resources/images/fanart.jpg)

# PseudoTV Live for Kodi™

> **Note:** All code in this project is written by a human developer. AI tools are used solely for linting, code review, and quality assurance purposes.

## What is it?

PseudoTV Live transforms your Kodi Library and Sources (Plugins, UPnP, etc…) into
**linear broadcast-style television** — complete with configurable channels,
advanced channel rules, an EPG guide, timeshift/catchup, and multi-room sync.
The interface is provided by Kodi via the IPTV Simple PVR backend.

## What it isn't!

PseudoTV Live is **not** an IPTV service. It does not provide content or support
live streams. Users are required to supply media through their own Kodi library.

---

## Features

### Linear TV from your own library
- Turns movies, TV shows, music, playlists, and smart playlists into always-on
  channels with a real TV guide.
- Auto-generated **EPG (XMLTV)** with artwork, genres, ratings, and plot synopses.
- Per-channel **numbering, grouping, favorites, and radio** support.

### Advanced Channel Rules
- A rich rules engine (`rules.py`, ~2,200 lines) for building and curating
  channel lineups: filters, ordering, filler injection, bumper/rating/advert
  placement, season/episode rounding, and playback resume.
- **Auto-Tune**: one-click generation of a complete channel list from your
  library (TV networks, TV/movie genres, studios, music genres, recommended,
  seasonal, services).

### EPG Guide & Playback
- Full 24/7 guide with **now-playing** rows, placeholder rows for no-guide
  channels, and **catchup/VOD** support.
- **Timeshift**, resume, and PVR recording integration.

### Multi-Room (Multi-Instance)
- Discover other PseudoTV Live instances on your LAN via **zeroconf/bonjour**.
- Share channel data, seasonal/holiday content, and server status between rooms.
- Each room gets its own IPTV Simple instance; edits sync out to enabled remotes.

### Built-in Web UI
- A self-hosted HTTP manager (channel editor, EPG grid, library browser,
  seasonal/holiday calendar, system info, PVR status, logs, backups/imports).
- Serve M3U, XMLTV, genres, and logos to any PVR client or browser.

### Seasonal & Holiday Content
- Calendar-based holiday programming and library rules (episodes & movies
  keyed by keyword), with a **3-way merge** so shipped defaults update without
  clobbering your customizations.

### AI-Generated Artwork (optional)
- Optional **OpenRouter AI image generation** for channel logos, with a curated
  fallback model chain and **BYOK** (bring-your-own-key) support.

### Fillers, Ratings, Bumpers, Adverts & Trailers
- MPAA ratings cards, bumpers, adverts, and trailers woven into channels.
- Optional resource addons provide the media (see Resources below).

### Overlays & Extras
- Channel bug / overlay, on-info overlays, OSD timers, and idle handling.

---

## Resources

PseudoTV Live ships with and/or depends on the following optional resource addons:

- **Images**: `resource.images.pseudotv.logos`, `resource.images.studios.white`,
  `resource.images.studios.coloured`, `resource.images.moviegenreicons.white/.transparent`,
  `resource.images.musicgenreicons.text`, `resource.images.overlays.crttv`
- **Video**: `resource.videos.bumpers.pseudotv`, `resource.videos.bumpers.kodi`,
  `resource.videos.ratings.mpaa.classic`, `resource.videos.adverts.pseudotv`,
  `resource.videos.trailers.pseudotv`

---

## Requirements

- Kodi **19 (Matrix)** or newer
- `pvr.iptvsimple` (IPTV Simple Client) enabled
- A populated Kodi video/music library

## Install

Install from the **PseudoTV Repository** (`repository.pseudotv`), or sideload the
addon zip. After install, enable the addon and run **Auto-Tune** (or import your
own channel set) from the Channel Manager.

---

## Quick Start

1. Install and enable PseudoTV Live + IPTV Simple Client.
2. Open **PseudoTV Live** → Channel Manager.
3. Choose **Auto-Tune** to build channels from your library, or create channels
   manually (library paths, playlists, smart playlists).
4. Return to Kodi's **Live TV** section — your channels and EPG appear there.
5. Optional: open the **web UI** (`http://<host>:50001/manager.html`) for the
   full manager, EPG grid, seasonal calendar, and system diagnostics.

---

## Configuration Categories

| Category | What you can set |
|----------|------------------|
| Channels | Autotune, channel manager, default channel set, import/export |
| Options  | Grouping, favorites, clean recordings, recommended content |
| Global   | TCP port, host/name, PVR reload, Kodi access, debug |
| Fillers  | Bumpers, ratings, adverts, trailers, filler folders |
| Multi-room | Server discovery, auto-allow, remote sync |
| Integrations | OpenRouter AI artwork, generative model, web UI |

---

[Changelog](https://github.com/PseudoTV/PseudoTV_Live/raw/master/plugin.video.pseudotv.live/changelog.txt)

[Wiki: Github](https://github.com/PseudoTV/PseudoTV_Live/wiki)

[Forum: Kodi](https://forum.kodi.tv/showthread.php?tid=355549)

[Discussion: Kodi](https://forum.kodi.tv/showthread.php?tid=346803)

[Discussion: Github](https://github.com/PseudoTV/PseudoTV_Live/discussions)

[Discussion: Reddit](https://www.reddit.com/r/PseudoTV/)

[![License](https://img.shields.io/github/license/PseudoTV/PseudoTV_Live?style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/blob/master/LICENSE)
[![Codacy Badge](https://img.shields.io/codacy/grade/efcc007bd689449f8cf89569ac6a311b.svg?style=flat-square)](https://www.codacy.com/app/PseudoTV/PseudoTV_Live/dashboard)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/PseudoTV/PseudoTV_Live.svg?color=red&style=flat-square)](https://github.com/PseudoTV/PseudoTV_Live/commits?author=Lunatixz)
[![Kodi URL](https://img.shields.io/badge/Supports-Kodi%2019+-blue.svg?style=flat-square)](https://kodi.tv/download)
[![Donate to Kodi](https://img.shields.io/badge/Donate%20to-Kodi-blue.svg?style=flat-square)](https://kodi.tv/contribute/donate)
[![Donate to Lunatixzl](https://img.shields.io/badge/Donate%20to-Lunatixz-blue.svg?style=flat-square)](https://paypal.me/Lunatixz)

# Special Thanks:
- @xbmc If you are enjoying this project please donate to Kodi!
- @phunkyfish for his continued work and help with IPTV Simple.
- @IAmJayFord for awesome PseudoTV Live Icon/Fanart sets.
- @preroller for fantastic PseudoTV Live Bumpers.

# GitHub Sponsors

A huge thank you to our generous sponsors who help keep PseudoTV Live development going!

[![Sponsors](https://img.shields.io/github/sponsors/PseudoTV?label=Sponsors&style=for-the-badge)](https://github.com/sponsors/PseudoTV)

<!-- AUTO-SPONSORS-START -->
<!-- This section is auto-updated by GitHub Actions -->
*Sponsor list available on the [Sponsors page](https://github.com/sponsors/PseudoTV)*
<!-- AUTO-SPONSORS-END -->

### License

* [GNU GPL v3](http://www.gnu.org/licenses/gpl.html)
* Copyright 2009-2025

### Community

<p align="center"><a href="https://www.pseudotvlive.com"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/pseudotv.png" height="40" alt="PseudoTV Live"></a>&nbsp;&nbsp;<a href="https://www.youtube.com/@PseudoTVLive"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/youtube.png" height="40" alt="YouTube"></a>&nbsp;&nbsp;<a href="https://github.com/PseudoTV/PseudoTV_Live/discussions"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/github.png" height="40" alt="GitHub"></a>&nbsp;&nbsp;<a href="https://www.reddit.com/r/PseudoTV"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/reddit.png" height="40" alt="Reddit"></a>&nbsp;&nbsp;<a href="https://discord.com/channels/726310663605190662/726310664032878602"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/discord.png" height="40" alt="Discord"></a>&nbsp;&nbsp;<a href="https://bsky.app/profile/pseudotv.com"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/bluesky.png" height="40" alt="Bluesky"></a>&nbsp;&nbsp;<img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/instagram.png" height="40" alt="Instagram">&nbsp;&nbsp;<a href="https://forum.kodi.tv/forumdisplay.php?fid=231"><img src="https://raw.githubusercontent.com/PseudoTV/PseudoTV_Live/master/wiki/images/kodi.png" height="40" alt="Kodi Forum"></a></p>
