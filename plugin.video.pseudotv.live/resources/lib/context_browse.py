#   Copyright (C) 2023 Lunatixz
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
from globals   import *
from builder   import Builder

class Browse:
    def __init__(self, sysARG, writer):
        log('Browse: __init__, sysARG = %s'%(sysARG))
        with busy_dialog():
            target  = '%ss'%(writer.get('media','video'))
            orgpath = writer.get('originalpath','')
            citem   = Builder().getProvisional(writer.get('citem',{}))

            if '?xsp=' in orgpath:
                path, params = orgpath.split('?xsp=')
                path = '%s?xsp=%s'%(path,quoteString(unquoteString(params)))
            elif citem.get('provisional',None):
                #todo build xsp with path rule.
                provisional = citem.get('provisional',{})
                path        = provisional.get('path',[])
            else: 
                path = citem.get('path','')
            if isinstance(path,list): path = path[0]
        log('Browse: target = %s, path = %s'%(target,path))
        BUILTIN.executebuiltin('ActivateWindow(%s,%s,return)'%(target,path))

if __name__ == '__main__': 
    Browse(sys.argv,writer=decodeWriter(BUILTIN.getInfoLabel('Writer')))

