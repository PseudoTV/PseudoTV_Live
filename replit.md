# PseudoTV Live - Kodi Addon Repository

## Overview
This is a Kodi addon repository for PseudoTV Live, which acts like a set-top box for Kodi. The project contains the main plugin, repository metadata, and a web interface addon.

**Current State:** Successfully imported and ready for development
**Last Updated:** December 8, 2024

## Project Structure

### Main Components
- **plugin.video.pseudotv.live/** - Main PseudoTV Live addon (v0.6.1q)
  - Resources, skins, libraries, and media files
  - Python-based Kodi plugin for simulating broadcast/cable TV
  
- **repository.pseudotv/** - Repository metadata (v1.0.9)
  
- **webinterface.pseudotv.live/** - Web interface addon (v0.0.1)

- **zips/** - Generated addon zip packages for distribution

### Build System
- **addon_generator.py** - Main build script that:
  - Cleans temporary files and folders
  - Generates addons.xml from all addon.xml files
  - Creates MD5 checksums
  - Packages addons into distributable zip files
  - Generates language reports

- **addon_generator_zip_only.py** - Alternative script for zip generation only

## Workflow

The project has a configured workflow called "Build Addons" that runs:
```
python addon_generator.py
```

This workflow:
1. Scans all addon directories
2. Generates consolidated addons.xml
3. Creates MD5 hash for verification
4. Packages each addon into versioned zip files in the zips/ directory
5. Copies icons, fanart, and screenshots
6. Generates a language report

## Development Setup

**Language:** Python 3.12
**Environment:** Replit NixOS

The project is ready to use. Simply run the "Build Addons" workflow to regenerate all addon packages.

## Files Generated
- `addons.xml` - Combined metadata from all addons
- `addons.xml.md5` - MD5 hash for verification
- `zips/[addon-name]/[addon-name]-[version].zip` - Packaged addons
- `language_report.txt` - Language string analysis

## Recent Changes

### December 8, 2024: Channel Switching and Filler Handling Fixes

**Problem 1:** When bumpers/adverts were playing during a channel switch, the callback would return to the old channel instead of continuing on the new channel.

**Fix:** Enhanced `_onChange()` in service.py to detect filler content and refresh the callback URL to the current channel before executing playback continuation.

**Problem 2:** Post-roll adverts could loop infinitely when no items fit the remaining runtime.

**Fix:** Improved loop termination in fillers.py with:
- Track skipped items by file path to prevent infinite re-adding
- Reset tracking when an item is successfully added (runtime changed)
- Break early when all remaining items are too long for available runtime
- Added additional logging for debugging

**Problem 3:** MP4 duration parsing could fail for files where mvhd box doesn't have valid data.

**Fix:** Added fallback to parse trak/mdhd boxes for duration when mvhd fails in MP4Parser.py.

### December 8, 2024: MP4 Parsing and Post-Roll Fixes

**Problem:** Videos with post-roll content were playing indefinitely due to MP4 duration parsing failures.

**Root Cause:** When MP4 duration couldn't be parsed (due to moov atom placement, corrupt files, or unusual formats), duration was returned as 0, causing post-roll filler loops to never terminate.

**Fixes Applied:**

1. **MP4Parser.py** - Enhanced MP4 duration parsing:
   - Added handling for moov atom at end of file (after mdat block)
   - Added support for extended size boxes (64-bit lengths)
   - Improved error handling with detailed logging
   - Added loop protection with max iterations
   - Returns float durations to preserve precision

2. **videoparser.py** - Added fallback mechanisms:
   - New `_getKodiDuration()` method to retrieve duration from Kodi database
   - Fallback chain: primary parser -> external parsers -> Kodi database
   - Duration validation that only rejects clearly invalid values (None, negative)
   - Preserves fractional durations

3. **fillers.py** - Improved post-roll handling:
   - Added `_validateFillerDuration()` method for consistent validation
   - Loop protection with `maxIterations=1000` to prevent infinite loops
   - Detailed logging for debugging filler injection
   - Removed hard duration caps that blocked legitimate content

### December 8, 2024: Project Import
- Python 3.12 installed
- Build workflow verified and working
- Generated addon packages successfully

## User Preferences
None recorded yet.

## Project Architecture
This is a Kodi addon repository project that uses Python scripts to automate the packaging and distribution of Kodi addons. The build system follows Kodi addon repository conventions.

### Key Files Modified for MP4/Post-roll Fixes:
- `plugin.video.pseudotv.live/resources/lib/parsers/MP4Parser.py` - Enhanced MP4 duration parsing
- `plugin.video.pseudotv.live/resources/lib/videoparser.py` - Added fallback duration mechanism
- `plugin.video.pseudotv.live/resources/lib/fillers.py` - Improved post-roll handling with safeguards

## Known Issues
- **10-bit video (HDR) playback**: Not a plugin issue - devices without hardware 10-bit video decoding support will show codec errors. This is a device/Kodi limitation, not PseudoTV Live.

## Future Enhancements

### Show-Specific Bumpers (Planned)
**Feature Request:** Add support for "You're watching X" and "Up next: X" bumpers that are specific to the currently playing show.

**Implementation Notes:**
- Would require extending the bumper system to support template-based bumpers
- Bumpers could be dynamically generated or selected based on show metadata
- Integration with the existing `isFiller()` detection in service.py
- Special handling needed for show-specific content in the callback mechanism

**Status:** Documented for future implementation. The filler infrastructure (pre-rolls, post-rolls, bumpers) is already in place and could be extended to support this feature.
