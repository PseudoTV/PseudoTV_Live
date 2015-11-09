# -*- coding: utf8 -*-

# Copyright (C) 2015 - Philipp Temminghoff <phil65@kodi.tv>
# This program is Free Software see LICENSE file for details

import xbmcgui
from utils import *
from Globals import *


# TODO: extend and use this for ContextMenu to get proper closing behaviour
class SelectDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self)
        self.items = kwargs.get('listing')
        show_busy_dialog()
        # self.listitems = getProperty('listitems')
        self.listitems = getProperty('listitems')
        self.listitem = None
        self.index = -1

    def onInit(self):
        self.list = self.getControl(6)
        self.getControl(3).setVisible(False)
        self.getControl(5).setVisible(False)
        self.getControl(1).setLabel('Choose option')
        self.list.addItems(self.listitems)
        self.setFocus(self.list)

    def onAction(self, action):
        if action in self.ACTION_PREVIOUS_MENU:
            self.close()

    def onClick(self, control_id):
        if control_id == 6 or control_id == 3:
            self.index = int(self.list.getSelectedItem())
            self.listitem = self.items[self.index]
            self.close()

    def onFocus(self, control_id):
        pass
