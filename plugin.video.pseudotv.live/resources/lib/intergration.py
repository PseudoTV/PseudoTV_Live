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

from typing import Any, Optional, Union
from variables   import *
from _services   import _Service
from fileaccess  import FileAccess, FileLock
from cache       import cacheit

BASE_HEADER = {"Authorization": "",
               "Content-Type" : "application/json",
               "X-Title"      : f"{ADDON_NAME}",
               "X-Reference"  : f"{ADDON_URL}",}

# =============================================================================
# Kodi artwork types (kodi.wiki/view/Artwork_types) -> rendering spec injected
# into the hardcoded system prompt when the user's style names one. Transparent
# types keep the green chroma-key contract (our keying needs a flat green bg);
# opaque types skip it because their background IS the image.
# =============================================================================
_ART_SPECS = {
    'clearlogo':    {'res': '800w x 310h',  'ratio': '80:31', 'transparent': True,
                     'desc': 'a distinctive, uncluttered emblem using a bold, iconic typeface, centered filling roughly 70-80% of the width with clear space around the edges'},
    'clearart':     {'res': '1000w x 562h', 'ratio': '16:9',  'transparent': True,
                     'desc': 'recognizable characters or props with a logo or name, uncluttered'},
    'characterart': {'res': '512w x 512h',  'ratio': '1:1',   'transparent': True,
                     'desc': 'an iconic character or object, simple and bold'},
    'discart':      {'res': '1000w x 1000h','ratio': '1:1',   'transparent': True,
                     'desc': 'a round disc placed centered on a plain background'},
    'banner':       {'res': '1000w x 185h', 'ratio': '200:37','transparent': False,
                     'desc': 'a wide, short image with recognizable imagery and a clearly visible logo or name'},
    'poster':       {'res': '1000w x 1500h','ratio': '2:3',   'transparent': False,
                     'desc': 'a portrait poster with a clearly visible logo or name of the content'},
    'keyart':       {'res': '1000w x 1500h','ratio': '2:3',   'transparent': False,
                     'desc': 'a poster WITHOUT text or logo, just striking imagery'},
    'landscape':    {'res': '1000w x 562h', 'ratio': '16:9',  'transparent': False,
                     'desc': 'a wide image with the logo or name overlaid on the artwork'},
    'fanart':       {'res': '1920w x 1080h','ratio': '16:9',  'transparent': False,
                     'desc': 'a full-screen background image, NO text or logo'},
    'thumb':        {'res': '960w x 540h',  'ratio': '16:9',  'transparent': False,
                     'desc': 'a wide thumbnail still, no logo overlay'},
}

_ART_KEYWORDS = sorted(_ART_SPECS, key=len, reverse=True)  # longest first so 'clearlogo' beats 'logo'


def _matchArtType(style: str) -> Optional[str]:
    """Return the Kodi artwork type keyword the style asks for, or None.

    Longest-keyword-first match so 'clearlogo' wins over 'logo', and simple
    English aliases (e.g. 'landscape') are caught before generic words."""
    if not style: return None
    s = style.lower()
    for kw in _ART_KEYWORDS:
        if kw in s:
            return kw
    return None


def _artSpecPrompt(kind: str) -> str:
    """Hardcoded rendering spec for a matched artwork type."""
    spec = _ART_SPECS[kind]
    txt = (f" Use {kind} format: {spec['desc']}. "
           f"Canvas {spec['res']}, aspect ratio {spec['ratio']}.")
    if not spec['transparent']:
        txt += " The background is a full, designed image — do NOT leave it empty or transparent."
    return txt

class OpenRouter(object):


    def __init__(self, service: Optional[_Service] = None):
        if service is None: service = _Service()
        self.service = service
        self.pool    = service.pool
        self.cache   = service.cache
        self.jsonRPC = service.jsonRPC
        


    def log(self, msg: str, level: int = xbmc.LOGDEBUG):
        LOG(f"{self.__class__.__name__}: {msg}", level)


    def _request(self, url: str, params: dict = {}, payload: dict = {}, header: dict = HEADER, timeout: int = 15) -> Optional[dict]:
        # No cacheit here: payload dicts are rebuilt per call, so id()-keyed
        # caching would never hit AND would store stale rows. jsonRPC.requestURL
        # already caches by MD5(url, params, payload, file) for life=15min.
        if Globals.settings.getSettingBool('Allow_Artificial_Intelligence'):
            req_header = BASE_HEADER.copy()
            if header: req_header.update(header)
            req_header.update({"Authorization": f"Bearer {Globals.settings.getSetting('Open_Router_APIKEY')}"})
            if hasattr(self.jsonRPC, 'requestURL'):
                result = self.jsonRPC.requestURL(url, params, payload, req_header, timeout)
                self._notifyError(url, getattr(self.jsonRPC, 'last_status', None),
                                  getattr(self.jsonRPC, 'last_error', None), result)
                return result
        return None


    _last_err_notify = 0.0  # throttle timestamp for the error dialog (seconds)

    # Fallback chains when the configured model fails. There are NO free image
    # models on OpenRouter, so the image chain is the cheapest known-good paid
    # models (cheapest first). The text chain is genuinely free.
    _IMAGE_FALLBACK_MODELS = [
        'google/gemini-3.1-flash-lite-image',
        'google/gemini-2.5-flash-image',
        'openai/gpt-5-image-mini',
    ]
    _TEXT_FALLBACK_MODELS = [
        'google/gemma-4-26b-a4b-it:free',
        'openrouter/free',
        'nvidia/nemotron-nano-9b-v2:free',
    ]

    def _modelChain(self, model: str, fallbacks: list) -> list:
        """Configured model first, then the fallback list (deduped, skipping the
        configured one if it's already in the list)."""
        chain = [model] if model else []
        for m in fallbacks:
            if m != model and m not in chain:
                chain.append(m)
        return chain


    def _freeFallbacks(self, image: bool = False) -> list:
        """Dynamically discover free/owned models from the cached OpenRouter
        /models list (image-capable only when `image`). Includes:
          - `:free` models (genuinely free)
          - `~` BYOK models (user's own provider keys — free to them via their
            provider account, even if OpenRouter lists a list price)
        Merged with the curated list so the rollover stays current.
        """
        ids = []
        try:
            image_models, text_models = self._getModels()
            pool = image_models if image else text_models
            for m in pool:
                mid = str(m.get('id', ''))
                if mid.endswith(':free') or mid.startswith('~'):
                    ids.append(mid)
        except Exception as e:
            self.log(f"_freeFallbacks, failed: {e}", xbmc.LOGDEBUG)
        return ids

    def _notifyDailyAllowed(self) -> bool:
        """True if we're still under the per-day AI notification budget.

        Persists a daily counter in the cache (keyed by date) so the 2-per-day
        cap survives service restarts. Returns False once NOTIFY_AI_DAILY_MAX
        dialogs have fired today.
        """
        day = time.strftime('%Y-%m-%d')
        key = 'OpenRouter.notify.%s' % day
        count = self.cache.get(key) or 0
        if int(count) >= NOTIFY_AI_DAILY_MAX:
            return False
        self.cache.set(key, int(count) + 1, expiration=datetime.timedelta(days=2))
        return True

    def _notifyImageFailure(self):
        """Surface an image-generation failure (empty/no-usable-image response).

        Shares the same short throttle as _notifyError so an HTTP error already
        dialoged moments ago won't double-notify, AND is capped at 2 dialogs per
        day total (persisted) so a persistently failing build can't spam.
        """
        now = time.time()
        if now - OpenRouter._last_err_notify < NOTIFY_AI_ERROR_INTERVAL:
            return
        if not self._notifyDailyAllowed():
            self.log("_notifyImageFailure: daily notification budget reached, skipping", xbmc.LOGDEBUG)
            return
        OpenRouter._last_err_notify = now
        message = LANGUAGE(33246)  # "Image generation failed..."
        self.log(f"_notifyImageFailure: {message}", xbmc.LOGWARNING)
        Globals.dialog.notificationDialog(message, header=ADDON_NAME, time=PROMPT_DELAY)

    def _isProvisioningKey(self) -> Optional[bool]:
        """Detect a management/provisioning OpenRouter key.

        Management/provisioning keys authenticate account endpoints (/auth/key)
        but are rejected by inference (chat/completions -> 401 "User not found").
        Checks the auth/key response (cached 24h) and returns True for such keys,
        False for normal user keys, None when the check couldn't run."""
        key = Globals.settings.getSetting('Open_Router_APIKEY')
        if not key:
            return None
        cache_name = 'OpenRouter.keytype.%s' % FileAccess._getMD5(key)
        cached = self.cache.get(cache_name)
        if cached is not None:
            return cached
        info = self._request("https://openrouter.ai/api/v1/auth/key")
        if not info:
            return None
        data = (info.get('data') or {})
        is_prov = bool(data.get('is_provisioning_key') or data.get('is_management_key'))
        self.cache.set(cache_name, is_prov, expiration=datetime.timedelta(hours=24))
        return is_prov

    def _notifyError(self, url: str, status: Optional[int], body: Any, result: Any = None):
        """Surface OpenRouter API failures as a user dialog.

        OpenRouter errors are HTTP status codes with a JSON body
        {"error": {"message": ...}}: 401 bad/invalid key, 402 insufficient
        credits, 429 rate-limited, 5xx server error. Network failures (timeout,
        unreachable) carry no status at all. Throttled to once per
        NOTIFY_AI_ERROR_INTERVAL so repeated pvr polls can't spam the dialog.
        """
        now = time.time()
        if now - OpenRouter._last_err_notify < NOTIFY_AI_ERROR_INTERVAL:
            return
        # A valid result means the call succeeded — never notify, even if a
        # stale status is left on the shared jsonRPC instance.
        if result is not None:
            return
        if isinstance(status, int) and status < 400:
            return
        OpenRouter._last_err_notify = now
        message = (body or {}).get('error', {}).get('message', '') or ''
        if status == 401:
            # Distinguish a management/provisioning key (rejected for inference
            # with "User not found.") from a plain invalid key — even when
            # OpenRouter supplies a message, the right hint is what matters.
            if self._isProvisioningKey():
                message = LANGUAGE(33245)  # "management key" hint
            elif not message:
                message = LANGUAGE(33243)  # "API key invalid or missing"
        elif not message:
            message = LANGUAGE(30079) if isinstance(status, int) and status >= 400 else LANGUAGE(33244)  # generic / timeout
        self.log(f"_notifyError, status={status}: {message}", xbmc.LOGWARNING)
        Globals.dialog.notificationDialog(f"OpenRouter {status or 'error'}: {message}",
                                          header=ADDON_NAME, time=PROMPT_DELAY)


    def _findGenerated(self, citem: dict) -> Optional[str]:
        """Return an already-generated logo file for a channel, or None.

        Permanent on-disk cache: an image generated once is reused forever, so
        we never re-spend tokens on a channel we already made a logo for.
        Files are named from the channel's unique id-hash, so two channels that
        share a display name never collide.
        """
        stem = self._logoStem(citem)
        for folder in (LOGO_LOC, TEMP_LOC):
            for ext in IMG_EXTS:
                fn = os.path.join(folder, stem + ext)
                if FileAccess.exists(fn):
                    self.log(f'_findGenerated, found cached logo {fn}')
                    return fn
        return None


    @staticmethod
    def _logoStem(citem: dict) -> str:
        """Unique, filesystem-safe filename stem for a channel's generated logo.

        Scheme: ai_<hexid> — the hexid is the first 8 hex chars of the channel's
        unique id, guaranteeing uniqueness even when two channels share a display
        name. The ai_ prefix keeps AI-generated logos identifiable in the cache
        folder. Callers append .png/.jpg (and an _idx variant suffix for
        multi-image requests) on top of this stem.
        """
        cid = str(citem.get('id', '') or '').split('@')[0]
        if len(cid) < 8:
            cid = FileAccess._getMD5(str(citem.get('path', '')))  # fallback hash
        return 'ai_%s' % (cid[:8])


    @staticmethod
    def _modelPriority(model: dict) -> int:
        """Sort rank: BYOK/free first (0), then paid (1). Free and BYOK both
        cost the user nothing (BYOK via their own provider key), so they sort
        ahead of paid models in the picker."""
        mid = str(model.get('id', ''))
        if mid.startswith('~') or mid.endswith(':free'):
            return 0
        pricing = model.get('pricing') or {}
        if str(pricing.get('prompt')) == '0' and str(pricing.get('completion')) == '0':
            return 0
        return 1

    @staticmethod
    def _sortModels(models: list) -> list:
        """Sort by picker rank (free/BYOK first), then name."""
        try:
            return sorted(models, key=lambda m: (OpenRouter._modelPriority(m), str(m.get('name', ''))))
        except Exception:
            return models

    @cacheit(expiration=datetime.timedelta(minutes=15))
    def _getModels(self) -> tuple[list, list]:
        response = self._request("https://openrouter.ai/api/v1/models")
        if not response: return [], []
        image_models = []
        text_models  = []
        if "data" in response:
            for model in response['data']:
                capabilities = model.get("architecture",{}).get("output_modalities", [])
                if   "image" in capabilities: image_models.append(model)
                elif "text"  in capabilities: text_models.append(model)
            self.log('_getModels, image_models = %s, text_models = %s'%(len(image_models),len(text_models)))
        return self._sortModels(image_models), self._sortModels(text_models)
        
        
    @staticmethod
    def _modelLabel(model: dict) -> str:
        """Human label for a model in the picker. Appends markers for source:
        [FREE] when the model costs nothing (pricing.prompt == 0 or a :free
        suffix), [BYOK] when it's a bring-your-own-key model (~ prefix or
        sourced from a provider key)."""
        name = model.get('name') or model.get('id', 'Unknown')
        mid  = str(model.get('id', ''))
        pricing = model.get('pricing') or {}
        free = (str(pricing.get('prompt')) == '0' and str(pricing.get('completion')) == '0') \
               or mid.endswith(':free')
        byok = mid.startswith('~')
        label = str(name)
        if byok:
            label += ' [BYOK]'
        elif free:
            label += ' [FREE]'
        return label

    def _getImageModels(self):
        if not Globals.settings.getSettingBool('Allow_Artificial_Intelligence'): return
        try:
            image_models, _ = self._getModels()
            if not image_models:
                self.log("_getImageModels: No image models available.")
                return
            names = [self._modelLabel(item) for item in image_models]
            preselect_id = Globals._findItemsInLST(image_models, Globals.settings.getSetting('Generative_Image_Model'), 'id')
            select = Globals.dialog.selectDialog(names, header=ADDON_NAME, preselect=preselect_id, useDetails=False, multi=False)
            if not select is None: Globals.settings.setSetting('Generative_Image_Model', image_models[select].get('id'))
        except Exception as e: 
            self.log("_getImageModels, failed! %s" % (e), xbmc.LOGERROR)
            
            
    def _getContextModels(self):
        if not Globals.settings.getSettingBool('Allow_Artificial_Intelligence'): return
        try:
            _, text_models = self._getModels()
            if not text_models:
                self.log("_getContextModels: No context models available.")
                return
            names = [self._modelLabel(item) for item in text_models]
            preselect_id = Globals._findItemsInLST(text_models, Globals.settings.getSetting('Generative_Contextual_Model'), 'id')
            select = Globals.dialog.selectDialog(names, header=ADDON_NAME, preselect=preselect_id, useDetails=False, multi=False)
            if not select is None: Globals.settings.setSetting('Generative_Contextual_Model', text_models[select].get('id'))
        except Exception as e: 
            self.log("_getContextModels, failed! %s" % (e), xbmc.LOGERROR)
        
            
    def getImage(self, citem: dict, count: int = 1, model: str = "google/gemini-2.5-flash-image-preview", background_color: tuple = (0, 255, 0)) -> Union[list, str, bool]:
        if not Globals.settings.getSettingBool('Allow_Artificial_Intelligence'): return False
        chname = citem.get('name', 'unknown_channel')
        self.log('getImage, chname = %s, count = %s, model = %s' % (chname, count, model))

        # Permanent file cache: skip the API entirely when a logo already exists.
        existing = self._findGenerated(citem)
        if existing:
            self.log(f'getImage, cached logo for {chname} -> {existing}')
            return existing if count == 1 else [existing]

        # Try the configured model, then roll through the fallback chain. Each
        # model has its own negative-cache key so a failed model doesn't block
        # the next one from being attempted. Fallbacks = curated cheap list +
        # any current free models discovered from the live /models catalog.
        fallbacks = OpenRouter._IMAGE_FALLBACK_MODELS + self._freeFallbacks(image=True)
        for attempt in self._modelChain(model, fallbacks):
            fail_key = 'OpenRouter.fail.%s.%s' % (chname, attempt)
            if self.cache.get(fail_key):
                self.log(f'getImage, cached failure for {chname} on {attempt}, trying next model')
                continue
            result = self._requestImage(citem, count, attempt, background_color)
            if result:
                return result
            # Model failed — negative-cache just this model so the roll can move on.
            self.cache.set(fail_key, True, expiration=datetime.timedelta(minutes=30))
        self._notifyImageFailure()
        return False


    def _requestImage(self, citem: dict, count: int, model: str, background_color: tuple = (0, 255, 0)) -> Union[list, str, bool]:
        """Attempt image generation with ONE model. Returns a saved path/list on
        success, False on failure (caller rolls to the next model)."""
        chname = citem.get('name', 'unknown_channel')
        self.log('_requestImage, chname = %s, count = %s, model = %s' % (chname, count, model))
        filtered_groups = [g for g in citem.get('group', []) if g != ADDON_NAME]
        group_str = '%s, %s' % (chname, ', '.join(filtered_groups)) if filtered_groups else chname
        # Single editable user prompt. The system layer is hardcoded in code:
        #   * channel attributes (name/radio/type/group)
        #   * the matched Kodi artwork-type spec (clearlogo/clearart/poster/...)
        #   * the chroma-key contract for transparent types (green #00FF00 bg
        #     that _alphaImage keys out)
        prompt = Globals.settings.getSetting('Generative_Image_Style')
        kind = _matchArtType(prompt) or 'clearlogo'  # default channel art
        key_background = _ART_SPECS[kind]['transparent']
        messages = [{"role": "user", "content": prompt}]
        if prompt.strip():
            media_hint = 'a music/radio channel' if citem.get('radio') else 'a television channel'
            type_hint  = f" content type: {citem.get('type', '')}" if citem.get('type') else ''
            theme_hint = f" theme: {group_str}" if group_str else ''
            contract = (f"This is {media_hint} named \"{chname}\".{type_hint}{theme_hint}. "
                        "Output ONLY the artwork. Use bold, high-contrast colors that stay legible "
                        "when overlaid on both light and dark video. No watermarks, extra text, or UI "
                        "elements.")
            contract += _artSpecPrompt(kind)
            if key_background:
                # Chroma-key contract: required so _alphaImage can key out the bg.
                contract += (" The background must be one single flat solid color: pure green #00FF00 "
                             "(RGB 0,255,0) — the KEY color. No gradients, shading, texture, border, frame, "
                             "or shadow behind the artwork. The artwork itself must NOT contain any green or "
                             "lime tones — any green is keyed out and becomes transparent. Keep every edge of "
                             "the artwork fully separated from the green.")
            messages.insert(0, {"role": "system", "content": contract})
        payload = {
                    "model": model,
                    "messages": messages,
                    "modalities": ["image"],
                    "response_format": {"type": "b64_json"},
                    # Cap output tokens: without max_tokens OpenRouter defaults to
                    # 32768, which exceeds a small key's per-request credit budget
                    # (HTTP 402 "can only afford N tokens"). A modest cap fits a
                    # single logo comfortably.
                    "max_tokens": AI_IMAGE_MAX_TOKENS,
                    "n": count,
                    "provider": {
                        "allow_fallbacks": True,
                        "require_parameters": True,
                        "data_collection": "deny"
                    }
                }

        # Image generation is slow (20-60s+); the default 15s request timeout
        # was timing out before the model could finish. Give it a generous cap.
        response = self._request("https://openrouter.ai/api/v1/chat/completions", payload=payload, timeout=AI_IMAGE_TIMEOUT)
        if not response or "choices" not in response:
            self.log("_requestImage: Invalid or empty response received from OpenRouter API.", xbmc.LOGERROR)
            return False
        try:
            message_content = response["choices"][0].get("message", {})
            images = message_content.get("images", [])
            if not images:
                self.log("_requestImage: No images found in the response message payload.", xbmc.LOGWARNING)
                return False

            logos = []
            for idx, image_node in enumerate(images):
                img_url = image_node.get("image_url", {}).get("url", "")
                if not img_url: continue
                # Regex matches standard Data URI format (e.g., data:image/png;base64,iVBORw0KGg...)
                match = re.match(r"data:image/(?P<ext>.*?);base64,(?P<data>.*)", img_url)
                if not match:
                    self.log("_requestImage: Target image URI failed to match base64 extraction format regex.", xbmc.LOGWARNING)
                    continue
                ext = match.group('ext').split(';')[0] or 'png'
                b64_data = match.group('data')
                try:
                    stem = self._logoStem(citem)
                    file_name = f"{stem}_{idx}.{ext}" if count > 1 else f"{stem}.{ext}"
                    raw = base64.b64decode(b64_data + '=' * (-len(b64_data) % 4))
                    with FileAccess.stream(os.path.join(TEMP_LOC, file_name), "w") as f:
                        f.write(raw)
                    logos.append(self._alphaImage(file_name, background_color=background_color, key_background=key_background))
                except Exception as b64_err:
                    self.log(f"_requestImage: Base64 binary decoding failed for {file_name}: {b64_err}", xbmc.LOGERROR)
            if logos:
                return logos if count > 1 else logos[0]
            self.log("_requestImage: no decodable images returned.", xbmc.LOGWARNING)
            return False
        except Exception as system_err:
            self.log(f"_requestImage: Critical engine breakdown handling response: {system_err}", xbmc.LOGERROR)
            return False


        
    def _alphaImage(self, file_name: str, background_color: tuple = (0, 255, 0), key_background: bool = True) -> str:
        input_file_path  = os.path.join(TEMP_LOC, file_name)
        output_file_path = os.path.join(LOGO_LOC, file_name)
        if not FileAccess.exists(input_file_path):
            self.log(f"_alphaImage, Error: Source file missing at {input_file_path}", xbmc.LOGERROR)
            return output_file_path

        if not key_background:
            # Opaque art type (poster/fanart/banner/...): the background IS the
            # image — never chroma-key it. Just move the raw file into LOGO_LOC.
            return self._moveToLogo(input_file_path, output_file_path)

        if Globals.settings.hasAddon('script.module.pil'):
            try:
                from PIL import Image
                from collections import deque

                fle = FileAccess.open(input_file_path, "rb")
                img_data = fle.readBytes()
                fle.close()
                img = Image.open(BytesIO(img_data)).convert("RGBA")
                w, h = img.size
                pixels = img.load()

                def _hasAlpha() -> bool:
                    """True when the image already carries real transparency —
                    a meaningful share of pixels are not fully opaque."""
                    n = 0
                    semi = 0
                    for y in range(0, h, max(1, h // 64)):
                        for x in range(0, w, max(1, w // 64)):
                            a = pixels[x, y][3]
                            n += 1
                            if a < 250: semi += 1
                    return n and (semi / n) > 0.005  # >0.5% sampled pixels transparent

                # Chroma-key the declared green regardless of any existing alpha:
                # a model may return a PNG that's partially transparent yet still
                # has a green backdrop (the explicit rendering contract). Only
                # skip keying when the background is genuinely transparent AND no
                # green remains, otherwise the logo keeps a green fringe.
                tolerance = 60  # RGB distance; generous for AI fringing
                key = tuple(background_color[:3])
                def _match(c, target) -> bool:
                    return sqrt((c[0] - target[0]) ** 2 + (c[1] - target[1]) ** 2 + (c[2] - target[2]) ** 2) <= tolerance

                def _hasGreen(c) -> bool:
                    return _match(c, key)

                if not _hasAlpha() or any(_hasGreen(pixels[x, y]) for x in range(0, w, max(1, w // 16)) for y in range(0, h, max(1, h // 16))):
                    # Prefer the declared key color (matches the system prompt's
                    # #00FF00); fall back to border detection if the model ignored it.
                    border = [pixels[x, 0] for x in range(0, w, max(1, w // 32))]
                    border += [pixels[x, h - 1] for x in range(0, w, max(1, w // 32))]
                    border += [pixels[0, y] for y in range(0, h, max(1, h // 32))]
                    border += [pixels[w - 1, y] for y in range(0, h, max(1, h // 32))]
                    border_rgb = [tuple(p[:3]) for p in border]
                    if key in border_rgb or any(_match(c, key) for c in border_rgb):
                        bg = key
                    else:
                        # Most common border color = the actual background.
                        bg = Counter(border_rgb).most_common(1)[0][0]

                    def _match_key(c) -> bool:
                        return _match(c, bg)

                    # Seed flood fill from every edge pixel matching the bg color.
                    seen = set()
                    stack = deque()
                    for x in range(w):
                        for y in (0, h - 1):
                            if _match_key(pixels[x, y]) and (x, y) not in seen:
                                seen.add((x, y))
                                stack.append((x, y))
                    for y in range(h):
                        for x in (0, w - 1):
                            if _match_key(pixels[x, y]) and (x, y) not in seen:
                                seen.add((x, y))
                                stack.append((x, y))
                    while stack:
                        x, y = stack.pop()
                        r, g, b, a = pixels[x, y]
                        # Feather: keep a thin semi-transparent halo at the boundary
                        # so anti-aliased edges don't look jagged.
                        if _match_key((r, g, b)):
                            pixels[x, y] = (r, g, b, 0)
                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and _match_key(pixels[nx, ny]):
                                seen.add((nx, ny))
                                stack.append((nx, ny))
                    self.log(f"_alphaImage: keyed out background {bg} (tolerance={tolerance})")

                img.save(FileAccess.translatePath(output_file_path), "PNG")
                self.log(f"_alphaImage: Image saved with transparency at: {output_file_path}")
                if FileAccess.exists(output_file_path): FileAccess.delete(input_file_path)
                return output_file_path
            except Exception as pil_err:
                self.log(f"_alphaImage: Local PIL processing failed. Falling back to raw copy. Error: {pil_err}", xbmc.LOGWARNING)

        # No PIL (or PIL failed): move the raw temp file into LOGO_LOC so the
        # permanent file cache still works — otherwise every build re-spends
        # tokens regenerating the same logo.
        return self._moveToLogo(input_file_path, output_file_path)


    def _moveToLogo(self, input_file_path: str, output_file_path: str) -> str:
        """Move a temp image into LOGO_LOC (raw fallback / opaque art types)."""
        try:
            if FileAccess.exists(output_file_path):
                FileAccess.delete(input_file_path)
                self.log(f"_alphaImage: raw fallback already at {output_file_path}")
            elif FileAccess.rename(input_file_path, output_file_path):
                self.log(f"_alphaImage: raw fallback saved at {output_file_path}")
            else:
                FileAccess.delete(input_file_path)
        except Exception as e:
            self.log(f"_alphaImage: raw fallback failed: {e}", xbmc.LOGWARNING)
        return output_file_path
            
            
    @staticmethod
    def _run(sysARG: list) -> tuple:
        with Globals.builtin.busy_dialog():
            ctl = (5,1)
            try:              param = sysARG[1]
            except Exception: param = None
            LOG('OpenRouter: param = %s'%(param))
            if param == 'getImageModels':   OpenRouter()._getImageModels()
            if param == 'getContextModels': OpenRouter()._getContextModels()
            return Globals._openSettings(ctl)

if __name__ == '__main__': OpenRouter()._run(sys.argv)
