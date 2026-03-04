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
    def __init__(self, cache=SETTINGS.cacheDB):
        self.cache = cache
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        return log('%s: %s'%(self.__class__.__name__,msg),level)


    def _request(self, url, params={}, payload={}, header=HEADER, timeout=15):
        if SETTINGS.getSettingBool('Enable_Generative_Artwork'):
            header.update({"Authorization": f"Bearer {SETTINGS.getSetting('Open_Router_APIKEY')}"})
            return requestURL(url, params, payload, header, timeout, cache={'cache':self.cache,'life':datetime.timedelta(days=MAX_GUIDEDAYS)})


    def _getModels(self):
        response = self._request("https://openrouter.ai/api/v1/models")
        print('_getModels',response)
        image_models = []
        text_models  = []
        if "data" in response:
            for model in response['data']:
                capabilities = model.get("architecture",{}).get("output_modalities", [])
                if   "image" in capabilities: image_models.append(model)
                elif "text"  in capabilities: text_models.append(model)
        self.log('_getModels, image_models = %s, text_models = %s'%(len(image_models),len(text_models)))
        return image_models, text_models
        
            
    def _getImage(self, chname, count=1, model="google/gemini-2.5-flash-image-preview", background_color=(0, 255, 0)):
        self.log('_getImage, chname = %s, count = %s, model = %s'%(chname, count, model))
        payload = { "model"          : model,
                    "messages"       : [{"role"        : "user",
                                         "content"     : f"Create a logo with a background rgb({background_color}), {SETTINGS.getSetting('Gnerative_Artwork_Prompt').format(channel_name=chname)}",
                                         "type"        : "text"}],
                    "modalities"     : ["image"],
                    "image_config"   : {"aspect_ratio": "16:9"},
                    "n"              : count,
                    "size"           : "512x512",
                    "response_format": {"type": "b64_json"}}
    
        response = self._request("https://openrouter.ai/api/v1/chat/completions",payload=payload)
        if "choices" in response:
            for idx, image in enumerate(response["choices"][0]["message"]["images"]):
                match = re.match(r"data:image/(?P<ext>.*?);base64,(?P<data>.*)", image["image_url"]["url"])
                if match:
                    try:
                        file_name = '%s.%s'%(chname,match.group('ext'))# '%s_%s.%s'%(chname,idx,match.group('ext'))
                        file_path = os.path.join(TEMP_IMAGE_LOC,file_name)
                        with FileLock(file_path):
                            with FileAccess.stream(file_path, "wb") as f:
                                f.write(base64.b64decode(match.group('data')))
                        if SETTINGS.hasAddon('script.module.pil', install=True): __alpha(file_name)
                    except base64.binascii.Error as e: print(f"Error decoding base64 data: {e}")
                else: print("Failed to parse the base64 data URI format.")
        
        
    def _alphaImage(self, file_name, background_color=(0, 255, 0)):
        # if SETTINGS.hasAddon('script.module.pil') and FileAccess.exists(os.path.join(TEMP_IMAGE_LOC,file_name)):
            # def __nearest(color1, color2, tolerance=50):
                # r1, g1, b1 = color1[:3]
                # r2, g2, b2 = color2[:3]
                # return sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2) <= tolerance

            # try:
                # from PIL import Image
                # fle = FileAccess.open(os.path.join(TEMP_IMAGE_LOC,file_name), "rb")
                # img = Image.open(BytesIO(fle.readBytes())).convert("RGBA")# Ensure image has an alpha channel
                # fle.close()

                # data   = list(img.getdata())
                # pixels = []
                # for pixel in data:
                    # if __nearest(pixel[:3], background_color): pixels.append((0, 255, 0, 0))
                    # else:                                      pixels.append(pixel)

                # new_img = Image.new('RGBA', img.size)
                # new_img.putdata(pixels)
                # new_img.save(os.path.join(FileAccess.translatePath(LOGO_LOC),file_name), "PNG")  # Save as PNG to preserve transparency
                # self.log(f"_alphaImage, Image saved with transparency at: {os.path.join(LOGO_LOC,file_name)}")
            # except FileNotFoundError: self.log(f"_alphaImage, Error: Image not found at {os.path.join(TEMP_IMAGE_LOC,file_name)}")
            # except Exception as e: self.log(f"_alphaImage, An error occurred: {e}")

        IMAGE_PATH = "/path/to/your/image.jpg" # Replace with the path to your image file
        OUTPUT_PATH = "image-no-bg.png" # Desired output file name

        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': open(os.path.join(TEMP_IMAGE_LOC,file_name), 'rb')}, data={'size': 'auto'}, headers={'X-Api-Key': SETTINGS.getSetting('Remove_BG_APIKEY')})

        if response.status_code == requests.codes.ok:
            with open(os.path.join(LOGO_LOC,file_name), 'wb') as out:
                out.write(response.content)
            print(f"Background removed successfully! Image saved to {os.path.join(LOGO_LOC,file_name)}")
        else:
            print("Error:", response.status_code, response.text)
                
    
