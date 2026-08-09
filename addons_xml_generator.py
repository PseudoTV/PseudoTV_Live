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
import time
import hashlib
import msvcrt
import datetime
import subprocess
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

LOG_FILE = None

def _prompt_skip(step_name, seconds=5):
    _log(f"\n{step_name} — press any key to skip ({seconds}s)...")
    for remaining in range(seconds, 0, -1):
        _log(f"  {remaining}s remaining...")
        if msvcrt.kbhit():
            msvcrt.getch()
            _log(f"Skipped {step_name}")
            return True
        time.sleep(1)
    _log(f"Proceeding with {step_name}")
    return False

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
ZIP_SKIP_DIRS = {'tests', 'graphify-out', '.opencode', '.github', 'wiki', '__pycache__', '.pytest_cache', '.git', '.idea'}
ZIP_SKIP_FILES = {'todo.md', 'generator.log', 'AGENTS.md', 'SESSION_BACKUP.md', 'task_plan.md',
                  'progress.md', 'findings.md', 'pytest.ini', '.gitignore', '.gitattributes', '.project'}
ADDON_DIR = os.path.join(GITPATH, 'plugin.video.pseudotv.live')
TEST_DIR = os.path.join(ADDON_DIR, 'tests')
CHANGELOG = os.path.join(ADDON_DIR, 'changelog.txt')
TODO_FILE = os.path.join(ADDON_DIR, 'todo.md')
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

OPENCODE_MODEL = 'opencode-go/deepseek-v4-flash'


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
            self._scan_todos()
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        self._zipit(GITPATH)
        _log("Finished updating addons xml and md5 files")
        if sys.stdin.isatty():
            _log("\nPress any key to close (30s)...")
            for _ in range(30):
                if msvcrt.kbhit():
                    msvcrt.getch()
                    break
                time.sleep(1)

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
                ['git', 'diff', 'HEAD~3', '--', EN_GB_FILE],
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
        if _prompt_skip('translations'):
            return

        for lang_code, lang_name in LANGUAGES.items():
            folder_code = lang_code[:2].lower() + '_' + lang_code[2:].lower()
            lang_dir = os.path.join(LANG_DIR, f'resource.language.{folder_code}')
            lang_file = os.path.join(lang_dir, 'strings.po')
            os.makedirs(lang_dir, exist_ok=True)

            # Read existing translations to skip already-translated IDs
            existing_content = ''
            existing_ids = set()
            if os.path.isfile(lang_file):
                with open(lang_file, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
                existing_ids = set(re.findall(r'msgctxt "#(\d+)"', existing_content))

            needed_ids = [sid for sid in changed_ids if sid not in existing_ids]
            if not needed_ids:
                _log(f"{lang_name} — all strings already translated, skipped")
                continue

            needed_lines = []
            for sid in needed_ids:
                match = re.search(rf'msgctxt "#{sid}"\s*\nmsgid "([^"]*)"', en_gb_content)
                if match:
                    needed_lines.append(f"#{sid}|{match.group(1)}")
            if not needed_lines:
                continue
            strings_text = '\n'.join(needed_lines)
            prompt = (
                f"Translate these Kodi addon UI strings from English to {lang_name}. "
                f"Keep all placeholders unchanged. "
                f"Only output translations in format: #ID|translation. "
                f"Do NOT read any files or use glob tool.\n"
                f"Strings:\n{strings_text}"
            )

            opencode_bin = os.path.join(_opencode_dir, 'opencode.exe')
            if not os.path.isfile(opencode_bin):
                _log("OpenCode binary not found, skipping translations")
                return
            try:
                result = subprocess.run(
                    [opencode_bin, 'run', '--model', OPENCODE_MODEL, prompt],
                    cwd=GITPATH, capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=120
                )
            except FileNotFoundError:
                _log(f"OpenCode CLI not found, skipping")
                return
            except subprocess.TimeoutExpired:
                _log(f"OpenCode timed out for {lang_name}, skipping")
                continue
            except Exception as e:
                _log(f"Error running OpenCode for {lang_name}: {e}")
                continue

            translations = {}
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if '|' in line and (line[0].isdigit() or (line.startswith('#') and len(line) > 1 and line[1].isdigit())):
                    parts = line.split('|', 1)
                    if len(parts) == 2:
                        translations[parts[0].strip().lstrip('#')] = parts[1].strip()

            if not translations:
                _log(f"Translation failed for {lang_name}, skipping")
                continue

            if existing_content:
                with open(lang_file, 'a', encoding='utf-8') as f:
                    for string_id, translation in translations.items():
                        match = re.search(rf'msgctxt "#{string_id}"\s*\nmsgid "([^"]*)"', en_gb_content)
                        if match:
                            msgid = match.group(1)
                            f.write(f'\nmsgctxt "#{string_id}"\nmsgid "{msgid}"\nmsgstr "{translation.replace(chr(34), chr(92) + chr(34))}"\n')
                _log(f"Appended {len(translations)} strings to {lang_file}")
            else:
                with open(lang_file, 'w', encoding='utf-8') as f:
                    f.write('# Kodi Media Center language file\n# Addon Name: "PseudoTV Live"\n# Addon id: plugin.video.pseudotv.live\n# Addon Provider: Lunatixz\nmsgid ""\nmsgstr ""\n'
                            f'"Project-Id-Version: plugin.video.pseudotv.live\\n"\n"Report-Msgid-Bugs-To: \\n"\n"POT-Creation-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n'
                            f'"PO-Revision-Date: YEAR-MO-DA HO:MI+ZONE\\n"\n"Last-Translator: Lunatixz Translation Team\\n"\n'
                            f'"Language-Team: {lang_name}\\n"\n"MIME-Version: 1.0\\n"\n"Content-Type: text/plain; charset=UTF-8\\n"\n'
                            f'"Content-Transfer-Encoding: 8bit\\n"\n"Language: {folder_code}\\n"\n"Plural-Forms: nplurals=2; plural=(n != 1);\\n"\n')
                    for string_id, translation in translations.items():
                        match = re.search(rf'msgctxt "#{string_id}"\s*\nmsgid "([^"]*)"', en_gb_content)
                        if match:
                            msgid = match.group(1)
                            f.write(f'\nmsgctxt "#{string_id}"\nmsgid "{msgid}"\nmsgstr "{translation.replace(chr(34), chr(92) + chr(34))}"\n')
                _log(f"Created {lang_file}")

        _log("Translation complete")

    def _update_changelog(self):
        """Generate up to 20 changelog entries using AI, prioritized by user relevance."""
        if not os.path.exists(CHANGELOG):
            _log("changelog.txt not found, skipping changelog update")
            return

        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD~3', '--', '*.py', '*.xml', '*.json'],
                cwd=GITPATH,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=10
            )
            diff = result.stdout[:15000]
            if not diff.strip():
                _log("No changes detected for changelog")
                return
        except Exception as e:
            _log(f"Could not get git diff: {e}")
            return

        try:
            result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD~3', '--', '*.py', '*.xml', '*.json'],
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
        if _prompt_skip('changelog'):
            return

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
            f"Generate changelog entries, one per line. ONLY list changes that are important for users to know about "
            f"or for developers to document: new features, notable bug fixes, significant improvements, "
            f"or behavior changes. Skip trivial refactors, internal-only cleanup, or minor cosmetic changes. "
            f"Lump any minor tweaks into a single entry like '- Tweaked Miscellaneous improvements and tweaks.' "
            f"Each line MUST start with '- ' and ONE of these EXACT keywords: {keywords}. "
            f"Keep each entry concise (1-2 lines). Order by most relevant to users first. "
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

        _log(f"Generated {len(changelog_entries)} changelog entries")

        with open(CHANGELOG, 'r', encoding='utf-8') as f:
            content = f.read()

        entries_text = '\n'.join(changelog_entries)

        if version in content:
            _log(f"Appending {len(changelog_entries)} entries to existing {version} section")
            lines = content.split('\n')
            new_lines = []
            in_ver = False
            inserted = False

            for i, line in enumerate(lines):
                if line.strip() == version and not in_ver:
                    in_ver = True
                    new_lines.append(line)
                    continue

                if in_ver and not inserted:
                    next_is_end = (i + 1 < len(lines) and lines[i + 1].startswith('v.')) or i >= len(lines) - 1
                    if not line.strip():
                        continue
                    new_lines.append(line)
                    if next_is_end:
                        new_lines.append(entries_text)
                        inserted = True
                else:
                    new_lines.append(line)

                content = '\n'.join(new_lines)
        else:
            _log(f"Adding new version section for {version}")
            notice = "### NOTICE: The nightly branch is in alpha; things will break! ####"
            if notice in content:
                content = content.replace(notice, f"{notice}\n{version}\n{entries_text}")
            else:
                content = f"{notice}\n{version}\n{entries_text}\n{content}"

        with open(CHANGELOG, 'w', encoding='utf-8') as f:
            f.write(content)

        _log("Changelog updated successfully")

    def _scan_todos(self):
        _log("\nScanning for TODO comments...")
        lib_dir = os.path.join(ADDON_DIR, 'resources', 'lib')
        if not os.path.isdir(lib_dir):
            _log("lib directory not found, skipping TODO scan")
            return

        todos = []
        for root, dirs, files in os.walk(lib_dir):
            for f in files:
                if not f.endswith('.py'):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, ADDON_DIR)
                with open(path, 'r', encoding='utf-8', errors='replace') as fh:
                    for i, line in enumerate(fh, 1):
                        lower = line.lower()
                        if 'todo' not in lower:
                            continue
                        idx = lower.find('todo')
                        if idx == 0 or (idx > 0 and not line[idx-1].isalpha()):
                            todos.append((rel, i, line.strip()))

        if not todos:
            _log("No TODOs found")
            return

        # Check which TODOs are already documented
        known_lines = set()
        if os.path.isfile(TODO_FILE):
            with open(TODO_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            for pair in re.findall(r'`([^`]+)`\s*\|\s*`(\d+)`', content):
                known_lines.add((pair[0], pair[1]))

        new_todos = [(f, l, t) for (f, l, t) in todos if (f, str(l)) not in known_lines]
        if not new_todos:
            _log(f"No new TODOs found (all {len(todos)} already documented)")
            return

        _log(f"Found {len(new_todos)} new TODOs (out of {len(todos)} total)")
        if _prompt_skip('TODO analysis'):
            return

        todos_text = '\n'.join(f"{f}|{l}|{t}" for f, l, t in new_todos)
        opencode_bin = os.path.join(_opencode_dir, 'opencode.exe')
        if not os.path.isfile(opencode_bin):
            _log("OpenCode not found, writing raw TODOs")
            self._write_todo_md(todos, None)
            return

        prompt = (
            "Do NOT read any files or use glob tool. "
            "Analyze these TODO comments from a Kodi addon codebase. "
            "Each line is: file|line|todo text. "
            "Categorize each TODO by type (feature, refactor, bugfix, cleanup, performance, deprecation) "
            "and assign a priority (HIGH/MEDIUM/LOW). "
            "Output ONLY a markdown table with columns: #, File, Line, TODO, Category, Priority. "
            "Sort by priority (HIGH first).\n"
            f"TODOs:\n{todos_text}"
        )

        try:
            result = subprocess.run(
                [opencode_bin, 'run', '--model', OPENCODE_MODEL, prompt],
                cwd=GITPATH, capture_output=True, text=True,
                encoding='utf-8', errors='replace', timeout=120
            )
            self._write_todo_md(todos, result.stdout)
        except Exception as e:
            _log(f"OpenCode analysis failed: {e}, writing raw TODOs")
            self._write_todo_md(todos, None)

    def _write_todo_md(self, todos, analysis):
        rows = []
        if analysis:
            for line in analysis.split('\n'):
                line = line.strip()
                if not line.startswith('|') or '---' in line or line.startswith('| -') or line.startswith('|#'):
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                        try:
                            rows.append({
                                'num': parts[1], 'file': parts[2], 'line': parts[3],
                                'todo': parts[4], 'cat': parts[5], 'pri': parts[6]
                            })
                        except IndexError:
                            pass

        with open(TODO_FILE, 'w', encoding='utf-8') as f:
            f.write("# 👾 PseudoTV Live - TODO List\n\n")
            f.write("> Auto-generated from code comments. Updated during local builds.\n\n")
            f.write(f"**Last scan:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`  \n")
            f.write(f"**Total:** `{len(todos)}` items")
            if rows:
                high = sum(1 for r in rows if r['pri'].upper() == 'HIGH')
                med  = sum(1 for r in rows if r['pri'].upper() == 'MEDIUM')
                low  = sum(1 for r in rows if r['pri'].upper() == 'LOW')
                f.write(f"  — 🔴 `{high}` HIGH · 🟡 `{med}` MEDIUM · 🟢 `{low}` LOW\n\n")
            else:
                f.write("\n\n")

            if not rows:
                f.write("| # | File | Line | TODO |\n")
                f.write("|---|------|------|------|\n")
                for i, (file, line, text) in enumerate(todos, 1):
                    text = text.replace('|', '/')
                    f.write(f"| {i} | `{file}` | `{line}` | {text} |\n")
                return

            for pri_label, pri_icon, pri_color in [
                ('HIGH', '🔴', 'dc3545'),
                ('MEDIUM', '🟡', '856404'),
                ('LOW', '🟢', '28a745'),
            ]:
                group = [r for r in rows if r['pri'].upper() == pri_label]
                if not group:
                    continue
                f.write(f"\n\n## {pri_icon} {pri_label} Priority\n\n")
                f.write(f"`{len(group)} item(s)`\n\n")
                f.write("| File | Line | TODO | Category |\n")
                f.write("|------|------|------|----------|\n")
                for r in group:
                    t = r['todo'].replace('|', '/')
                    f.write(f"| `{r['file']}` | `{r['line']}` | {t} | {r['cat']} |\n")

            f.write("\n\n---\n\n### 📋 Full Reference\n\n")
            f.write("| # | File | Line | TODO | Category | Priority |\n")
            f.write("|---|------|------|------|----------|----------|\n")
            for r in rows:
                t = r['todo'].replace('|', '/')
                f.write(f"| {r['num']} | `{r['file']}` | `{r['line']}` | {t} | {r['cat']} | {r['pri']} |\n")

        _log(f"Written {len(todos)} TODOs to {TODO_FILE}")

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
                # Prune skipped directories in-place so os.walk skips them
                dirs[:] = [d for d in dirs if d not in ZIP_SKIP_DIRS]
                for file_path in files:
                    if file_path.endswith('.zip') or file_path in ZIP_SKIP_FILES:
                        continue
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
