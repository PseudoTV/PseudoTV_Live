# PseudoTV Live - Kodi Addon Repository

## Overview
PseudoTV Live is a Kodi addon that transforms your Kodi Library and Sources into linear TV similar to broadcast television, complete with configurable channels and advanced channel rules. The interface is provided by Kodi via IPTV Simple PVR Backend.

## Project Structure
- `plugin.video.pseudotv.live/` - Main Kodi video plugin
- `repository.pseudotv/` - Kodi addon repository configuration
- `webinterface.pseudotv.live/` - Web interface addon (experimental)
- `zips/` - Pre-built addon packages
- `addon_generator.py` - Build script to generate repository files and zip packages

## Recent Changes
- **2025-12-08**: Fixed milliseconds to seconds conversion bug in duration handling
  - `jsonrpc.py`: Fixed `_getRuntime()` to convert `streamdetails.video.duration` from milliseconds to seconds
  - `VFSParser.py`: Added `_getDurationFromItem()` helper function with milliseconds conversion

## Bug Fix Details
The EPG was showing incorrect durations (e.g., 1440000 seconds instead of 1440 seconds) because:
- Kodi's `streamdetails.video[].duration` returns duration in **milliseconds**
- The code was using this value directly as seconds

The fix checks if the duration value is greater than 86400 (24 hours in seconds) and divides by 1000 to convert from milliseconds to seconds.

## Building
Run `python addon_generator.py` to:
1. Clean up temporary files
2. Generate `addons.xml` repository index
3. Generate `addons.xml.md5` checksum
4. Create zip packages for each addon

## Installation on Kodi
1. Install the repository from `zips/repository.pseudotv/`
2. Install PseudoTV Live from the repository
3. Configure channels through the addon settings

## Dependencies
- Kodi 19+ (Matrix or newer)
- IPTV Simple PVR Client
- Various Kodi script modules (see addon.xml for full list)

## License
GNU GPL v3
