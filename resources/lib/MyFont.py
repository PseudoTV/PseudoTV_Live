#   Copyright (C) 2016 Steveb1968, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import os
import xml.etree.ElementTree as ET
import xbmc, xbmcaddon, xbmcvfs

from utils import *
from Globals import *
from FileAccess import FileAccess

SkinPath = xbmc.translatePath('special://skin')

class PCParser(ET.XMLTreeBuilder):
    def __init__(self):
        ET.XMLTreeBuilder.__init__(self)
        self._parser.CommentHandler = self.handle_comment
        
    def handle_comment(self, data):
        self._target.start(ET.Comment, {})
        self._target.data(data)
        self._target.end(ET.Comment)

def getFonts():
    FontLst = []
    try:
        for item in os.listdir(os.path.join(PTVL_SELECT_SKIN_LOC,'fonts')):
            if item.endswith('ttf'):
                log("MyFont: getFonts = " + item) 
                FontLst.append(item)
        return FontLst
    except:
        pass
    
def getFontsXML():
    fontxml_paths = []
    ListDir = os.listdir(SkinPath)
    try:
        for item in ListDir:
            item = os.path.join(SkinPath, item)
            if os.path.isdir(item):
                font_xml = os.path.join(item, "Font.xml")
                if os.path.exists(font_xml):
                    fontxml_paths.append(font_xml)
    except:
        pass
    log("MyFont: getFontsXML = " + str(fontxml_paths))
    return fontxml_paths
    
def isFontInstalled(fontxml_path, fntname, fontfile):
    log("MyFont: isFontInstalled, fntname = " + fntname + ", fontfile = " + fontfile)
    fle = file(fontxml_path, "r").read()
    fleLst = file(fontxml_path, "r").readlines()
    name = "<name>%s</name>" % fntname
    if not name in fle:
        nameCheck = False
    else:
        nameCheck = True
    filename = "<filename>%s</filename>" % fontfile
    if nameCheck == True:
        #todo add multi font support, find fntname and only change if needed.
        # for line in fle:
            # if line == fntname and filename != fontfile replace that line
        if not filename in fle:
            nameCheck = False
            for i in range(len(fleLst)):
                line = fleLst[i].replace('\t','').replace('\r','').replace('\n','')
                if line == name:
                    initFont = fleLst[i+1].replace('\t','').replace('\r','').replace('\n','')
                    initName = initFont.replace('/','').replace('<filename>','')
                    if initName != 'Arial.ttf':
                        log("MyFont: isFontInstalled, replace configuration: " + initFont + ", with = " + filename)
                        replaceAll(fontxml_path,initFont,filename)
                        nameCheck = True
        else:
            nameCheck = True
    log("MyFont: isFontInstalled, found configuration = " + str(nameCheck))
    return nameCheck

def getSkinRes():
    log("MyFont: getSkinRes") 
    SkinRes = '720p'
    SkinResPath = os.path.join(SkinPath, SkinRes)
    if not os.path.exists(SkinResPath):
        SkinRes = '1080i'
    return SkinRes

def addFont(fntname, filename, size, style=""):
    log("MyFont: addFont, filename = " + filename + ", size = " + size)
    FontName = filename
    FontPath = os.path.join(PTVL_SELECT_SKIN_LOC, 'fonts', FontName)
    log("MyFont: addFont, FontName = " + FontName)
    log("MyFont: addFont, FontPath = " + FontPath)
    reload_skin = False
    fontxml_paths = getFontsXML()
    if fontxml_paths:
        for fontxml_path in fontxml_paths:
            if not isFontInstalled(fontxml_path, fntname, FontName):
                parser = PCParser()
                tree = ET.parse(fontxml_path, parser=parser)
                root = tree.getroot()
                for sets in root.getchildren():
                    sets.findall("font")[-1].tail = "\n\t\t"                        
                    new = ET.SubElement(sets, "font")
                    new.text, new.tail = "\n\t\t\t", "\n\t"
                    subnew1 = ET.SubElement(new, "name")
                    subnew1.text = fntname
                    subnew1.tail = "\n\t\t\t"
                    subnew2 = ET.SubElement(new, "filename")
                    subnew2.text = (filename, "Arial.ttf")[sets.attrib.get("id") == "Arial"]
                    subnew2.tail = "\n\t\t\t"
                    subnew3 = ET.SubElement(new, "size")
                    subnew3.text = size
                    subnew3.tail = "\n\t\t\t"
                    last_elem = subnew3
                    if style in ["normal", "bold", "italics", "bolditalics"]:
                        subnew4 = ET.SubElement(new, "style")
                        subnew4.text = style
                        subnew4.tail = "\n\t\t\t"
                        last_elem = subnew4
                    reload_skin = True
                    last_elem.tail = "\n\t\t"
                tree.write(fontxml_path)
                reload_skin = True
                
        if os.path.exists(SkinPath) == False:
            reload_skin = True
            
        dest = os.path.join(SkinPath, 'fonts', FontName)
        if os.path.exists(dest) == False:
            log("MyFont: copyFont, FontPath = " + FontPath + ", SkinPath = " + SkinPath)
            FileAccess.copy(FontPath, dest)
    
    if reload_skin:
        xbmc.executebuiltin("XBMC.ReloadSkin()")
        return True
    return False