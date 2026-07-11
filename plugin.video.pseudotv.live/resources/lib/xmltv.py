#   Copyright (C) 2026 Lunatixz
#
#
# This file is part of PseudoTV.
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

""" 
MODIFIED FROM
xmltv.py - Python interface to XMLTV format, based on XMLTV.py

Copyright (C) 2001 James Oakley <jfunk@funktronics.ca>

This library is free software: you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation; either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with this software; if not, see <http://www.gnu.org/licenses/>.
"""
# https://github.com/kodi-pvr/pvr.iptvsimple#supported-m3u-and-xmltv-elements

from variables import *
from typing import Any, Dict, List, Optional, Tuple
VERSION = "1.4.5_PSEUDOTV"

# The date format used in XMLTV (the %Z will go away in 0.6)
locale           = DEFAULT_ENCODING  # 'utf-8'
date_format      = DTZFORMAT          # '%Y%m%d%H%M%S %Z'
date_format_notz = DTFORMAT           # '%Y%m%d%H%M%S'

def set_attrs(d: Dict[str, Any], elem: Any, attrs: Tuple[str, ...]):
    """
    set_attrs(d, elem, attrs)

    Add any attributes in 'attrs' found in 'elem' to 'd'
    """
    for attr in attrs:
        if attr in elem.attrib:
            d[attr] = elem.get(attr)

def set_boolean(d: Dict[str, Any], name: str, elem: Any):
    """
    set_boolean(d, name, elem)

    If element, 'name' is found in 'elem', set 'd'['name'] to a boolean
    from the 'yes' or 'no' content of the node
    """
    node = elem.find(name)
    if node is not None and node.text:
        val = node.text.lower()
        if val == 'yes':
            d[name] = True
        elif val == 'no':
            d[name] = False

def append_text(d: Dict[str, Any], name: str, elem: Any, with_lang: bool = True):
    """
    append_text(d, name, elem, with_lang=True)

    Append any text nodes with 'name' found in 'elem' to 'd'['name']. If
    'with_lang' is 'True', a tuple of ('text', 'lang') is appended
    """
    nodes = elem.findall(name)
    if not nodes:
        return
        
    if name not in d:
        d[name] = []
        
    for node in nodes:
        if with_lang:
            d[name].append((node.text or '', node.get('lang', '')))
        else:
            d[name].append(node.text or '')

def set_text(d: Dict[str, Any], name: str, elem: Any, with_lang: bool = True):
    """
    set_text(d, name, elem, with_lang=True)

    Set 'd'['name'] to the text found in 'name', if found under 'elem'. If
    'with_lang' is 'True', a tuple of ('text', 'lang') is set
    """
    node = elem.find(name)
    if node is not None:
        if with_lang:
            d[name] = (node.text or '', node.get('lang', ''))
        else:
            d[name] = node.text or ''

def append_icons(d: Dict[str, Any], elem: Any):
    """
    append_icons(d, elem)

    Append any icons found under 'elem' to 'd'
    """
    icon_nodes = elem.findall('icon')
    if not icon_nodes:
        return
        
    if 'icon' not in d:
        d['icon'] = []
        
    for iconnode in icon_nodes:
        src = iconnode.get('src')
        if src:
            icon_dict = {'src': src}
            for attr in ('width', 'height'):
                if iconnode.get(attr):
                    icon_dict[attr] = iconnode.get(attr)
            d['icon'].append(icon_dict)

def elem_to_channel(elem: Any) -> Dict[str, Any]:
    """
    elem_to_channel(Element) -> dict

    Convert channel element to dictionary
    """
    d = {'id': elem.get('id'),
         'display-name': []}

    append_text(d, 'display-name', elem)
    append_icons(d, elem)
    append_text(d, 'url', elem, with_lang=False)
    return d

def elem_to_programme(elem: Any) -> Dict[str, Any]:
    """
    elem_to_programme(Element) -> dict

    Convert programme element to dictionary
    """
    d = {'start': elem.get('start'),
         'stop': elem.get('stop'),
         'channel': elem.get('channel'),
         'catchup-id': elem.get('catchup-id', '')}

    set_attrs(d, elem, ('catchup-id', 'stop', 'pdc-start', 'vps-start', 'showview',
                        'videoplus', 'clumpidx'))

    append_text(d, 'title', elem)
    append_text(d, 'sub-title', elem)
    append_text(d, 'desc', elem)

    crednode = elem.find('credits')
    if crednode is not None:
        creddict = {}
        for credtype in ('director', 'actor', 'writer', 'adapter', 'producer',
                         'presenter', 'commentator', 'guest', 'composer',
                         'editor'):
            append_text(creddict, credtype, crednode, with_lang=False)
        d['credits'] = creddict

    set_text(d, 'date', elem, with_lang=False)
    append_text(d, 'category', elem)
    set_text(d, 'language', elem)
    set_text(d, 'orig-language', elem)

    lennode = elem.find('length')
    if lennode is not None:
        d['length'] = {'units': lennode.get('units'), 'length': lennode.text or ''}

    append_icons(d, elem)
    append_text(d, 'url', elem, with_lang=False)
    append_text(d, 'country', elem)

    for epnumnode in elem.findall('episode-num'):
        if 'episode-num' not in d:
            d['episode-num'] = []
        d['episode-num'].append((epnumnode.text or '',
                                 epnumnode.get('system', 'xmltv_ns')))

    vidnode = elem.find('video')
    if vidnode is not None:
        vidd = {}
        for name in ('present', 'colour'):
            set_boolean(vidd, name, vidnode)
        for videlem in ('aspect', 'quality'):
            venode = vidnode.find(videlem)
            if venode is not None:
                vidd[videlem] = venode.text
        d['video'] = vidd

    audnode = elem.find('audio')
    if audnode is not None:
        audd = {}
        set_boolean(audd, 'present', audnode)
        stereonode = audnode.find('stereo')
        if stereonode is not None:
            audd['stereo'] = stereonode.text
        d['audio'] = audd

    psnode = elem.find('previously-shown')
    if psnode is not None:
        psd = {}
        set_attrs(psd, psnode, ('start', 'channel', 'catchup-id'))
        d['previously-shown'] = psd

    set_text(d, 'premiere', elem)
    set_text(d, 'last-chance', elem)

    if elem.find('new') is not None:
        d['new'] = True

    for stnode in elem.findall('subtitles'):
        if 'subtitles' not in d:
            d['subtitles'] = []
        std = {}
        set_attrs(std, stnode, ('type',))
        set_text(std, 'language', stnode)
        d['subtitles'].append(std)

    for ratnode in elem.findall('rating'):
        if 'rating' not in d:
            d['rating'] = []
        ratd = {}
        set_attrs(ratd, ratnode, ('system',))
        set_text(ratd, 'value', ratnode, with_lang=False)
        append_icons(ratd, ratnode)
        d['rating'].append(ratd)

    for srnode in elem.findall('star-rating'):
        if 'star-rating' not in d:
            d['star-rating'] = []
        srd = {}
        set_attrs(srd, srnode, ('system',))
        set_text(srd, 'value', srnode, with_lang=False)
        append_icons(srd, srnode)
        d['star-rating'].append(srd)

    for revnode in elem.findall('review'):
        if 'review' not in d:
            d['review'] = []
        rd = {}
        set_attrs(rd, revnode, ('type', 'source', 'reviewer'))
        set_text(rd, 'value', revnode, with_lang=False)
        d['review'].append(rd)

    return d
         
def escape_xml_string(text: str) -> str:
    """Escapes special characters in a string for use in XML."""
    return escape(text)

def read_error(msg: str, fp: Any, e: Exception):
    try:
        line   = int(e.args[0].split(':')[0].split('line ')[1])
        column = int(e.args[0].split(':')[1].split('column ')[1])
        LOG(f"{msg}, Error at line: {line}, column: {column}")
        try:    lines = fp.readlines()
        except Exception: lines = []
        if len(lines) >= line: LOG(f"{msg}, Line {line}: {lines[line-1].strip()}")
    except Exception: LOG(f"{msg}, {e}")

def _parse_tree(fp: Any, tree: Any) -> Any:
    if tree is not None:
        return tree if hasattr(tree, 'getroot') else tree
    if fp:
        if hasattr(fp, 'read'): 
            return fromstring(fp.read(), parser=XMLParser(encoding=locale))
        else:                   
            return ETparse(fp, parser=XMLParser(encoding=locale)).getroot()
    return None

def read_data(fp: Any = None, tree: Any = None) -> Dict[str, Any]:
    """
    read_data(fp=None, tree=None) -> dict
    """
    try:
        root = _parse_tree(fp, tree)
        if root is not None:
            d = {}
            set_attrs(d, root, ('date', 'source-info-url', 'source-info-name', 
                                'source-data-url', 'generator-info-name', 'generator-info-url'))
            return d
    except Exception as e:
        read_error('read_data', fp, e)
    return {}

def read_channels(fp: Any = None, tree: Any = None) -> List[Dict[str, Any]]:
    """
    read_channels(fp=None, tree=None) -> list
    """
    try:
        root = _parse_tree(fp, tree)
        if root is not None:
            channels = []
            for elem in root.findall('channel'):
                channel = elem_to_channel(elem)
                channels.append(channel)
            return channels
    except Exception as e:
        read_error('read_channels', fp, e)
    return []
            
def read_programmes(fp: Any = None, tree: Any = None) -> List[Dict[str, Any]]:
    """
    read_programmes(fp=None, tree=None) -> list
    """
    try:
        root = _parse_tree(fp, tree)
        if root is not None:
            return [elem_to_programme(elem) for elem in root.findall('programme')]
    except Exception as e:
        read_error('read_programmes', fp, e)
    return []
            
def indent(elem: Any, level: int = 0):
    """
    Indent XML for pretty printing
    """
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for sub_elem in elem:
            indent(sub_elem, level + 1)
        if not sub_elem.tail or not sub_elem.tail.strip():
            sub_elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

class Writer:
    """
    A class for generating XMLTV data
    """
    def __init__(self, encoding: str = locale, date: Optional[str] = None,
                 source_info_url: Optional[str] = None, source_info_name: Optional[str] = None,
                 generator_info_url: Optional[str] = None, generator_info_name: Optional[str] = None):
        self.data = {'date': date,
                     'source-info-url': source_info_url,
                     'source-info-name': source_info_name,
                     'generator-info-url': generator_info_url,
                     'generator-info-name': generator_info_name}

        self.root = Element('tv')
        for attr, val in self.data.items():
            if val:
                self.root.set(attr, val)

    def setattr(self, node: Any, attr: str, value: Any):
        if value is not None:
            node.set(attr, str(value))

    def settext(self, node: Any, text: Any, with_lang: bool = True):
        if with_lang:
            if isinstance(text, tuple) or isinstance(text, list):
                node.text = '' if text[0] is None else str(text[0])
                if len(text) > 1 and text[1]:
                    node.set('lang', str(text[1]))
            else:
                node.text = '' if text is None else str(text)
        else:
            node.text = '' if text is None else str(text)

    def seticons(self, node: Any, icons: List[Dict[str, Any]]):
        for icon in icons:
            if 'src' not in icon:
                raise ValueError("'icon' element requires 'src' attribute")
            i = SubElement(node, 'icon')
            for attr in ('src', 'width', 'height'):
                if attr in icon:
                    self.setattr(i, attr, icon[attr])

    def set_zero_ormore(self, programme: Dict[str, Any], element: str, p: Any):
        if element in programme and programme[element]:
            for item in programme[element]:
                e = SubElement(p, element)
                self.settext(e, item)

    def set_zero_orone(self, programme: Dict[str, Any], element: str, p: Any):
        if element in programme and programme[element] is not None:
            e = SubElement(p, element)
            self.settext(e, programme[element])

    def addProgramme(self, programme: Dict[str, Any]) -> Any:
        """
        Add a single XMLTV 'programme'
        """
        p = SubElement(self.root, 'programme')

        # programme attributes
        for attr in ('start', 'channel'):
            if attr in programme:
                self.setattr(p, attr, programme[attr])
            else:
                raise ValueError("'programme' must contain '%s' attribute" % attr)

        for attr in ('catchup-id', 'stop', 'pdc-start', 'vps-start', 'showview', 'videoplus', 'clumpidx'):
            if attr in programme:
                self.setattr(p, attr, programme[attr])

        if 'title' in programme:
            for title in programme['title']:
                t = SubElement(p, 'title')
                self.settext(t, title)

        # Sub-title and description
        for element in ('sub-title', 'desc'):
            self.set_zero_ormore(programme, element, p)

        # Credits
        if 'credits' in programme and programme['credits']:
            c = SubElement(p, 'credits')
            for credtype in ('director', 'actor', 'writer', 'adapter',
                             'producer', 'presenter', 'commentator', 'guest', 'composer', 'editor'):
                if credtype in programme['credits']:
                    for name in programme['credits'][credtype]:
                        cred = SubElement(c, credtype)
                        self.settext(cred, name, with_lang=False)

        # Date
        if 'date' in programme:
            d = SubElement(p, 'date')
            self.settext(d, programme['date'], with_lang=False)

        # Category
        self.set_zero_ormore(programme, 'category', p)

        # Language and original language
        for element in ('language', 'orig-language'):
            self.set_zero_orone(programme, element, p)

        # Length
        if 'length' in programme and programme['length']:
            l = SubElement(p, 'length')
            if 'units' in programme['length']:
                self.setattr(l, 'units', programme['length']['units'])
            if 'length' in programme['length']:
                self.settext(l, programme['length']['length'], with_lang=False)

        # Icon
        if 'icon' in programme:
            self.seticons(p, programme['icon'])

        # URL
        if 'url' in programme:
            for url in programme['url']:
                u = SubElement(p, 'url')
                self.settext(u, url, with_lang=False)

        # Country
        self.set_zero_ormore(programme, 'country', p)

        # Episode-num
        if 'episode-num' in programme:
            for epnum in programme['episode-num']:
                e = SubElement(p, 'episode-num')
                if len(epnum) > 1:
                    self.setattr(e, 'system', epnum[1])
                self.settext(e, epnum[0], with_lang=False)

        # Video details
        if 'video' in programme and programme['video']:
            e = SubElement(p, 'video')
            for videlem in ('aspect', 'quality'):
                if videlem in programme['video']:
                    v = SubElement(e, videlem)
                    self.settext(v, programme['video'][videlem], with_lang=False)
            for attr in ('present', 'colour'):
                if attr in programme['video']:
                    a = SubElement(e, attr)
                    self.settext(a, 'yes' if programme['video'][attr] else 'no', with_lang=False)

        # Audio details
        if 'audio' in programme and programme['audio']:
            a = SubElement(p, 'audio')
            if 'stereo' in programme['audio']:
                s = SubElement(a, 'stereo')
                self.settext(s, programme['audio']['stereo'], with_lang=False)
            if 'present' in programme['audio']:
                # CRITICAL BUG FIX: Renamed 'p' to 'pres_elem' to prevent over-writing parent container reference
                pres_elem = SubElement(a, 'present')
                self.settext(pres_elem, 'yes' if programme['audio']['present'] else 'no', with_lang=False)

        # Previously shown
        if 'previously-shown' in programme and programme['previously-shown']:
            ps = SubElement(p, 'previously-shown')
            for attr in ('start', 'channel', 'catchup-id'):
                if attr in programme['previously-shown']:
                    self.setattr(ps, attr, programme['previously-shown'][attr])

        # Premiere / last chance
        for element in ('premiere', 'last-chance'):
            self.set_zero_orone(programme, element, p)

        # New
        if 'new' in programme and programme['new']:
            SubElement(p, 'new')

        # Subtitles
        if 'subtitles' in programme:
            for subtitles in programme['subtitles']:
                s = SubElement(p, 'subtitles')
                if 'type' in subtitles:
                    self.setattr(s, 'type', subtitles['type'])
                if 'language' in subtitles:
                    l = SubElement(s, 'language')
                    self.settext(l, subtitles['language'])

        # Rating & Star Rating & Review blocks
        for block_name in ('rating', 'star-rating'):
            if block_name in programme:
                for rate_data in programme[block_name]:
                    block_elem = SubElement(p, block_name)
                    if 'system' in rate_data:
                        self.setattr(block_elem, 'system', rate_data['system'])
                    if 'value' in rate_data:
                        v = SubElement(block_elem, 'value')
                        self.settext(v, rate_data['value'], with_lang=False)
                    if 'icon' in rate_data:
                        self.seticons(block_elem, rate_data['icon'])

        if 'review' in programme:
            for review in programme['review']:
                r = SubElement(p, 'review')
                for attr in ('type', 'source', 'reviewer'):
                    if attr in review:
                        self.setattr(r, attr, review[attr])
                if 'value' in review:
                    v = SubElement(r, 'value')
                    self.settext(v, review['value'], with_lang=False)

        return p

    def addChannel(self, channel: Dict[str, Any]) -> Any:
        """
        add a single XMLTV 'channel'
        """
        c = SubElement(self.root, 'channel')
        self.setattr(c, 'id', channel['id'])
        
        # Display Name
        if 'display-name' in channel:
            for display_name in channel['display-name']:
                dn = SubElement(c, 'display-name')
                self.settext(dn, display_name)

        # Icon
        if 'icon' in channel:
            self.seticons(c, channel['icon'])

        # URL
        if 'url' in channel:
            for url in channel['url']:
                u = SubElement(c, 'url')
                self.settext(u, url, with_lang=False)
        return c
        
    def write(self, file: Any, pretty_print: bool = False):
        """
        write(file, pretty_print=False)
        """
        if pretty_print:
            indent(self.root)
        et = ElementTree(self.root)
        et.write(file, encoding=locale, xml_declaration=True)