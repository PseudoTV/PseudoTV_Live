# Translation Merge Summary

## Current State
- **GitHub Workflow**: Separate translate job that creates PRs for approval
- **Local Build**: No translation functionality

## Merged Approach
Keep the local version as the primary translation updater since:
1. It integrates with the build process
2. It's simpler and more direct
3. Single source of truth for translations

## Key Features to Keep
1. **Change Detection**: Check if en_gb strings.po changed
2. **AI Translation**: Use OpenCode to translate to 5 languages
3. **Language Support**: esES, deDE, frFR, ptBR
4. **Placeholder Preservation**: Keep %s, [B], [/B], [COLOR=...], [CR], {name}, {group}
5. **strings.po Generation**: Create proper Kodi language files

## Changes Made
1. Added `_update_translations()` method to Generator class
2. Called after tests pass and before changelog update
3. Removed translate job from GitHub workflow
4. Updated report job to remove translate references

## Result
- Single source of truth for translations
- Reduced workflow complexity
- Consistent behavior between local and CI builds
