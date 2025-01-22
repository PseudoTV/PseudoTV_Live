from dataclasses import asdict
from typing import List, Dict
import random
from operator import itemgetter
from globals import getJSON, setJSON, SETTINGS, PROPERTIES, LANGUAGE, xbmc, log

@dataclass
class Channel:
    id: str
    type: str
    number: int
    name: str
    logo: str
    path: List[str] = field(default_factory=list)
    group: List[str] = field(default_factory=list)
    rules: Dict = field(default_factory=dict)
    catchup: str = "vod"
    radio: bool = False
    favorite: bool = False

class Channels:
    def __init__(self):
        self.channelDATA: Dict[str, List[Channel]] = getJSON(CHANNELFLE_DEFAULT)
        self.channelTEMP: Dict = getJSON(CHANNEL_ITEM)
        self.channelDATA.update(self._load())

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s' % (self.__class__.__name__, msg), level)

    def _load(self, file=CHANNELFLEPATH) -> Dict[str, List[Channel]]:
        channelDATA = getJSON(file)
        self.log('_load, channels = %s' % (len(channelDATA.get('channels', []))))
        return channelDATA

    def _verify(self, channels: List[Channel] = []):
        for idx, citem in enumerate(self.channelDATA.get('channels', [])):
            if not citem.name or not citem.id or len(citem.path) == 0:
                self.log('_verify, in-valid citem [%s]\n%s' % (citem.id, citem))
                continue
            else:
                yield citem

    def _save(self, file=CHANNELFLEPATH) -> bool:
        self.channelDATA['uuid'] = SETTINGS.getMYUUID()
        self.channelDATA['channels'] = self.sortChannels(self.channelDATA['channels'])
        self.log('_save, channels = %s' % (len(self.channelDATA['channels'])))
        return setJSON(file, self.channelDATA)

    def getTemplate(self) -> Dict:
        return self.channelTEMP.copy()

    def getChannels(self) -> List[Channel]:
        return sorted(self.channelDATA['channels'], key=itemgetter('number'))

    def popChannels(self, type: str, channels: List[Channel] = []) -> List[Channel]:
        return [self.channelDATA['channels'].pop(self.channelDATA['channels'].index(citem)) for citem in list([c for c in channels if c.type == type])]

    def getCustom(self) -> List[Channel]:
        channels = self.getChannels()
        return list([citem for citem in channels if citem.number <= CHANNEL_LIMIT])

    def getAutotuned(self) -> List[Channel]:
        channels = self.getChannels()
        return list([citem for citem in channels if citem.number > CHANNEL_LIMIT])

    def getChannelbyID(self, id: str) -> List[Channel]:
        channels = self.getChannels()
        return list([c for c in channels if c.id == id])

    def getType(self, type: str) -> List[Channel]:
        channels = self.getChannels()
        return list([citem for citem in channels if citem.type == type])

    def sortChannels(self, channels: List[Channel]) -> List[Channel]:
        try:
            return sorted(channels, key=itemgetter('number'))
        except:
            return channels

    def setChannels(self, channels: List[Channel] = []) -> bool:
        if len(channels) == 0:
            channels = self.channelDATA['channels']
        self.channelDATA['channels'] = channels
        SETTINGS.setSetting('Select_Channels', '[B]%s[/B] Channels' % (len(channels)))
        PROPERTIES.setChannels(len(channels) > 0)
        return self._save()

    def getImports(self) -> List:
        return self.channelDATA.get('imports', [])

    def setImports(self, data: List = []) -> bool:
        self.channelDATA['imports'] = data
        return self.setChannels()

    def clearChannels(self):
        self.channelDATA['channels'] = []

    def delChannel(self, citem: Channel) -> bool:
        self.log('delChannel,[%s]' % (citem.id), xbmc.LOGINFO)
        idx, channel = self.findChannel(citem)
        if idx is not None:
            self.channelDATA['channels'].pop(idx)
        return True

    def addChannel(self, citem: Channel) -> bool:
        idx, channel = self.findChannel(citem)
        if idx is not None:
            for key in ['id', 'rules', 'number', 'favorite', 'logo']:
                if getattr(channel, key):
                    setattr(citem, key, getattr(channel, key))  # existing id found, reuse channel meta.

            if citem.favorite:
                citem.group.append(LANGUAGE(32019))
                citem.group = sorted(set(citem.group))

            self.log('addChannel, [%s] updating channel %s' % (citem.id, citem.name), xbmc.LOGINFO)
            self.channelDATA['channels'][idx] = citem
        else:
            self.log('addChannel, [%s] adding channel %s' % (citem.id, citem.name), xbmc.LOGINFO)
            self.channelDATA.setdefault('channels', []).append(citem)
        return True

    def findChannel(self, citem: Channel, channels: List[Channel] = []) -> tuple:
        if len(channels) == 0:
            channels = self.getChannels()
        for idx, eitem in enumerate(channels):
            if citem.id == eitem.id:
                return idx, eitem
        return None, {}

    def findAutotuned(self, citem: Channel, channels: List[Channel] = []) -> tuple:
        if len(channels) == 0:
            channels = self.getAutotuned()
        for idx, eitem in enumerate(channels):
            if citem.id == eitem.id or (citem.type == eitem.type and citem.name.lower() == eitem.name.lower()):
                return idx, eitem
        return None, {}