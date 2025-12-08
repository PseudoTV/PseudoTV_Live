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

**Language:** Python 3.11
**Environment:** Replit NixOS

The project is ready to use. Simply run the "Build Addons" workflow to regenerate all addon packages.

## Files Generated
- `addons.xml` - Combined metadata from all addons
- `addons.xml.md5` - MD5 hash for verification
- `zips/[addon-name]/[addon-name]-[version].zip` - Packaged addons
- `language_report.txt` - Language string analysis

## Recent Changes
- December 8, 2024: Project imported and configured for Replit environment
  - Python 3.11 installed
  - Build workflow verified and working
  - Generated addon packages successfully

## User Preferences
None recorded yet.

## Project Architecture
This is a Kodi addon repository project that uses Python scripts to automate the packaging and distribution of Kodi addons. The build system follows Kodi addon repository conventions.
