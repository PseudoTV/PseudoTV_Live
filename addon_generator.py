# *
# *  Copyright (C) 2018      Lunatixz
# *  Copyright (C) 2012-2013 Garrett Brown
# *  Copyright (C) 2010      j48antialias
# *
# *  This Program is free software; you can redistribute it and/or modify
# *  it under the terms of the GNU General Public License as published by
# *  the Free Software Foundation; either version 2, or (at your option)
# *  any later version.
# *
# *  This Program is distributed in the hope that it will be useful,
# *  but WITHOUT ANY WARRANTY; without even the implied warranty of
# *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# *  GNU General Public License for more details.
# *
# *  You should have received a copy of the GNU General Public License
# *  along with XBMC; see the file COPYING.  If not, write to
# *  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
# *  http://www.gnu.org/copyleft/gpl.html
# *
# *  Based on code by j48antialias:
# *  https://anarchintosh-projects.googlecode.com/files/addons_xml_generator.py
 
""" addons.xml generator """
 
import os, sys, fnmatch
import xml.etree.ElementTree
from zipfile import ZipFile
from shutil import copyfile, rmtree

CHKPATH    = 'D:/GitHub/addon-check/'
GITPATH    = 'D:/GitHub/PseudoTV_Live/'
ZIPPATH    = os.path.join(GITPATH,'zips','')
DELETE_EXT = ('.pyc', '.pyo', '.db')
DELETE_FOLDERS = ['__pycache__','.idea','Corel Auto-Preserve']

# Compatibility with 3.0, 3.1 and 3.2 not supporting u"" literals
if sys.version < '3':
    import codecs
    def u(x):
        return codecs.unicode_escape_decode(x)[0]
else:
    def u(x):
        return x

class Generator(object):
    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from the root of
        the checked-out repo. Only handles single depth folder structure.
    """
    def __init__(self):
        # generate files
        self._clean_addons()
        self._generate_addons_file()
        self._generate_md5_file()
        self._zipit(GITPATH)
        # self.runCheck()
        # notify user
        print("Finished updating addons xml and md5 files")
    
    
    # def runCheck(self):
        # print 'runCheck'
        # for path in self.newPaths:
        # kodi-addon-checker <path-to-addon>
    
    def _clean_addons(self):
        for root, dirnames, filenames in os.walk(GITPATH):
            for dirname in dirnames:
                if dirname in DELETE_FOLDERS:
                    try:
                        print("found: " + dirname)
                        try:
                            os.rmdir(os.path.join(root, dirname))
                        except: 
                            rmtree(os.path.join(root, dirname))
                        print("removing: " + dirname)
                    except: pass
            for filename in filenames:
                if filename.endswith(DELETE_EXT):
                    print("removing: " + filename)
                    os.remove(os.path.join(root, filename))
                 
                 
    def _generate_addons_file( self ):
        # addon list
        addons = os.listdir(GITPATH)
        # final addons text
        addons_xml = u("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>\n<addons>\n")
        # loop thru and add each addons addon.xml file
        for addon in addons:
            try:
                # skip any file or .svn folder or .git folder
                if ( not os.path.isdir( addon ) or addon == ".svn" or addon == ".git" ): continue
                # create path
                _path = os.path.join( addon, "addon.xml" )
                # split lines for stripping
                xml_lines = open( _path, "r", encoding="utf8").read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if ( line.find( "<?xml" ) >= 0 ): continue
                    # add line
                    if sys.version < '3':
                        addon_xml += unicode( line.rstrip() + "\n", "UTF-8" )
                    else:
                        addon_xml += line.rstrip() + "\n"
                # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception as e:
                # missing or poorly formatted addon.xml
                print("Excluding %s for %s" % ( _path, e ))
        # clean and add closing tag
        addons_xml = addons_xml.strip() + u("\n</addons>\n")
        # save file
        self._save_file( addons_xml.encode( "UTF-8" ), file="addons.xml" )
    
    
    def _generate_md5_file( self ):
        # create a new md5 hash
        try:
            import md5
            m = md5.new( open( os.path.join(GITPATH,"addons.xml"), "r" , encoding="utf8").read() ).hexdigest()
        except ImportError:
            import hashlib
            m = hashlib.md5( open( os.path.join(GITPATH,"addons.xml"), "r", encoding="UTF-8" ).read().encode( "UTF-8" ) ).hexdigest()
        
        # save file
        try:
            self._save_file( m.encode( "UTF-8" ), file="addons.xml.md5" )
        except Exception as e:
            # oops
            print("An error occurred creating addons.xml.md5 file!\n%s" % e)
    
    def _save_file( self, data, file ):
        try:
            # write data to the file (use b for Python 3)
            open(os.path.join(GITPATH,file), "wb").write( data )
        except Exception as e:
            # oops
            print("An error occurred saving %s file!\n%s" % ( file, e ))
            
            
    def get_plugin_version( self, addon_dir):
        addon_file = os.path.join(addon_dir, 'addon.xml')
        if(not os.path.exists(addon_file)) :
            #not an addon directory
            return
        try:
            data = open(addon_file, 'r', encoding="utf8").read()
            node = xml.etree.ElementTree.XML(data)
            return(node.get('version'))
        except Exception as e:
            print ('Failed to open %s' % addon_file)
            print (e)

            
    def create_zip_file( self, fpath, addon):
        print("addon_dir: " + addon)
        version = self.get_plugin_version(os.path.join(fpath,addon))
        if not version: return
        print("version: " + version)
        home = os.getcwd()
        os.chdir(fpath)
        path = os.path.join(ZIPPATH,addon)
        if(not os.path.exists(path)) : os.makedirs(path)
        print("copying icon.png...")
        if os.path.exists(os.path.join(addon,'icon.png')): copyfile(os.path.join(addon,'icon.png'), os.path.join(path,'icon.png'))
        elif os.path.exists(os.path.join(addon,'resources','images','icon.png')): copyfile(os.path.join(addon,'resources','images','icon.png'), os.path.join(path,'icon.png'))
        print("copying fanart.jpg...")
        if os.path.exists(os.path.join(addon,'fanart.jpg')): copyfile(os.path.join(addon,'fanart.jpg'), os.path.join(path,'fanart.jpg'))
        elif os.path.exists(os.path.join(addon,'resources','images','fanart.jpg')): copyfile(os.path.join(addon,'resources','images','fanart.jpg'), os.path.join(path,'fanart.jpg'))
        if os.path.exists(os.path.join(addon,'resources','images','screenshot01.png')): 
            print("copying screenshots...")
            for i in range(1,6):
                try:
                    sspath = os.path.join(addon,'resources','images','screenshot0%d.png'%i)
                    copyfile(sspath, os.path.join(path,'screenshot0%d.png'%i))
                    print("copied %s..."%sspath)
                except: break
        with ZipFile(os.path.join(ZIPPATH,addon,addon + '-' + version + '.zip'),'w') as addonzip:
            for root, dirs, files in os.walk(addon):
                print("Root: "  + root )
                print("Dirs: "  + str(len(dirs)) )
                print("Files: " + str(len(files)) )
                for file_path in files:
                    if file_path.endswith('.zip'): continue
                    print ("adding %s" % os.path.join(root, file_path)) 
                    addonzip.write(os.path.join(root, file_path))
            addonzip.close()
        os.chdir(home)
        
    def _zipit( self, fpath):
        fpath = fpath or  "."
        print("fpath in zipgen:" + fpath)
        dirs = (os.listdir(fpath))
        print(str(len(dirs)) + " dirs found in zipgen")
        for addon_dir in dirs:
            directory = os.path.join(fpath, addon_dir)
            if(not os.path.isdir(directory)): continue      
            if(addon_dir.startswith('.')): continue # skip hidden dirs
            ## does nothing at the mnment
            if(addon_dir.startswith("download")): continue # skip download 
            print("processing..." + addon_dir)
            self.create_zip_file(fpath, addon_dir)

if ( __name__ == "__main__" ):
    # start
    Generator()
