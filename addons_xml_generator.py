"""
addons.xml generator
Copyright (C) 2018 Lunatixz
Copyright (C) 2012-2013 Garrett Brown
Copyright (C) 2010 j48antialias

This Program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2, or (at your option)
any later version.

This Program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with XBMC; see the file COPYING. If not, write to
the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
http://www.gnu.org/copyleft/gpl.html

Based on code by j48antialias:
https://anarchintosh-projects.googlecode.com/files/addons_xml_generator.py
"""

import os
import re
import sys
import hashlib
import datetime
import subprocess
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

LOG_FILE = None

def _log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}'
    print(line)
    if LOG_FILE:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + '\n')

GITPATH = os.path.dirname(os.path.abspath(__file__))
ZIPPATH = os.path.join(GITPATH, 'zips')

# ponytail: add opencode bin dir to PATH for subprocess calls
_opencode_dir = os.path.join(os.path.expanduser('~'), '.opencode', 'bin')
if os.path.isdir(_opencode_dir) and _opencode_dir not in os.environ.get('PATH', ''):
    os.environ['PATH'] = _opencode_dir + os.pathsep + os.environ.get('PATH', '')
DELETE_EXT = ('.pyc', '.pyo', '.db')
DELETE_FOLDERS = {'__pycache__', '.idea', 'Corel Auto-Preserve', 'venv'}
ADDON_DIR = os.path.join(GITPATH, 'plugin.video.pseudotv.live')
TEST_DIR = os.path.join(ADDON_DIR, 'tests')
CHANGELOG = os.path.join(ADDON_DIR, 'changelog.txt')
ADDON_XML = os.path.join(ADDON_DIR, 'addon.xml')
EN_GB_FILE = os.path.join(ADDON_DIR, 'resources', 'language', 'resource.language.en_gb', 'strings.po')
LANG_DIR = os.path.join(ADDON_DIR, 'resources', 'language')

# Top 5 Kodi languages by user base (excluding en_GB source)
LANGUAGES = {
    'esES': 'Spanish (Spain)',
    'deDE': 'German (Germany)',
    'frFR': 'French (France)',
    'ptBR': 'Portuguese (Brazil)',
    'jaJP': 'Japanese (Japan)',
}

OPENCODE_MODEL = 'opencode/mimo-v2.5-free'


class Generator:
    """Generates addons.xml and addons.xml.md5 from addon.xml files."""

    def __init__(self, run_tests=True):
        global LOG_FILE
        LOG_FILE = os.path.join(ADDON_DIR, 'generator.log')
        _log('=== Generator started ===')
        if run_tests:
            if not self._run_local_tests():
                _log("\nTests failed. Aborting build.")
                sys.exit(1)
            self._update_translations()
            self._update_changelog()
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        self._zipit(GITPATH)
        _log("Finished updating addons xml and md5 files")

    def _run_local_tests(self):
        """Run pytest on local test suite before building."""
        if not os.path.isdir(TEST_DIR):
            _log("Test directory not found, skipping tests")
            return True

        _log("\n" + "=" * 60)
        _log("Running local test suite...")
        _log("=" * 60)

        try:
            result = subprocess.run(
                [sys.executable, '-m', 'pytest', TEST_DIR, '-v', '--tb=short'],
                cwd=ADDON_DIR,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=120
            )

            _log(result.stdout)
            if result.stderr:
                _log(result.stderr)

            if result.returncode == 0:
                _log("=" * 60)
                _log("All tests passed!")
                _log("=" * 60 + "\n")
                return True
            else:
                _log("=" * 60)
                _log("TESTS FAILED!")
                _log("=" * 60 + "\n")
                return False

        except subprocess.TimeoutExpired:
            _log("Tests timed out after 120 seconds")
            return False
        except FileNotFoundError:
            _log("pytest not found. Install with: pip install pytest")
            return True
        except Exception as e:
            _log(f"Error running tests: {e}")
            return True

    def _update_translations(self):
        """Generate translations for changed strings.po entries using AI."""
        if not os.path.exists(EN_GB_FILE):
            _log("en_GB strings.po not found, skipping translations")
            return

        # Get git diff for en_gb strings.po changes
        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD~1', 'HEAD', '--', EN_GB_FILE],
                cwd=GITPATH,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            diff = result.stdout[:30000]
            if not diff.strip():
                _log("No changes detected in en_GB strings.po")
                return
        except Exception as e:
            _log(f"Could not get git diff: {e}")
            return

        # Extract changed msgctxt IDs from diff
        changed_ids = list(set(re.findall(r'msgctxt "#(\d+)"', diff)))
        if not changed_ids:
            _log("No new/changed string IDs detected")
            return

        _log(f"\nFound {len(changed_ids)} changed string IDs: {', '.join(changed_ids)}")

        # Read en_GB file to extract msgids
        try:
            with open(EN_GB_FILE, 'r', encoding='utf-8') as f:
                en_gb_content = f.read()
        except Exception as e:
            _log(f"Could not read en_GB strings.po: {e}")
            return

        # Build strings to translate
        strings_to_translate = []
        for string_id in changed_ids:
            # Extract msgid for this ID
            pattern = rf'msgctxt "#{string_id}"\s*\nmsgid "([^"]*)"'
            match = re.search(pattern, en_gb_content)
            if match:
                msgid = match.group(1)
                strings_to_translate.append(f"#{string_id}|{msgid}")

        if not strings_to_translate:
            _log("No strings to translate")
            return

        _log(f"Translating {len(strings_to_translate)} strings to {len(LANGUAGES)} languages...")

        # Generate translations for each language
        for lang_code, lang_name in LANGUAGES.items():
            # Convert lang code format: esES -> resource.language.es_es
            folder_code = lang_code[:2].lower() + '_' + lang_code[2:].lower()
            lang_dir = os.path.join(LANG_DIR, f'resource.language.{folder_code}')
            lang_file = os.path.join(lang_dir, 'strings.po')

            # Create directory if not exists
            os.makedirs(lang_dir, exist_ok=True)

            # Build translation prompt
            strings_text = '\n'.join(strings_to_translate)
            prompt = (
                f"Translate these Kodi addon UI strings from English to {lang_name}. "
                f"Keep all placeholders (%s, [B], [/B], [COLOR=...], [CR], {{name}}, {{group}}) unchanged. "
                f"Only output translations in format: #ID|translation. "
                f"Do NOT read any files or use glob tool.\n"
                f"Strings:\n{strings_text}"
            )

            opencode_bin = os.path.join(_opencode_dir, 'opencode.exe')
            if not os.path.isfile(opencode_bin):
                _log(f"OpenCode binary not found at {opencode_bin}, skipping")
                continue
            try:
                result = subprocess.run(
                    [opencode_bin, 'run', '--model', OPENCODE_MODEL, prompt],
                    cwd=GITPATH,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120
                )
                raw_output = result.stdout
            except FileNotFoundError:
                _log(f"OpenCode CLI not found, skipping translation for {lang_name}")
                continue
            except subprocess.TimeoutExpired:
                _log(f"OpenCode timed out for {lang_name} (120s), skipping")
                continue
            except Exception as e:
                _log(f"Error running OpenCode for {lang_name}: {e}")
                continue

            # Parse translations
            translations = {}
            for line in raw_output.strip().split('\n'):
                line = line.strip()
                if '|' in line and (line[0].isdigit() or (line.startswith('#') and len(line) > 1 and line[1].isdigit())):
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        translations[parts[0].strip().lstrip('#')] = parts[1].strip()

            if not translations:
                _log(f"Translation failed for {lang_name}, skipping")
                continue

            # Generate strings.po file
            with open(lang_file, 'w', encoding='utf-8') as f:
                f.write('# Kodi Media Center language file\n')
                f.write('# Addon Name: "PseudoTV Live"\n')
                f.write('# Addon id: plugin.video.pseudotv.live\n')
                f.write('# Addon Provider: Lunatixz\n')
                f.write('msgid ""\n')
                f.write('msgstr ""\n')
                f.write(f'"Project-Id-Version: plugin.video.pseudotv.live\\n"\n')
                f.write('"Report-Msgid-Bugs-To: \\n"\n')
                f.write('"POT-Creation-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n')
                f.write('"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n')
                f.write('"Last-Translator: Lunatixz Translation Team\\n"\n')
                f.write(f'"Language-Team: {lang_name}\\n"\n')
                f.write('"MIME-Version: 1.0\\n"\n')
                f.write('"Content-Type: text/plain; charset=UTF-8\\n"\n')
                f.write('"Content-Transfer-Encoding: 8bit\\n"\n')
                f.write(f'"Language: {folder_code}\\n"\n')
                f.write('"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n')

                # Append translated strings
                for string_id, translation in translations.items():
                    # Extract msgid from en_GB file
                    pattern = rf'msgctxt "#{string_id}"\s*\nmsgid "([^"]*)"'
                    match = re.search(pattern, en_gb_content)
                    if match:
                        msgid = match.group(1)
                        translation = translation.replace('"', '\\"')
                        f.write(f'\nmsgctxt "#{string_id}"\n')
                        f.write(f'msgid "{msgid}"\n')
                        f.write(f'msgstr "{translation}"\n')

            _log(f"Created {lang_file}")

        _log("Translation complete")

    def _update_changelog(self):
        """Generate up to 20 changelog entries using AI, prioritized by user relevance."""
        if not os.path.exists(CHANGELOG):
            _log("changelog.txt not found, skipping changelog update")
            return

        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD~1', 'HEAD', '--', '*.py', '*.xml', '*.json'],
                cwd=GITPATH,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            diff = result.stdout[:10000]
            if not diff.strip():
                _log("No changes detected for changelog")
                return
        except Exception as e:
            _log(f"Could not get git diff: {e}")
            return

        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~1', 'HEAD', '--', '*.py', '*.xml', '*.json'],
                cwd=GITPATH,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            files = result.stdout.strip() or "None"
        except Exception:
            files = "None"

        try:
            tree = xml.etree.ElementTree.parse(ADDON_XML)
            raw_version = tree.getroot().get('version')
        except Exception as e:
            _log(f"Could not read version from addon.xml: {e}")
            return

        if not raw_version:
            _log("No version found in addon.xml")
            return

        version = f"v.{raw_version}"
        _log(f"\nGenerating changelog entries for {version}...")

        existing_entries = []
        with open(CHANGELOG, 'r', encoding='utf-8') as f:
            in_ver = False
            for line in f.read().split('\n'):
                if line.strip() == version:
                    in_ver = True
                    continue
                if in_ver and line.startswith('v.'):
                    break
                if in_ver and line.startswith('- '):
                    existing_entries.append(line)

        keywords = "Improved|Added|Tweaked|Refactored|Fixed|Resolved|Optimized|Moved|Introduced|Enhanced|Refined|Implemented|Replaced|Removed"
        existing_text = '\n'.join(existing_entries) if existing_entries else 'None'
        prompt = (
            f"Review these code changes to PseudoTV Live Kodi addon. "
            f"Do NOT read any files or use glob tool. "
            f"Generate up to 20 changelog entries, one per line, prioritized by user-facing importance. "
            f"Each line MUST start with '- ' and ONE of these EXACT keywords: {keywords}. "
            f"Keep each entry concise (1-2 lines). Focus on user-facing changes: new features, bug fixes, "
            f"performance improvements, refactors users will notice. Skip internal-only refactors or "
            f"minor cleanup. Order by most relevant to users first. "
            f"If the diff is small, weigh whether each change is important enough to add "
            f"alongside existing entries for this version — don't add low-value entries just to fill space. "
            f"CHANGED FILES: {files}\nCODE DIFF: {diff}\n"
            f"EXISTING ENTRIES for {version}:\n{existing_text}\n"
            f"Output ONLY the dash-prefixed lines, nothing else."
        )

        try:
            opencode_bin = os.path.join(_opencode_dir, 'opencode.exe')
            if not os.path.isfile(opencode_bin):
                _log(f"OpenCode binary not found at {opencode_bin}, skipping changelog generation")
                return
            try:
                result = subprocess.run(
                    [opencode_bin, 'run', '--model', OPENCODE_MODEL, prompt],
                    cwd=GITPATH,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=120
                )
                raw_output = result.stdout
            except FileNotFoundError:
                _log("OpenCode CLI not found, skipping changelog generation")
                return
        except subprocess.TimeoutExpired:
            _log("OpenCode timed out (120s), skipping changelog generation")
            return
        except Exception as e:
            _log(f"Error running OpenCode: {e}")
            return

        changelog_entries = []
        for line in raw_output.strip().split('\n'):
            line = re.sub(r'[\x00-\x1f\x7f]', '', line.strip())
            if re.match(rf'^- ({keywords})', line):
                changelog_entries.append(line)

        if not changelog_entries:
            _log("No valid changelog entries generated")
            return

        changelog_entries = changelog_entries[:20]
        _log(f"Generated {len(changelog_entries)} changelog entries")

        with open(CHANGELOG, 'r', encoding='utf-8') as f:
            content = f.read()

        entry_count = 0
        in_version = False
        if version in content:
            for line in content.split('\n'):
                if line.strip() == version:
                    in_version = True
                    continue
                if in_version and line.startswith('v.'):
                    break
                if in_version and line.startswith('- '):
                    entry_count += 1

            max_new = 20 - entry_count
            if max_new <= 0:
                _log(f"Version already has {entry_count} entries (max 20). Skipping.")
                return
            if len(changelog_entries) > max_new:
                changelog_entries = changelog_entries[:max_new]
                _log(f"Truncated to {max_new} entries to stay within limit")

        entries_text = '\n'.join(changelog_entries)

        if version in content:
            _log(f"Appending {len(changelog_entries)} entries to existing {version} section")
            lines = content.split('\n')
            new_lines = []
            version_line_idx = -1
            insert_idx = -1

            for i, line in enumerate(lines):
                if line.strip() == version and version_line_idx == -1:
                    version_line_idx = i
                    new_lines.append(line)
                    continue

                if version_line_idx != -1 and insert_idx == -1:
                    if line.startswith('v.'):
                        insert_idx = len(new_lines)
                        new_lines.append(entries_text)
                        new_lines.append(line)
                    elif i == len(lines) - 1:
                        new_lines.append(line)
                        new_lines.append(entries_text)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            if version_line_idx != -1 and insert_idx == -1:
                new_lines.append(entries_text)

            content = '\n'.join(new_lines)
        else:
            _log(f"Adding new version section for {version}")
            notice = "### NOTICE: The nightly branch is in alpha; things will break! ####"
            if notice in content:
                content = content.replace(notice, f"{notice}\n{version}\n{entries_text}\n")
            else:
                content = f"{notice}\n{version}\n{entries_text}\n\n{content}"

        with open(CHANGELOG, 'w', encoding='utf-8') as f:
            f.write(content)

        _log("Changelog updated successfully")

    def _clean_addons(self):
        for root, dirnames, filenames in os.walk(GITPATH):
            for dirname in dirnames:
                if dirname in DELETE_FOLDERS:
                    path = os.path.join(root, dirname)
                    try:
                        _log(f"removing: {dirname}")
                        try:
                            os.rmdir(path)
                        except OSError:
                            rmtree(path)
                    except Exception:
                        pass
            for filename in filenames:
                if filename.endswith(DELETE_EXT):
                    _log(f"removing: {filename}")
                    os.remove(os.path.join(root, filename))

    def _generate_addons_file(self):
        addons_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<addons>\n'

        for addon in os.listdir(GITPATH):
            addon_path = os.path.join(GITPATH, addon, "addon.xml")
            if not os.path.isdir(os.path.join(GITPATH, addon)) or addon in (".svn", ".git"):
                continue
            try:
                with open(addon_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                addon_xml = "".join(line.rstrip() + "\n" for line in lines if "<?xml" not in line)
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception as e:
                _log(f"Excluding {addon_path} for {e}")

        addons_xml = addons_xml.strip() + "\n</addons>\n"
        self._save_file(addons_xml.encode("UTF-8"), "addons.xml")

    def _generate_md5_file(self):
        try:
            with open(os.path.join(GITPATH, "addons.xml"), "r", encoding="UTF-8") as f:
                m = hashlib.md5(f.read().encode("UTF-8")).hexdigest()
            self._save_file(m.encode("UTF-8"), "addons.xml.md5")
        except Exception as e:
            _log(f"An error occurred creating addons.xml.md5 file!\n{e}")

    def _save_file(self, data, filename):
        try:
            with open(os.path.join(GITPATH, filename), "wb") as f:
                f.write(data)
        except Exception as e:
            _log(f"An error occurred saving {filename} file!\n{e}")

    def get_plugin_version(self, addon_dir):
        addon_file = os.path.join(addon_dir, 'addon.xml')
        if not os.path.exists(addon_file):
            return None
        try:
            with open(addon_file, 'r', encoding="utf-8") as f:
                node = xml.etree.ElementTree.XML(f.read())
            return node.get('version')
        except Exception as e:
            _log(f'Failed to open {addon_file}: {e}')
            return None

    def create_zip_file(self, fpath, addon):
        _log(f"addon_dir: {addon}")
        version = self.get_plugin_version(os.path.join(fpath, addon))
        if not version:
            return
        _log(f"version: {version}")

        home = os.getcwd()
        os.chdir(fpath)

        path = os.path.join(ZIPPATH, addon)
        os.makedirs(path, exist_ok=True)

        # Copy icon
        icon_src = os.path.join(addon, 'icon.png')
        icon_alt = os.path.join(addon, 'resources', 'images', 'icon.png')
        if os.path.exists(icon_src):
            copyfile(icon_src, os.path.join(path, 'icon.png'))
        elif os.path.exists(icon_alt):
            copyfile(icon_alt, os.path.join(path, 'icon.png'))

        # Copy fanart
        fanart_src = os.path.join(addon, 'fanart.jpg')
        fanart_alt = os.path.join(addon, 'resources', 'images', 'fanart.jpg')
        if os.path.exists(fanart_src):
            copyfile(fanart_src, os.path.join(path, 'fanart.jpg'))
        elif os.path.exists(fanart_alt):
            copyfile(fanart_alt, os.path.join(path, 'fanart.jpg'))

        # Copy screenshots
        for i in range(1, 6):
            src = os.path.join(addon, 'resources', 'images', f'screenshot0{i}.png')
            if os.path.exists(src):
                copyfile(src, os.path.join(path, f'screenshot0{i}.png'))
            else:
                break

        # Create zip
        zip_path = os.path.join(ZIPPATH, addon, f'{addon}-{version}.zip')
        with ZipFile(zip_path, 'w') as addonzip:
            for root, dirs, files in os.walk(addon):
                for file_path in files:
                    if not file_path.endswith('.zip'):
                        addonzip.write(os.path.join(root, file_path))

        os.chdir(home)

    def _zipit(self, fpath):
        fpath = fpath or "."
        _log(f"fpath in zipgen: {fpath}")
        dirs = os.listdir(fpath)
        _log(f"{len(dirs)} dirs found in zipgen")

        for addon_dir in dirs:
            directory = os.path.join(fpath, addon_dir)
            if not os.path.isdir(directory) or addon_dir.startswith(('.', 'download')):
                continue
            _log(f"processing... {addon_dir}")
            self.create_zip_file(fpath, addon_dir)


if __name__ == "__main__":
    run_tests = '--no-tests' not in sys.argv
    exit_code = 0
    try:
        Generator(run_tests=run_tests)
    except SystemExit as e:
        exit_code = e.code
    if exit_code != 0 and sys.stdin.isatty():
        input("\nPress Enter to exit...")
    sys.exit(exit_code)
