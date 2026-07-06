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
import hashlib
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

GITPATH = os.path.dirname(os.path.abspath(__file__))
ZIPPATH = os.path.join(GITPATH, 'zips')
DELETE_EXT = ('.pyc', '.pyo', '.db')
DELETE_FOLDERS = {'__pycache__', '.idea', 'Corel Auto-Preserve', 'venv'}


class Generator:
    """Generates addons.xml and addons.xml.md5 from addon.xml files."""

    def __init__(self):
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        self._zipit(GITPATH)
        print("Finished updating addons xml and md5 files")

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
    Generator()
