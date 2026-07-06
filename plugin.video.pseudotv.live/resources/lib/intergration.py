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

from variables   import *
from fileaccess  import FileAccess, FileLock
from cache       import cacheit

BASE_HEADER = {"Authorization": "",
               "Content-Type" : "application/json",
               "X-Title"      : f"{ADDON_NAME}",
               "X-Reference"  : f"{ADDON_URL}",}
           
class OpenRouter(object):
    def __init__(self, service=None):
        if service is None:
            from kodi import _get_Service
            service = _get_Service()
        self.service = service
        self.pool    = service.pool
        self.cache   = service.cache
        

    def log(self, msg, level=xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def _request(self, url, params={}, payload={}, header=HEADER, timeout=15):
        if Globals.settings.getSettingBool('Allow_Artificial_Intelligence'):
            req_header = BASE_HEADER.copy()
            if header: req_header.update(header)
            req_header.update({"Authorization": f"Bearer {Globals.settings.getSetting('Open_Router_APIKEY')}"})
            if hasattr(self.jsonRPC, 'requestURL'):
                return self.jsonRPC.requestURL(url, params, payload, req_header, timeout)
        return None


    @cacheit(expiration=datetime.timedelta(minutes=15))
    def _getModels(self):
        response = self._request("https://openrouter.ai/api/v1/models")
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
            image_models, _ = self._getModels()
            if not image_models:
                self.log("_getImageModels: No image models available.")
                return
            names = [item.get('name', 'Unknown') for item in image_models]
            preselect_id = Globals._findItemsInLST(image_models, Globals.settings.getSetting('Generative_Image_Model'), 'id')
            select = Globals.dialog.selectDialog(names, header=ADDON_NAME, preselect=preselect_id, useDetails=False, multi=False)
            if not select is None: Globals.settings.setSetting('Generative_Image_Model', image_models[select].get('id'))
        except Exception as e: 
            self.log("_getImageModels, failed! %s" % (e), xbmc.LOGERROR)
            
            
    def _getContextModels(self):
        try:
            _, text_models = self._getModels()
            if not text_models:
                self.log("_getContextModels: No context models available.")
                return
            names = [item.get('name', 'Unknown') for item in text_models]
            preselect_id = Globals._findItemsInLST(text_models, Globals.settings.getSetting('Generative_Contextual_Model'), 'id')
            select = Globals.dialog.selectDialog(names, header=ADDON_NAME, preselect=preselect_id, useDetails=False, multi=False)
            if not select is None: Globals.settings.setSetting('Generative_Contextual_Model', text_models[select].get('id'))
        except Exception as e: self.log("_getContextModels, failed! %s" % (e), xbmc.LOGERROR)
        
            
    def getImage(self, citem, count=1, model="google/gemini-2.5-flash-image-preview", background_color=(0, 255, 0)):
        chname = citem.get('name', 'unknown_channel')
        self.log('getImage, chname = %s, count = %s, model = %s' % (chname, count, model))
        filtered_groups = [g for g in citem.get('group', []) if g != ADDON_NAME]
        group_str = '%s, %s' % (chname, ', '.join(filtered_groups)) if filtered_groups else chname

        payload = { 
                    "model": model,
                    "messages": [
                        { 
                            "role": "user",
                            "content": Globals.settings.getSetting('Generative_Image_Prompt').format(name=chname, group=group_str)
                        }
                    ],
                    "modalities": ["image"],
                    "response_format": {"type": "b64_json"},
                    "n": count,
                    "provider": {
                        "allow_fallbacks": True,
                        "require_parameters": True,
                        "data_collection": "deny"
                    }
                }

        response = self._request("https://openrouter.ai/api/v1/chat/completions", payload=payload)
        if not response or "choices" not in response:
            self.log("getImage: Invalid or empty response received from OpenRouter API.", xbmc.LOGERROR)
            return False
        try:
            message_content = response["choices"][0].get("message", {})
            images = message_content.get("images", [])
            if not images:
                self.log("getImage: No images found in the response message payload.", xbmc.LOGWARNING)
                return False
                
            logos = []
            for idx, image_node in enumerate(images):
                img_url = image_node.get("image_url", {}).get("url", "")
                if not img_url: continue
                # Regex matches standard Data URI format (e.g., data:image/png;base64,iVBORw0KGg...)
                match = re.match(r"data:image/(?P<ext>.*?);base64,(?P<data>.*)", img_url)
                if match:
                    ext = match.group('ext')
                    b64_data = match.group('data')
                    try:
                        file_name = f"{chname}.{ext}" if count == 1 else f"{chname}_{idx}.{ext}"
                        file_path = os.path.join(TEMP_LOC, file_name)
                        with FileAccess.stream(file_path, "w") as f:
                            f.write(base64.b64decode(b64_data.encode('utf-8') + b"=="))
                    except base64.binascii.Error as b64_err:
                        self.log(f"getImage: Base64 binary decoding failed for {file_name}: {b64_err}", xbmc.LOGERROR)
                    except Exception as file_err:
                        self.log(f"getImage: IO write error tracking {file_name}: {file_err}", xbmc.LOGERROR)
                    finally: logos.append(self._alphaImage(file_name, background_color=background_color))
                else: 
                    self.log("getImage: Target image URI failed to match base64 extraction format regex.", xbmc.LOGWARNING)
            return logos if len(logos) > 0 else file_path
        except Exception as system_err:
            self.log(f"getImage: Critical engine breakdown handling response: {system_err}", xbmc.LOGERROR)
            return False
        
        
    def _alphaImage(self, file_name, background_color=(0, 255, 0)):
        input_file_path  = os.path.join(TEMP_LOC, file_name)
        output_file_path = os.path.join(LOGO_LOC, file_name)
        if not FileAccess.exists(input_file_path):
            self.log(f"_alphaImage, Error: Source file missing at {input_file_path}", xbmc.LOGERROR)
            return file_name
            
        if Globals.settings.hasAddon('script.module.pil'):
            try:
                def __nearest(color1, color2, tolerance=50):
                    r1, g1, b1 = color1[:3]
                    r2, g2, b2 = color2[:3]
                    return math.sqrt((r1 - r2)**2 + (g1 - g2)**2 + (b1 - b2)**2) <= tolerance

                fle = FileAccess.open(input_file_path, "rb")
                img_data = fle.readBytes()
                fle.close()
                img = Image.open(BytesIO(img_data)).convert("RGBA")
                data = list(img.getdata())
                pixels = []
                for pixel in data:
                    # If pixel color falls within target tolerance, swap it with a transparent pixel
                    if __nearest(pixel[:3], background_color): 
                        pixels.append((0, 255, 0, 0))  # Fully transparent alpha
                    else:                                      
                        pixels.append(pixel)

                new_img = Image.new('RGBA', img.size)
                new_img.putdata(pixels)
                new_img.save(FileAccess.translatePath(output_file_path), "PNG")
                self.log(f"_alphaImage: Image saved via PIL with transparency at: {output_file_path}")
                if FileAccess.exists(output_file_path): FileAccess.delete(input_file_path)
                return output_file_path
            except Exception as pil_err:
                self.log(f"_alphaImage: Local PIL processing failed. Falling back to API. Error: {pil_err}", xbmc.LOGWARNING)
        return file_name
        
        # self.log("_alphaImage: Running fallback remote background extraction via remove.bg API.")
        # try:
            # with open(input_file_path, 'rb') as img_file:
                # response = requests.post(
                    # 'https://api.remove.bg/v1.0/removebg',
                    # files={'image_file': img_file},
                    # data={'size': 'auto'},
                    # headers={'X-Api-Key': Globals.settings.getSetting('Remove_BG_APIKEY')},
                    # timeout=30
                # )
            # if response.status_code == requests.codes.ok:
                # with open(output_file_path, 'wb') as out:
                    # out.write(response.content)
                # self.log(f"_alphaImage: Background removed successfully via API! Saved to {output_file_path}")
            # else:
                # self.log(f"_alphaImage: Remove.bg API error: {response.status_code} - {response.text}", xbmc.LOGERROR)
        # except Exception as api_err:
            # self.log(f"_alphaImage: Critical failure during API background extraction: {api_err}", xbmc.LOGERROR)
            
            
    @staticmethod
    def _run(sysARG):
        with Globals.builtin.busy_dialog():
            ctl = (5,1)
            try:              param = sysARG[1]
            except Exception: param = None
            LOG('OpenRouter: param = %s'%(param))
            if param == 'getImageModels':   OpenRouter()._getImageModels()
            if param == 'getContextModels': OpenRouter()._getContextModels()
            return Globals._openSettings(ctl)

if __name__ == '__main__': OpenRouter()._run(sys.argv)