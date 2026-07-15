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
import subprocess
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

GITPATH = os.path.dirname(os.path.abspath(__file__))
ZIPPATH = os.path.join(GITPATH, 'zips')
DELETE_EXT = ('.pyc', '.pyo', '.db')
DELETE_FOLDERS = {'__pycache__', '.idea', 'Corel Auto-Preserve', 'venv'}
ADDON_DIR = os.path.join(GITPATH, 'plugin.video.pseudotv.live')
TEST_DIR = os.path.join(ADDON_DIR, 'tests')
CHANGELOG = os.path.join(ADDON_DIR, 'changelog.txt')
ADDON_XML = os.path.join(ADDON_DIR, 'addon.xml')


class Generator:
    """Generates addons.xml and addons.xml.md5 from addon.xml files."""

    def __init__(self, run_tests=True):
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        if run_tests:
            if not self._run_local_tests():
                print("\nTests failed. Aborting build.")
                sys.exit(1)
            self._update_changelog()
        self._zipit(GITPATH)
        print("Finished updating addons xml and md5 files")

    def _run_local_tests(self):
        """Run pytest on local test suite before building."""
        if not os.path.isdir(TEST_DIR):
            print("Test directory not found, skipping tests")
            return True

        print("\n" + "=" * 60)
        print("Running local test suite...")
        print("=" * 60)

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

            print(result.stdout)
            if result.stderr:
                print(result.stderr)

            if result.returncode == 0:
                print("=" * 60)
                print("All tests passed!")
                print("=" * 60 + "\n")
                return True
            else:
                print("=" * 60)
                print("TESTS FAILED!")
                print("=" * 60 + "\n")
                return False

        except subprocess.TimeoutExpired:
            print("Tests timed out after 120 seconds")
            return False
        except FileNotFoundError:
            print("pytest not found. Install with: pip install pytest")
            return True
        except Exception as e:
            print(f"Error running tests: {e}")
            return True

    def _update_changelog(self):
        """Generate changelog entry using AI and update changelog.txt."""
        if not os.path.exists(CHANGELOG):
            print("changelog.txt not found, skipping changelog update")
            return

        # Get git diff for changes
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
            diff = result.stdout[:20000]
            if not diff.strip():
                print("No changes detected for changelog")
                return
        except Exception as e:
            print(f"Could not get git diff: {e}")
            return

        # Get changed file names
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

        # Read version from addon.xml
        try:
            tree = xml.etree.ElementTree.parse(ADDON_XML)
            raw_version = tree.getroot().get('version')
        except Exception as e:
            print(f"Could not read version from addon.xml: {e}")
            return

        if not raw_version:
            print("No version found in addon.xml")
            return

        version = f"v.{raw_version}"
        print(f"\nGenerating changelog entry for version {version}...")

        # Use OpenCode AI to generate changelog entry
        keywords = "Improved|Added|Tweaked|Refactored|Fixed|Resolved|Optimized|Moved|Introduced|Enhanced|Refined|Implemented|Replaced|Removed"
        prompt = (
            f"Generate a changelog entry for these code changes to PseudoTV Live Kodi addon. "
            f"You MUST use ONE of these EXACT keywords to start: {keywords}. "
            f"Follow the dash with a space then the keyword. Keep it concise (1-2 lines max). "
            f"Focus on user-facing changes, new features, improvements, or bug fixes. "
            f"Do not include file names or technical details. "
            f"CHANGED FILES: {files}\nCODE DIFF: {diff}\n"
            f"Output ONLY the changelog line starting with dash, nothing else."
        )

        try:
            result = subprocess.run(
                ['opencode', 'run', '--model', 'opencode/mimo-v2.5-free', prompt],
                cwd=GITPATH,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            raw_output = result.stdout
        except FileNotFoundError:
            print("OpenCode not found, skipping changelog generation")
            return
        except Exception as e:
            print(f"Error running OpenCode: {e}")
            return

        # Extract and validate changelog entry
        lines = raw_output.strip().split('\n')
        changelog_entry = ""
        for line in lines:
            line = line.strip()
            if line.startswith('- '):
                changelog_entry = re.sub(r'[^\w\s._/-]', '', line)
                break

        if not changelog_entry:
            print("No valid changelog entry generated")
            return

        if not re.match(rf'^- ({keywords})', changelog_entry):
            print(f"Invalid changelog entry format: {changelog_entry}")
            return

        print(f"Generated entry: {changelog_entry}")

        # Update changelog.txt
        with open(CHANGELOG, 'r', encoding='utf-8') as f:
            content = f.read()

        if version in content:
            # Version exists, append entry
            print(f"Appending to existing version {version} section")
            lines = content.split('\n')
            new_lines = []
            version_line_idx = -1
            insert_idx = -1

            # Find the version line and determine insertion point
            for i, line in enumerate(lines):
                if line.strip() == version and version_line_idx == -1:
                    version_line_idx = i
                    new_lines.append(line)
                    continue

                if version_line_idx != -1 and insert_idx == -1:
                    # We're under the target version section
                    if line.startswith('v.'):
                        # Hit next version, insert before it
                        insert_idx = len(new_lines)
                        new_lines.append(changelog_entry)
                        new_lines.append(line)
                    elif i == len(lines) - 1:
                        # End of file, append here
                        new_lines.append(line)
                        new_lines.append(changelog_entry)
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

            # If we found version but haven't inserted yet (version was last section)
            if version_line_idx != -1 and insert_idx == -1:
                new_lines.append(changelog_entry)

            content = '\n'.join(new_lines)
        else:
            # New version, add at top after notice
            print(f"Adding new version section for {version}")
            notice = "### NOTICE: The nightly branch is in alpha; things will break! ####"
            if notice in content:
                content = content.replace(notice, f"{notice}\n{version}\n{changelog_entry}\n")
            else:
                content = f"{notice}\n{version}\n{changelog_entry}\n\n{content}"

        with open(CHANGELOG, 'w', encoding='utf-8') as f:
            f.write(content)

        print("Changelog updated successfully")

    def _clean_addons(self):
        for root, dirnames, filenames in os.walk(GITPATH):
            for dirname in dirnames:
                if dirname in DELETE_FOLDERS:
                    path = os.path.join(root, dirname)
                    try:
                        print(f"removing: {dirname}")
                        try:
                            os.rmdir(path)
                        except OSError:
                            rmtree(path)
                    except Exception:
                        pass
            for filename in filenames:
                if filename.endswith(DELETE_EXT):
                    print(f"removing: {filename}")
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
                print(f"Excluding {addon_path} for {e}")

        addons_xml = addons_xml.strip() + "\n</addons>\n"
        self._save_file(addons_xml.encode("UTF-8"), "addons.xml")

    def _generate_md5_file(self):
        try:
            with open(os.path.join(GITPATH, "addons.xml"), "r", encoding="UTF-8") as f:
                m = hashlib.md5(f.read().encode("UTF-8")).hexdigest()
            self._save_file(m.encode("UTF-8"), "addons.xml.md5")
        except Exception as e:
            print(f"An error occurred creating addons.xml.md5 file!\n{e}")

    def _save_file(self, data, filename):
        try:
            with open(os.path.join(GITPATH, filename), "wb") as f:
                f.write(data)
        except Exception as e:
            print(f"An error occurred saving {filename} file!\n{e}")

    def get_plugin_version(self, addon_dir):
        addon_file = os.path.join(addon_dir, 'addon.xml')
        if not os.path.exists(addon_file):
            return None
        try:
            with open(addon_file, 'r', encoding="utf-8") as f:
                node = xml.etree.ElementTree.XML(f.read())
            return node.get('version')
        except Exception as e:
            print(f'Failed to open {addon_file}: {e}')
            return None

    def create_zip_file(self, fpath, addon):
        print(f"addon_dir: {addon}")
        version = self.get_plugin_version(os.path.join(fpath, addon))
        if not version:
            return
        print(f"version: {version}")

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
        print(f"fpath in zipgen: {fpath}")
        dirs = os.listdir(fpath)
        print(f"{len(dirs)} dirs found in zipgen")

        for addon_dir in dirs:
            directory = os.path.join(fpath, addon_dir)
            if not os.path.isdir(directory) or addon_dir.startswith(('.', 'download')):
                continue
            print(f"processing... {addon_dir}")
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
