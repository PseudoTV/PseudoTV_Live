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
from variables   import *
from typing import Any, Generator, Iterator, List, Optional, Tuple, Union

class FileAccess(object):
    _JSON_CACHE_MAX = 512
    _json_cache = OrderedDict()

    @staticmethod
    def _getMD5(data: Any) -> str:
        if not isinstance(data, (str, bytes, bytearray)):
            data = FileAccess.dumpJSON(data, sortkey=True)
        if isinstance(data, str):
            data = data.encode(DEFAULT_ENCODING)
        return hashlib.md5(data).hexdigest()

    @staticmethod
    def _encodeString(data: str = "") -> str:
        """Compress and base64-encode a value for safe storage."""
        if not data:
            return ""
        try:
            normalized_str = FileAccess.dumpJSON(data)
            compressed = zlib.compress(normalized_str.encode(DEFAULT_ENCODING), level=1)
            return base64.urlsafe_b64encode(compressed).decode('ascii')
        except Exception as e:
            LOG(f"_encodeString failed! {e}", xbmc.LOGERROR)
        return ""

    @staticmethod
    def _decodeString(data: str = "") -> Any:
        """Decode and decompress a base64-encoded value."""
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
            LOG(f"_decodeString failed! {e}", xbmc.LOGERROR)
        return ""

    @staticmethod
    def dumpPICKLE(item: Any = None) -> bytes:
        """Serialize an object to bytes using pickle protocol 4."""
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
            LOG(f"dumpPICKLE failed! {e}", xbmc.LOGERROR)
        return b""

    @staticmethod
    def loadPICKLE(item: Any = None) -> Any:
        """Deserialize a pickle bytes stream or string back to an object."""
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
            LOG(f"loadPICKLE failed! {e}", xbmc.LOGERROR)
        return None

    @staticmethod
    def dumpJSON(item: Any = None, idnt: Optional[int] = None, sortkey: bool = False, separators: Tuple[str, str] = (',', ':')) -> str:
        """Serialize an object to a JSON string with optional indentation and sorting."""
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
            LOG(f"dumpJSON failed! {e}", xbmc.LOGERROR)
        return '{}'

    @staticmethod
    def loadJSON(item: str = "") -> Any:
        """Deserialize a JSON string with LRU caching for small strings."""
        if not item:
            return {}
        try:
            if hasattr(item, 'read'):
                return json.load(item) or {}
            if isinstance(item, (bytes, bytearray)):
                item = item.decode('utf-8')
            if isinstance(item, str) and len(item) < 8192:
                cached = FileAccess._json_cache.get(item)
                if cached is not None:
                    FileAccess._json_cache.move_to_end(item)
                    return cached.copy() if hasattr(cached, 'copy') else cached
                result = json.loads(item)
                FileAccess._json_cache[item] = result
                if len(FileAccess._json_cache) > FileAccess._JSON_CACHE_MAX:
                    FileAccess._json_cache.popitem(last=False)
                return result
            return json.loads(item)
        except (json.JSONDecodeError, TypeError):
            return item
        except Exception as e:
            LOG(f"loadJSON failed! {e}", xbmc.LOGERROR)
        return item

    @staticmethod
    def getJSON(file_path: str) -> dict:
        """Read a JSON file and return the parsed content."""
        try:
            with FileAccess.stream(file_path, 'r') as fle:
                return FileAccess.loadJSON(fle.read())
        except Exception as e:
            LOG(f"getJSON failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return {}

    @staticmethod
    def setJSON(file_path: str, data: Any) -> bool:
        """Write data to a JSON file with file locking."""
        with FileLock(file_path):
            try:
                with FileAccess.stream(file_path, 'w') as fle:
                    fle.write(FileAccess.dumpJSON(data, idnt=4, sortkey=False))
                return True
            except Exception as e:
                LOG(f"setJSON failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return False

    @staticmethod
    def setURL(url: str, file_path: str) -> bool:
        """Download a URL and save it to a local file."""
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
            LOG(f"setURL failed! {e}\nfile = {file_path}", xbmc.LOGERROR)
        return False

    @staticmethod
    def open(filename: str, mode: str, encoding: str = DEFAULT_ENCODING) -> 'VFSFile':
        try:
            return VFSFile(filename, mode)
        except UnicodeDecodeError:
            return VFSFile(filename, mode)  # Fallback logic retained from original

    @staticmethod
    @contextmanager
    def stream(filename: str, mode: str = 'r', encoding: str = DEFAULT_ENCODING) -> Iterator['VFSFile']:
        f = FileAccess.open(filename, mode, encoding)
        try:
            yield f
        finally:
            f.close()

    @staticmethod
    def _getFolderPath(path: str) -> str:
        head, tail = os.path.split(path)
        return os.path.join(os.path.basename(head), tail)

    @staticmethod
    def _getShortPath(path: str, max_parts: int = 3) -> str:
        parts = path.split(os.sep)
        if len(parts) > max_parts:
            return f"...{os.sep}{os.path.join(*parts[-max_parts:])}"
        return path

    @staticmethod
    def listdir(path: str) -> Tuple[List[str], List[str]]:
        if FileAccess.exists(path):
            return xbmcvfs.listdir(path)
        return [], []

    @staticmethod
    def mkdirs(path: str) -> bool:
        if not path.endswith(("/", "\\")):
            path = f"{path}/"
        return xbmcvfs.mkdirs(path)

    @staticmethod
    def translatePath(path: str) -> str:
        if '@' in path:
            path = path.split('@')[1]
        return xbmcvfs.translatePath(path)

    @staticmethod
    def copyFolder(src: str, dest_dir: str, dia: Any = None, move: bool = False) -> Any:
        """Recursively copy/move a folder with optional progress dialog."""
        LOG(f"copyFolder {src} to {dest_dir}")
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
    def copy(orgfilename: str, newfilename: str) -> bool:
        if not FileAccess.exists(orgfilename):
            return False
        parent_dir, _ = os.path.split(newfilename)
        if not FileAccess.exists(parent_dir):
            FileAccess.mkdirs(parent_dir)
        elif FileAccess.exists(newfilename):
            FileAccess.delete(newfilename)
            
        LOG(f"copying {orgfilename} to {newfilename}")
        if xbmcvfs.copy(orgfilename, newfilename):
            return FileAccess.exists(newfilename)
        return False

    @staticmethod
    def move(orgfilename: str, newfilename: str) -> bool:
        LOG(f"moving {orgfilename} to {newfilename}")
        if FileAccess.copy(orgfilename, newfilename):
            return FileAccess.delete(orgfilename)
        return False

    @staticmethod
    def delete(filename: str) -> bool:
        try:
            if not FileAccess.exists(filename):
                return False
            LOG(f"delete {filename}", xbmc.LOGINFO)
            return xbmcvfs.delete(filename)
        except Exception as e:
            LOG(f"delete failed via VFS! {e}. Attempting native os.remove", xbmc.LOGERROR)
            translated = FileAccess.translatePath(filename)
            if os.path.exists(translated):
                os.remove(translated)
            return not FileAccess.exists(filename)

    @staticmethod
    def exists(path: str) -> bool:
        filepath = path
        if filepath.startswith('stack://'):
            try:
                filepath = (filepath.split('stack://')[1].split(' , '))[0]
            except Exception as e:
                LOG("exists stack:// parse failed: %s" % e, xbmc.LOGDEBUG)
        
        exists = xbmcvfs.exists(filepath)
        if not exists and not filepath.endswith('\\'):
            filepath_slashed = os.path.join(filepath, '')
            exists = os.path.exists(filepath_slashed) or os.path.exists(FileAccess.translatePath(filepath_slashed))
            
        LOG(f"path = {path}, exists = {exists}")
        return exists

    @staticmethod
    def openSMB(filename: str, mode: str, encoding: str = DEFAULT_ENCODING) -> Optional[Any]:
        if os.name.lower() == 'nt' and filename.lower().startswith('smb://'):
            newname = '\\\\' + filename[6:]
            try:
                return codecs.open(newname, mode, encoding)
            except Exception as e:
                LOG("openSMB %s failed: %s" % (newname, e), xbmc.LOGDEBUG)
        return None

    @staticmethod
    def existsSMB(filename: str) -> bool:
        if os.name.lower() == 'nt' and filename.lower().startswith('smb://'):
            return FileAccess.exists('\\\\' + filename[6:])
        return False

    @staticmethod
    def rename(path: str, newpath: str, force: bool = True) -> bool:
        """Rename a file using multiple fallback strategies (xbmcvfs, os, shutil)."""
        LOG(f"rename {path} to {newpath}, force = {force}")
        if not FileAccess.exists(path):
            return False
        
        try:
            if xbmcvfs.rename(path, newpath):
                return FileAccess.exists(newpath)
        except Exception as e:
            LOG(f"xbmcvfs.rename failed! {e}", xbmc.LOGERROR)
            
        try:
            if FileAccess.move(path, newpath):
                return True
        except Exception as e:
            LOG(f"Fallback move failed! {e}", xbmc.LOGERROR)
           
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
            LOG(f"os.rename failed! {e}", xbmc.LOGERROR)
     
        try:
            shutil.move(trans_path, trans_newpath)
            return True
        except Exception as e:
            LOG(f"shutil.move failed! {e}", xbmc.LOGERROR)
            
        return False

    @staticmethod
    def removedirs(path: str, force: bool = True) -> bool:
        """Remove a directory with fallback to native os.rmdir."""
        LOG(f"removedirs, path = {path}, force = {force}")
        if not path:
            return False
        try:
            if xbmcvfs.rmdir(path, force=force):
                return True
        except Exception as e:
            LOG(f"removedirs, xbmcvfs.rmdir failed for {path}: {e}", xbmc.LOGWARNING)
            try:
                translated = FileAccess.translatePath(path)
                os.rmdir(translated)
                return not os.path.exists(translated)
            except Exception:
                LOG("removedirs completely failed!", xbmc.LOGERROR)
        return False
            
    @staticmethod
    def makedirs(path: str) -> bool:
        try:
            LOG(f"makedirs, path = {path}")
            translated = FileAccess.translatePath(path)
            os.makedirs(translated, exist_ok=True)
            return os.path.exists(translated)
        except Exception as e:
            LOG(f"makedirs, os.makedirs failed for {path}: {e}", xbmc.LOGWARNING)
            return FileAccess._makedirs_fallback(path)
            
    @staticmethod
    def _makedirs_fallback(path: str) -> bool:
        """Recursively create directories using xbmcvfs as fallback."""
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
    def __init__(self, filename: str, mode: str):
        self.monitor  = MONITOR()
        self.filename = filename
        if mode == 'w':
            parent_dir = os.path.split(filename)[0]
            if not FileAccess.exists(parent_dir):
                FileAccess.mkdirs(parent_dir)
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:
            self.currentFile = xbmcvfs.File(filename, 'r')
            
        LOG(f"VFSFile Opening {filename}", xbmc.LOGDEBUG)
        if self.currentFile is None:
            LOG(f"VFSFile Couldn't open {filename}", xbmc.LOGERROR)

    def __enter__(self) -> 'VFSFile':
        return self

    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Any):
        self.close()

    def read(self, num_bytes: int = 0) -> Union[bytes, str]:
        try:
            return self.currentFile.read(num_bytes)
        except Exception:
            return self.currentFile.readBytes(num_bytes)
        
    def readBytes(self, num_bytes: int = 0) -> bytes:
        return self.currentFile.readBytes(num_bytes)
        
    def write(self, buffer: Union[str, bytes, bytearray]) -> int:
        if not isinstance(buffer, (bytes, bytearray)):
            buffer = buffer.encode(DEFAULT_ENCODING, 'backslashreplace')
        return self.currentFile.write(buffer)
        
    def close(self):
        if self.currentFile:
            return self.currentFile.close()

    def seek(self, num_bytes: int, offset: int = 1) -> int:
        return self.currentFile.seek(num_bytes, offset)

    def size(self) -> int:
        return self.currentFile.size()

    def tell(self) -> int:
        try:
            return self.currentFile.tell()
        except Exception:
            return self.currentFile.seek(0, 1)

    def readlines(self) -> List[str]:
        try:
            return ''.join(list(self.readline())).split('\n')
        except Exception:
            return self.read().split('\n')

    def readline(self) -> Generator[str, None, None]:
        try:
            yield from self.read_in_chunks()
        except Exception as e:
            LOG(f"VFSFile: readline failed! {e}", xbmc.LOGERROR)
        
    def read_in_chunks(self, chunk_size: int = 1024) -> Generator[str, None, None]:
        """Read file data in fixed-size chunks."""
        while not self.monitor.abortRequested():
            data = self.read(chunk_size)
            if not data:
                break
            yield data


class FileLock:
    def __init__(self, filename: str, timeout: Optional[float] = None, delay: Optional[float] = None):
        if timeout is None: timeout = LOCK_MAX_FILE_TIMEOUT
        if delay is None: delay = LOCK_MAX_FILE_DELAY
        self.monitor = MONITOR()
        self.thread_lock = Lock()
        self.is_locked = False
        self.lockfile = f"{os.path.splitext(filename.strip('\\'))[0]}.lock"
        self.timeout = timeout
        self.delay = delay
        self.fd = None
 
    def __del__(self):
        try:
            self.release()
        except Exception as e:
            LOG("FileLock.__del__ release failed: %s" % e, xbmc.LOGDEBUG)
        
    def acquire(self):
        """Acquire a file lock with timeout and delay between retries."""
        with self.thread_lock:
            start_time = time.time()
            while not self.monitor.abortRequested():
                if FileAccess.exists(self.lockfile):
                    if (time.time() - start_time) >= self.timeout:
                        LOG("FileLock Timeout occurred waiting for lock to release.", xbmc.LOGWARNING)
                        break
                    self.monitor.waitForAbort(self.delay)
                    continue
                
                try:
                    self.fd = FileAccess.open(self.lockfile, 'w')
                    self.is_locked = True
                    break
                except Exception as e:
                    LOG(f"FileLock acquiring failed! {e}", xbmc.LOGERROR)
                    break
 
    def release(self):
        if self.is_locked:
            if self.fd and hasattr(self.fd, 'close'):
                self.fd.close()
            self.is_locked = False
            FileAccess.delete(self.lockfile)
 
    def __enter__(self) -> 'FileLock':
        if not self.is_locked:
            self.acquire()
        return self
 
    def __exit__(self, exc_type: Optional[type], exc_val: Optional[BaseException], exc_tb: Any):
        self.release()
