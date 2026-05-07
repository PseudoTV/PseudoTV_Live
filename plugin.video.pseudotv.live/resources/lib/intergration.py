  # Copyright (C) 2024 Lunatixz


# This file is part of PseudoTV Live.

# PseudoTV Live is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# PseudoTV Live is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with PseudoTV Live.  If not, see <http://www.gnu.org/licenses/>.
# -*- coding: utf-8 -*-

from globals     import *
from fileaccess  import FileAccess, FileLock

HEADER = {"Authorization": "",
          "Content-Type" : "application/json",
          "X-Title"      : f"{ADDON_NAME}",
          "X-Reference"  : f"{ADDON_URL}",}
           
class OpenRouter(object):
    def __init__(self, cache=None, jsonRPC=None):
        self.jsonRPC = jsonRPC
        self.cache   = cache
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _request(self, url, params={}, payload={}, header=HEADER, timeout=15):
        if SETTINGS.getSettingBool('Allow_Artificial_Intelligence'):
            header.update({"Authorization": f"Bearer {SETTINGS.getSetting('Open_Router_APIKEY')}"})
            if hasattr(self.jsonRPC,'requestURL'):
                return self.jsonRPC.requestURL(url, params, payload, header, timeout)


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def _getModels(self):
        response = self._request("https://openrouter.ai/api/v1/models")
        print(response)
        image_models = []
        text_models  = []
        if "data" in response:
            for model in response['data']:
                capabilities = model.get("architecture",{}).get("output_modalities", [])
                if   "image" in capabilities: image_models.append(model)
                elif "text"  in capabilities: text_models.append(model)
        self.log('_getModels, image_models = %s, text_models = %s'%(len(image_models),len(text_models)))
        return sorted(image_models,key=itemgetter('name')), sorted(text_models,key=itemgetter('name'))
        
        
    def _getImageModels(self):
        try:
            image_models, text_models = self._getModels()
            print(image_models)
            select = DIALOG.selectDialog([item.get('name') for item in image_models], header=ADDON_NAME, preselect=Globals._findItemsInLST(image_models,SETTINGS.getSetting('Generative_Image_Model'),'id'), useDetails=False, multi=False)
            print(select)
            SETTINGS.setSetting('Generative_Image_Model',image_models[select].get('id'))
        except Exception as e: self.log("_getImageModels, failed! %s"%(e), xbmc.LOGERROR)
            
            
    def _getContextModels(self):
        try:
            image_models, text_models = self._getModels()
            print(text_models)
            select = DIALOG.selectDialog([item.get('name') for item in text_models], header=ADDON_NAME, preselect=Globals._findItemsInLST(text_models,SETTINGS.getSetting('Generative_Contextual_Model'),'id'), useDetails=False, multi=False)
            print(select)
            SETTINGS.setSetting('Generative_Contextual_Model',text_models[select].get('id'))
        except Exception as e: self.log("_getContextModels, failed! %s"%(e), xbmc.LOGERROR)
        
            
    def getImage(self, citem, count=1, model="google/gemini-2.5-flash-image-preview", background_color=(0, 255, 0)):
        self.log('getImage, chname = %s, count = %s, model = %s'%(citem.get('name'), count, model))
        # payload = { "model"        : model,
                    # "messages"     : [ { "role": "user",
                                          # "content": SETTINGS.getSetting('Generative_Image_Prompt').format(name=citem.get('name'),group='%s %s'%(citem.get('name'),', '.join(citem.get('group',[]).remove(ADDON_NAME))))}],
                  # "modalities"     : ["image"],
                  # "response_format": {"type": "b64_json"},
                   # "n"             : count,
                  # "provider"       : { "allow_fallbacks": true,
                                       # "require_parameters": true,
                                       # "data_collection": "deny"}}

        # response = self._request("https://openrouter.ai/api/v1/chat/completions",payload=payload)
        # if "choices" in response:
            # for idx, image in enumerate(response["choices"][0]["message"]["images"]):
                # match = re.match(r"data:image/(?P<ext>.*?);base64,(?P<data>.*)", image["image_url"]["url"])
                # if match:
                    # try:
                        # file_name = '%s.%s'%(chname,match.group('ext'))# '%s_%s.%s'%(chname,idx,match.group('ext'))
                        # file_path = os.path.join(TEMP_LOC,file_name)
                        # with FileLock(file_path):
                            # with FileAccess.stream(file_path, "wb") as f:
                                # f.write(base64.b64decode(match.group('data') + b"=="))
                        # if SETTINGS.hasAddon('script.module.pil'): __alpha(file_name)
                    # except base64.binascii.Error as e: print(f"Error decoding base64 data: {e}")
                # else: print("Failed to parse the base64 data URI format.")
        
        
    def _alphaImage(self, file_name, background_color=(0, 255, 0)):
        # if SETTINGS.hasAddon('script.module.pil') and FileAccess.exists(os.path.join(TEMP_LOC,file_name)):
            # def __nearest(color1, color2, tolerance=50):
                # r1, g1, b1 = color1[:3]
                # r2, g2, b2 = color2[:3]
                # return sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2) <= tolerance

            # try:
                # from PIL import Image
                # fle = FileAccess.open(os.path.join(TEMP_LOC,file_name), "rb")
                # img = Image.open(BytesIO(fle.readBytes())).convert("RGBA")# Ensure image has an alpha channel
                # fle.close()

                # data   = list(img.getdata())
                # pixels = []
                # for pixel in data:
                    # if __nearest(pixel[:3], background_color): pixels.append((0, 255, 0, 0))
                    # else:                                      pixels.append(pixel)

                # new_img = Image.new('RGBA', img.size)e
                # new_img.putdata(pixels)
                # new_img.save(os.path.join(FileAccess.translatePath(LOGO_LOC),file_name), "PNG")  # Save as PNG to preserve transparency
                # self.log(f"_alphaImage, Image saved with transparency at: {os.path.join(LOGO_LOC,file_name)}")
            # except FileNotFoundError: self.log(f"_alphaImage, Error: Image not found at {os.path.join(TEMP_LOC,file_name)}")
            # except Exception as e: self.log(f"_alphaImage, An error occurred: {e}")

        IMAGE_PATH = "/path/to/your/image.jpg" # Replace with the path to your image file
        OUTPUT_PATH = "image-no-bg.png" # Desired output file name

        response = requests.post('https://api.remove.bg/v1.0/removebg',
             files={'image_file': open(os.path.join(TEMP_LOC,file_name), 'rb')}, data={'size': 'auto'}, headers={'X-Api-Key': SETTINGS.getSetting('Remove_BG_APIKEY')})

        if response.status_code == requests.codes.ok:
            with open(os.path.join(LOGO_LOC,file_name), 'wb') as out:
                out.write(response.content)
            print(f"Background removed successfully! Image saved to {os.path.join(LOGO_LOC,file_name)}")
        else:
            print("Error:", response.status_code, response.text)
            
            
    @staticmethod
    def _run(sysARG):
        with BUILTIN.busy_dialog():
            ctl = (5,1)
            try:              param = sysARG[1]
            except Exception: param = None
            log('OpenRouter: param = %s'%(param))
            if param == 'getImageModels':   OpenRouter(cache=SETTINGS.cache)._getImageModels()
            if param == 'getContextModels': OpenRouter(cache=SETTINGS.cache)._getContextModels()
            return Globals._openSettings(ctl)

if __name__ == '__main__': OpenRouter()._run(sys.argv)