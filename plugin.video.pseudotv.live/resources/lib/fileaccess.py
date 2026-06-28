#   Copyright (C) 2026 Lunatixz
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
#
# -*- coding: utf-8 -*-
import codecs, shutil, errno

from constants   import *
from logger      import log

#constants 
DEFAULT_ENCODING = "utf-8"

class FileAccess:

    @staticmethod
    def _getMD5(data):
        if not isinstance(data, (str, bytes, bytearray)):
            data = FileAccess.dumpJSON(data, sortkey=True)
        if isinstance(data, str):
            data = data.encode(DEFAULT_ENCODING)
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def _encodeString(data=''):
        if not data:
            return ""
        try:
            normalized_str = FileAccess.dumpJSON(data)
            compressed = zlib.compress(normalized_str.encode(DEFAULT_ENCODING), level=1)
            return base64.urlsafe_b64encode(compressed).decode('ascii')
        except Exception as e:
            log(f"_encodeString failed! {e}", xbmc.LOGERROR)
        return ""

    @staticmethod
    def _decodeString(data=''):
        if not data:
            return ""
        try:
            if isinstance(data, str):
                data = data.encode('ascii')
            padded_data = data + b'=' * (-len(data) % 4)
            raw_bytes = base64.urlsafe_b64decode(padded_data)
            decompressed_str = zlib.decompress(raw_bytes).decode(DEFAULT_ENCODING)
            return FileAccess.loadJSON(decompressed_str)
        except Exception as e:
            log(f"_decodeString failed! {e}", xbmc.LOGERROR)
        return ""

    @staticmethod
    def dumpPICKLE(item=None):
        if item is None:
            return b""
        try:
            if hasattr(item, 'write'):
                pickle.dump(None, item)
                return b""
            if isinstance(item, (bytes, bytearray)):
                return bytes(item)
            return pickle.dumps(item, protocol=4)
        except Exception as e:
            log(f"dumpPICKLE failed! {e}", xbmc.LOGERROR)
        return b""

    @staticmethod
    def loadPICKLE(item=None):
        if not item:
            return None
        try:
            if hasattr(item, 'read'):
                return pickle.load(item)
            if isinstance(item, str):
                item = item.encode('latin-1')
            return pickle.loads(item)
        except pickle.UnpicklingError:
            pass
        except Exception as e:
            log(f"loadPICKLE failed! {e}", xbmc.LOGERROR)
        return None

    @staticmethod
    def dumpJSON(item=None, idnt=None, sortkey=False, separators=(',', ':')):
        try:
            if item is None:
                return '{}'
            if isinstance(item, (bytes, bytearray)):
                return item.decode('utf-8')
            if isinstance(item, str):
                return item
            if hasattr(item, 'write'):
                json.dump(None, item, indent=idnt, sort_keys=sortkey, separators=separators)
                return '{}'
            return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
        except (TypeError, ValueError):
            return '{}'
        except Exception as e:
            log(f"dumpJSON failed! {e}", xbmc.LOGERROR)
        return '{}'

    @staticmethod
    def loadJSON(item=""):
        if not item:
            return {}
        try:
            if hasattr(item, 'read'):
                return json.load(item) or {}
            if isinstance(item, (bytes, bytearray)):
                item = item.decode('utf-8')
            return json.loads(item)
        except (json.JSONDecodeError, TypeError):
            return item
        except Exception as e:
            log(f"loadJSON failed! {e}", xbmc.LOGERROR)
        return item

    @staticmethod
    def getJSON(file_path):
        try:
            with FileAccess.stream(file_path, 'r') as fle:
                return FileAccess.loadJSON(fle.read())
        except Exception as e:
            log(f"getJSON failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return {}

    @staticmethod
    def setJSON(file_path, data):
        with FileLock(file_path):
            try:
                with FileAccess.stream(file_path, 'w') as fle:
                    fle.write(FileAccess.dumpJSON(data, idnt=4, sortkey=False))
                return True
            except Exception as e:
                log(f"setJSON failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return False

    @staticmethod
    def setURL(url, file_path):
        try:
            req = urllib.request.Request(url, headers=HEADER)
            monitor = MONITOR()
            with urllib.request.urlopen(req) as response:
                with FileAccess.stream(file_path, 'w') as f:
                    while not monitor.abortRequested():
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            return True
        except Exception as e:
            log(f"setURL failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return False

    @staticmethod
    def open(filename, mode, encoding=DEFAULT_ENCODING):
        try:
            return VFSFile(filename, mode)
        except UnicodeDecodeError:
            return VFSFile(filename, mode)  # Fallback logic retained from original

    @staticmethod
    @contextmanager
    def stream(filename, mode='r', encoding=DEFAULT_ENCODING):
        f = FileAccess.open(filename, mode, encoding)
        try:
            yield f
        finally:
            f.close()

    @staticmethod
    def _getFolderPath(path):
        head, tail = os.path.split(path)
        return os.path.join(os.path.basename(head), tail)

    @staticmethod
    def _getShortPath(path, max_parts=3):
        parts = path.split(os.sep)
        if len(parts) > max_parts:
            return f"...{os.sep}{os.path.join(*parts[-max_parts:])}"
        return path

    @staticmethod
    def listdir(path):
        if FileAccess.exists(path):
            return xbmcvfs.listdir(path)
        return [], []

    @staticmethod
    def mkdirs(path):
        if not path.endswith(("/", "\\")):
            path = f"{path}/"
        return xbmcvfs.mkdirs(path)

    @staticmethod
    def translatePath(path):
        if '@' in path:
            path = path.split('@')[1]
        return xbmcvfs.translatePath(path)

    @staticmethod
    def copyFolder(src, dest_dir, dia=None, move=False):
        log(f"copyFolder {src} to {dest_dir}")
        if not FileAccess.exists(dest_dir):
            FileAccess.mkdirs(dest_dir)
        
        if dia is not None:
            dia._updateProgress(dia, 0, message=f"{LANGUAGE(32051)}\n{src}")

        subs, files = FileAccess.listdir(src)
        
        for fidx, file in enumerate(files):
            progress = int(fidx * 100) // max(len(files), 1)
            if dia is not None:
                dia._updateProgress(dia, progress, message=f'copying {file} {progress}%\n{fidx}/{len(files)}')
            
            src_file = os.path.join(src, file)
            dest_file = os.path.join(dest_dir, file)
            if move:
                FileAccess.move(src_file, dest_file)
            else:
                FileAccess.copy(src_file, dest_file)
        
        for sidx, sub in enumerate(subs):
            progress = int(sidx * 100) // max(len(subs), 1)
            if dia is not None:
                dia._updateProgress(dia, progress, message=f'copying {sub} {progress}%\n{sidx}/{len(subs)}')
            FileAccess.copyFolder(os.path.join(src, sub), os.path.join(dest_dir, sub), dia, move)
        return dia

    @staticmethod
    def copy(orgfilename, newfilename):
        if not FileAccess.exists(orgfilename):
            return False
        parent_dir, _ = os.path.split(newfilename)
        if not FileAccess.exists(parent_dir):
            FileAccess.mkdirs(parent_dir)
        elif FileAccess.exists(newfilename):
            FileAccess.delete(newfilename)
            
        log(f"copying {orgfilename} to {newfilename}")
        if xbmcvfs.copy(orgfilename, newfilename):
            return FileAccess.exists(newfilename)
        return False

    @staticmethod
    def move(orgfilename, newfilename):
        log(f"moving {orgfilename} to {newfilename}")
        if FileAccess.copy(orgfilename, newfilename):
            return FileAccess.delete(orgfilename)
        return False

    @staticmethod
    def delete(filename):
        try:
            if not FileAccess.exists(filename):
                return False
            log(f"delete {filename}", xbmc.LOGINFO)
            return xbmcvfs.delete(filename)
        except Exception as e:
            log(f"delete failed via VFS! {e}. Attempting native os.remove", xbmc.LOGERROR)
            translated = FileAccess.translatePath(filename)
            if os.path.exists(translated):
                os.remove(translated)
            return not FileAccess.exists(filename)

    @staticmethod
    def exists(path):
        filepath = path
        if filepath.startswith('stack://'):
            try:
                filepath = (filepath.split('stack://')[1].split(' , '))[0]
            except Exception:
                pass
        
        exists = xbmcvfs.exists(filepath)
        if not exists and not filepath.endswith('\\'):
            filepath_slashed = os.path.join(filepath, '')
            exists = os.path.exists(filepath_slashed) or os.path.exists(FileAccess.translatePath(filepath_slashed))
            
        log(f"path = {path}, exists = {exists}")
        return exists

    @staticmethod
    def openSMB(filename, mode, encoding=DEFAULT_ENCODING):
        if os.name.lower() == 'nt' and filename.lower().startswith('smb://'):
            newname = '\\\\' + filename[6:]
            try:
                return codecs.open(newname, mode, encoding)
            except Exception:
                pass
        return None

    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt' and filename.lower().startswith('smb://'):
            return FileAccess.exists('\\\\' + filename[6:])
        return False

    @staticmethod
    def rename(path, newpath, force=True):
        log(f"rename {path} to {newpath}, force = {force}")
        if not FileAccess.exists(path):
            return False
        
        try:
            if xbmcvfs.rename(path, newpath):
                return FileAccess.exists(newpath)
        except Exception as e:
            log(f"xbmcvfs.rename failed! {e}", xbmc.LOGERROR)
            
        try:
            if FileAccess.move(path, newpath):
                return True
        except Exception as e:
            log(f"Fallback move failed! {e}", xbmc.LOGERROR)
           
        if os.name.lower() == 'nt':
            if path.lower().startswith('smb://'): 
                path = '\\\\' + path[6:]
            if newpath.lower().startswith('smb://'): 
                newpath = '\\\\' + newpath[6:]
                
        trans_path = FileAccess.translatePath(path)
        trans_newpath = FileAccess.translatePath(newpath)
        
        if not os.path.exists(trans_path):
            return False
        
        try:
            os.rename(trans_path, trans_newpath)
            return True
        except Exception as e:
            log(f"os.rename failed! {e}", xbmc.LOGERROR)
     
        try:
            shutil.move(trans_path, trans_newpath)
            return True
        except Exception as e:
            log(f"shutil.move failed! {e}", xbmc.LOGERROR)
            
        return False

    @staticmethod
    def removedirs(path, force=True):
        log(f"removedirs, path = {path}, force = {force}")
        if not path:
            return False
        try:
            if xbmcvfs.rmdir(path, force=force):
                return True
        except Exception:
            try:
                translated = FileAccess.translatePath(path)
                os.rmdir(translated)
                return not os.path.exists(translated)
            except Exception:
                log("removedirs completely failed!", xbmc.LOGERROR)
        return False
            
    @staticmethod
    def makedirs(path):
        try:
            log(f"makedirs, path = {path}")
            translated = FileAccess.translatePath(path)
            os.makedirs(translated, exist_ok=True)
            return os.path.exists(translated)
        except Exception:
            return FileAccess._makedirs_fallback(path)
            
    @staticmethod
    def _makedirs_fallback(path):
        if not path:
            return False
        if xbmcvfs.exists(path):
            return True
        if not xbmcvfs.mkdir(path):
            parent = os.path.dirname(FileAccess.translatePath(path))
            if path == parent:
                return False
            if FileAccess._makedirs_fallback(parent):
                return xbmcvfs.mkdir(path)
        return bool(xbmcvfs.exists(path))


class VFSFile:
    monitor = MONITOR()
    
    def __init__(self, filename, mode):
        self.filename = filename
        if mode == 'w':
            parent_dir = os.path.split(filename)[0]
            if not FileAccess.exists(parent_dir):
                FileAccess.mkdirs(parent_dir)
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:
            self.currentFile = xbmcvfs.File(filename, 'r')
            
        log(f"VFSFile Opening {filename}", xbmc.LOGDEBUG)
        if self.currentFile is None:
            log(f"VFSFile Couldn't open {filename}", xbmc.LOGERROR)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def read(self, num_bytes=0):
        try:
            return self.currentFile.read(num_bytes)
        except Exception:
            return self.currentFile.readBytes(num_bytes)
        
    def readBytes(self, num_bytes=0):
        return self.currentFile.readBytes(num_bytes)
        
    def write(self, buffer):
        if not isinstance(buffer, (bytes, bytearray)):
            buffer = buffer.encode(DEFAULT_ENCODING, 'backslashreplace')
        return self.currentFile.write(buffer)
        
    def close(self):
        if self.currentFile:
            return self.currentFile.close()

    def seek(self, num_bytes, offset=1):
        return self.currentFile.seek(num_bytes, offset)

    def size(self):
        return self.currentFile.size()

    def tell(self):
        try:
            return self.currentFile.tell()
        except Exception:
            return self.currentFile.seek(0, 1)

    def readlines(self):
        try:
            return ''.join(list(self.readline())).split('\n')
        except Exception:
            return self.read().split('\n')

    def readline(self):
        try:
            yield from self.read_in_chunks()
        except Exception as e:
            log(f"VFSFile: readline failed! {e}", xbmc.LOGERROR)
        
    def read_in_chunks(self, chunk_size=1024):
        while not self.monitor.abortRequested():
            data = self.read(chunk_size)
            if not data:
                break
            yield data


class FileLock:
    monitor = MONITOR()
    thread_lock = Lock()
 
    def __init__(self, filename, timeout=LOCK_MAX_FILE_TIMEOUT, delay=LOCK_MAX_FILE_DELAY):
        self.is_locked = False
        self.lockfile = f"{os.path.splitext(filename.strip('\\'))[0]}.lock"
        self.timeout = timeout
        self.delay = delay
        self.fd = None
 
    def __del__(self):
        try:
            self.release()
        except Exception:
            pass
        
    def acquire(self):
        with self.thread_lock:
            start_time = time.time()
            while not self.monitor.abortRequested():
                if FileAccess.exists(self.lockfile):
                    if (time.time() - start_time) >= self.timeout:
                        log("FileLock Timeout occurred waiting for lock to release.", xbmc.LOGWARNING)
                        break
                    self.monitor.waitForAbort(self.delay)
                    continue
                
                try:
                    self.fd = FileAccess.open(self.lockfile, 'w')
                    self.is_locked = True
                    break
                except Exception as e:
                    log(f"FileLock acquiring failed! {e}", xbmc.LOGERROR)
                    break
 
    def release(self):
        if self.is_locked:
            if self.fd and hasattr(self.fd, 'close'):
                self.fd.close()
            self.is_locked = False
            FileAccess.delete(self.lockfile)
 
    def __enter__(self):
        if not self.is_locked:
            self.acquire()
        return self
 
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
