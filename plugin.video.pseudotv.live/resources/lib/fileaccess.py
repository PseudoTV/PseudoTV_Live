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

from variables   import *
from logger      import log

#constants 
DEFAULT_ENCODING = "utf-8"

class FileAccess(object):
    
    @staticmethod
    def _getMD5(data):
        if not isinstance(data, (str, bytes, bytearray)):
            data = FileAccess.dumpJSON(data, sortkey=True)
        if isinstance(data, str): data = data.encode(DEFAULT_ENCODING)
        return hashlib.md5(data).hexdigest()


    @staticmethod
    def _encodeString(data=''):
        if not data: return ""
        try:
            normalized_str = FileAccess.dumpJSON(data)
            compressed = zlib.compress(normalized_str.encode(DEFAULT_ENCODING), level=1)
            return base64.urlsafe_b64encode(compressed).decode('ascii')
        except Exception as e: log(f"_encodeString failed! {e}", xbmc.LOGERROR)
        return ""


    @staticmethod
    def _decodeString(data=''):
        if not data: return ""
        try:
            if isinstance(data, str): data = data.encode('ascii')
            padded_data = data + b'=' * (-len(data) % 4)
            raw_bytes = base64.urlsafe_b64decode(padded_data)
            decompressed_str = zlib.decompress(raw_bytes).decode(DEFAULT_ENCODING)
            return FileAccess.loadJSON(decompressed_str)
        except Exception as e: log(f"_decodeString failed! {e}", xbmc.LOGERROR)
        return ""
            
            
    @staticmethod
    def dumpPICKLE(item={}):
        try:
            if not item:                               return b""
            elif hasattr(item,'write'):                return pickle.dump(None, item)
            elif isinstance(item, (bytes, bytearray)): return item
            return pickle.dumps(item, protocol=4)
        except Exception as e: log('FileAccess: dumpPICKLE failed! %s'%(e), xbmc.LOGERROR)
        return b""
        
        
    @staticmethod
    def loadPICKLE(item=""):
        try:        
            if not item:                return None
            elif hasattr(item,'read'):  return pickle.load(item)
            elif isinstance(item, str): item = item.encode('latin-1')
            return pickle.loads(item)
        except pickle.UnpicklingError: pass
        except Exception as e: log('FileAccess: loadPICKLE failed! %s'%(e), xbmc.LOGERROR)
        return None
        
        
    @staticmethod
    def dumpJSON(item=None, idnt=None, sortkey=False, separators=(',', ':')):
        try:
            if item is None: return '{}'
            if isinstance(item, (str, bytes, bytearray)): return item.decode('utf-8') if isinstance(item, (bytes, bytearray)) else item
            if not hasattr(item,'write'): return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
            json.dump(None, item, indent=idnt, sort_keys=sortkey, separators=separators)
        except (TypeError, ValueError): return '{}'
        except Exception as e: log('FileAccess: dumpJSON failed! %s'%(e), xbmc.LOGERROR)
        return '{}'
            
        
    @staticmethod
    def loadJSON(item=""):
        try:
            if not item: return {}
            if not hasattr(item,'read'): return json.loads(item)
            json.load(item)
        except (json.JSONDecodeError, TypeError): return item
        except Exception as e: log('FileAccess: loadJSON failed! %s' % (e), xbmc.LOGERROR)
        return item
        
        
    @staticmethod
    def getJSON(file):
        data = {}
        try: 
            fle  = FileAccess.open(file,'r')
            data = FileAccess.loadJSON(fle.read())
        except Exception as e: log('FileAccess: getJSON failed! %s\nfile = %s'%(e,file), xbmc.LOGERROR)
        finally: 
            if hasattr(fle, 'close'): fle.close()
        return data


    @staticmethod
    def setJSON(file, data):
        with FileLock(file):
            try:
                fle = FileAccess.open(file, 'w')
                fle.write(FileAccess.dumpJSON(data, idnt=4, sortkey=False))
            except Exception as e: log('FileAccess: setJSON failed! %s\nfile = %s'%(e,file), xbmc.LOGERROR)
            finally:
                if hasattr(fle, 'close'): fle.close()
            return True


    @staticmethod
    def setURL(url, file):
        try:
            req = urllib.request.Request(url, headers=HEADER)
            with urllib.request.urlopen(req) as response:
                with FileAccess.stream(file, 'w') as f:
                    while not MONITOR().abortRequested():
                        chunk = response.read(8192)
                        if not chunk: break
                        f.write(chunk)
            return True
        except Exception as e: log('FileAccess: setURL failed! %s\nfile = %s'%(e,file), xbmc.LOGERROR)
        return False


    @staticmethod
    def open(filename, mode, encoding=DEFAULT_ENCODING):
        # monitor    = MONITOR()
        # start_time = time.time()
        # lock_path  = '%s.lock' % (os.path.splitext(filename.strip('\\'))[0])
        # while not monitor.abortRequested() and FileAccess.exists(lock_path):
            # if not FileAccess.exists(lock_path): break
            # elif (time.time() - start_time) >= LOCK_MAX_FILE_TIMEOUT:
                # log(f"FileAccess: Timeout waiting for lock to clear on {filename}", xbmc.LOGWARNING)
                # break
            # elif monitor.waitForAbort(LOCK_MAX_FILE_DELAY): break
        # del monitor
        
        try:
            return VFSFile(filename, mode)
        except UnicodeDecodeError:
            return FileAccess.open(filename, mode, encoding)

                
    @staticmethod
    @contextmanager
    def stream(filename, mode='r', encoding=DEFAULT_ENCODING):
        """
        A context manager/decorator that opens a file stream, 
        yields the file object, and ensures it's closed.
        
        with FileAccess.stream("special://profile/settings.xml") as f:
            content = f.read()
        """
        f = FileAccess.open(filename, mode, encoding)
        try: yield f
        finally: f.close()


    @staticmethod
    def _getFolderPath(path):
        head, tail  = os.path.split(path)
        last_folder = os.path.basename(head)
        return os.path.join(last_folder, tail)
        
        
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
        return [],[]


    @staticmethod
    def mkdirs(path):
        if not path.endswith(("/","\\")): path = "%s/"%(path)
        return xbmcvfs.mkdirs(path)


    @staticmethod
    def translatePath(path):
        if '@' in path: path = path.split('@')[1]
        return xbmcvfs.translatePath(path)


    @staticmethod
    def copyFolder(src, dir, dia=None, move=False):
        log('FileAccess: copyFolder %s to %s'%(src,dir))
        if not FileAccess.exists(dir): FileAccess.makedirs(dir)
        if not dia is None: dia = dia._updateProgress(dia, 0, message='%s\n%s'%(LANGUAGE(32051),src))

        subs, files = FileAccess.listdir(src)
        for fidx, file in enumerate(files):
            if not dia is None: dia = dia._updateProgress(dia, int(fidx*100)//len(files), message=f'copying {file} {int(fidx*100)//len(files)}%\n{fidx}/{len(files)}')
            if move: FileAccess.move(os.path.join(src, file), os.path.join(dir, file))
            else:    FileAccess.copy(os.path.join(src, file), os.path.join(dir, file))
        
        for sidx, sub in enumerate(subs):
            if not dia is None: dia = dia._updateProgress(dia, int(sidx*100)//len(subs), message=f'copying {sub} {int(sidx*100)//len(subs)}%\n{sidx}/{len(subs)}')
            dia = FileAccess.copyFolder(os.path.join(src, sub), os.path.join(dir, sub), dia, move)
        return dia
        

    @staticmethod
    def copy(orgfilename, newfilename):
        if not FileAccess.exists(orgfilename): return False
        dir, file = os.path.split(newfilename)
        if not FileAccess.exists(dir): FileAccess.makedirs(dir)
        elif   FileAccess.exists(newfilename): FileAccess.delete(newfilename) #todo prompt to delete existing.
        log('FileAccess: copying %s to %s'%(orgfilename,newfilename))
        return xbmcvfs.copy(orgfilename, newfilename)


    @staticmethod
    def move(orgfilename, newfilename):
        log('FileAccess: moving %s to %s'%(orgfilename,newfilename))
        if FileAccess.copy(orgfilename, newfilename):
            return FileAccess.delete(orgfilename)
        

    @staticmethod
    def delete(filename):
        try: 
            if not FileAccess.exists(filename): return False
            xbmcvfs.delete(filename)
        except Exception as e: 
            log('FileAccess: delete failed! %s'%(e), xbmc.LOGERROR)
            os.remove(FileAccess.translatePath(filename))
        return FileAccess.exists(filename)
        
        
    @staticmethod
    def exists(path):
        filepath = path
        if filepath.startswith('stack://'):
            try: filepath = (filepath.split('stack://')[1].split(' , '))[0]
            except Exception: pass
        exists = xbmcvfs.exists(filepath)
        if not exists and not filepath.endswith('\\'):
            filepath = os.path.join(filepath,'')
            exists = os.path.exists(filepath)
            if not exists and not filepath.endswith('\\'):
                filepath = FileAccess.translatePath(filepath)
                exists = os.path.exists(filepath)
        log('FileAccess: path = %s, exists = %s'%(path,exists))
        return exists


    @staticmethod
    def openSMB(filename, mode, encoding=DEFAULT_ENCODING):
        fle = 0
        if os.name.lower() == 'nt':
            newname = '\\\\' + filename[6:]
            try:    fle = codecs.open(newname, mode, encoding)
            except Exception: fle = 0
        return fle


    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
            return FileAccess.exists(filename)
        return False


    @staticmethod
    def rename(path, newpath, force=True):       
        log("FileAccess: rename %s to %s, force = %s"%(path,newpath,force))
        if not FileAccess.exists(path): return False
        try:
            if not FileAccess.exists(path):   return False
            if xbmcvfs.rename(path, newpath): return FileAccess.exists(newpath)
        except Exception as e: 
            log("FileAccess: rename, failed! %s"%(e), xbmc.LOGERROR)
            
        try:#failed rename try moving.
            if FileAccess.move(path, newpath): return True
        except Exception as e: 
            log("FileAccess: move, failed! %s"%(e), xbmc.LOGERROR)
           
        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                log("FileAccess: Modifying name")
                if path[0:6].lower() == 'smb://': path = '\\\\' + path[6:]
                if newpath[0:6].lower() == 'smb://': newpath = '\\\\' + newpath[6:]      
        if not os.path.exists(FileAccess.translatePath(path)): return False
        else:
            try:
                log("FileAccess: os.rename")
                os.rename(FileAccess.translatePath(path), FileAccess.translatePath(newpath))
                return True
            except Exception as e: 
                log("FileAccess: os.rename, failed! %s"%(e), xbmc.LOGERROR)
     
            try:
                log("FileAccess: shutil.move")
                shutil.move(FileAccess.translatePath(path), FileAccess.translatePath(newpath))
                return True
            except Exception as e: 
                log("FileAccess: shutil.move, failed! %s"%(e), xbmc.LOGERROR)
        log("FileAccess: OSError")
        raise False


    @staticmethod
    def removedirs(path, force=True):
        log("FileAccess: removedirs, path = %s, force = %s"%(path, force))
        if not path: return False
        elif(xbmcvfs.exists(path)):
            return True
        try: 
            success = xbmcvfs.rmdir(dir, force=force)
            if success: return True
            else: raise
        except Exception: 
            try: 
                os.rmdir(FileAccess.translatePath(path))
                if not os.path.exists(FileAccess.translatePath(path)): return True
            except Exception: log("FileAccess: removedirs failed!", xbmc.LOGERROR)
            return False
            
            
    @staticmethod
    def makedirs(path):
        try:  
            log("FileAccess: makedirs, path = %s"%(path))
            os.makedirs(FileAccess.translatePath(path))
            return os.path.exists(FileAccess.translatePath(path))
        except Exception:
            return FileAccess._makedirs(path)
            
            
    @staticmethod
    def _makedirs(path):
        if not path: return False
        if(xbmcvfs.exists(path)): return True
        if not xbmcvfs.mkdir(path):
            if path == os.path.dirname(FileAccess.translatePath(path)): return False
            if FileAccess._makedirs(os.path.dirname(FileAccess.translatePath(path))):
                return xbmcvfs.mkdir(path)
        return xbmcvfs.exists(path)


class VFSFile(object):
    monitor = MONITOR()
    
    def __init__(self, filename, mode):
        if mode == 'w':
            if not FileAccess.exists(filename): 
                FileAccess.makedirs(os.path.split(filename)[0])
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:
            self.currentFile = xbmcvfs.File(filename, 'r')
        log("VFSFile: __init__, Opening %s"%filename, xbmc.LOGDEBUG)

        if self.currentFile == None:
            log("VFSFile: __init__, Couldnt open %s"%filename, xbmc.LOGERROR)


    def read(self, bytes=0):
        try:              return self.currentFile.read(bytes)
        except Exception: return self.currentFile.readBytes(bytes)
        
        
    def readBytes(self, bytes=0):
        return self.currentFile.readBytes(bytes)
        
        
    def write(self, buffer):
        if not isinstance(buffer, (bytes, bytearray)):
            buffer = buffer.encode(DEFAULT_ENCODING, 'backslashreplace')
        return self.currentFile.write(buffer)
        
        
    def close(self):
        return self.currentFile.close()


    def seek(self, bytes, offset=1):
        return self.currentFile.seek(bytes, offset)


    def size(self):
        return self.currentFile.size()


    def tell(self):
        try:              return self.currentFile.tell()
        except Exception: return self.currentFile.seek(0, 1)
        

    def readlines(self):
        try:              return ''.join(list(self.readline())).split('\n')
        except Exception: return self.read().split('\n')


    def readline(self):
        try:
            for line in self.read_in_chunks():
                yield line
        except Exception as e:
            log("VFSFile: readline, failed! %s"%e, xbmc.LOGERROR)
        

    def read_in_chunks(self, chunk_size=1024):
        """Lazy function (generator) to read a file piece by piece."""
        while not self.monitor.abortRequested():
            data = self.read(chunk_size)
            if not data: break
            yield data


class FileLock(object):
    monitor = MONITOR()
    thread_lock = Lock()
    
    # https://github.com/dmfrey/FileLock
    """ A file locking mechanism that has context-manager support so 
        you can use it in a with statement. This should be relatively cross
        compatible as it doesn't rely on msvcrt or fcntl for the locking.
    """
 
    def __init__(self, filename, timeout=LOCK_MAX_FILE_TIMEOUT, delay: float=LOCK_MAX_FILE_DELAY):
        self.is_locked = False
        self.lockfile  = '%s.lock' % (os.path.splitext(filename.strip('\\'))[0])
        self.timeout   = timeout
        self.delay     = delay
        self.fd        = None
 
 
    def __del__(self):
        try: self.release()
        except Exception: pass
        
        
    def acquire(self):
        with self.thread_lock:
            start_time = time.time()
            while not self.monitor.abortRequested():
                try:
                    if not self.is_locked and FileAccess.exists(self.lockfile):
                        FileAccess.delete(self.lockfile)
                    else:
                        self.fd = FileAccess.open(self.lockfile, 'w')
                        self.is_locked = True #moved to ensure tag only when locked
                        break
                except Exception as e: log("FileLock, Failed! %s"%(e), xbmc.LOGERROR)
                if self.monitor.waitForAbort(self.delay): 
                    self.log("FileLock: Could not acquire lock.")
                    break
                elif (time.time() - start_time) >= self.timeout: 
                    self.log("FileLock: Timeout occurred.")
                    break
     
 
    def release(self):
        if self.is_locked: 
            if hasattr(self.fd, 'close'): 
                self.fd.close()
            self.is_locked = False
            FileAccess.delete(self.lockfile)
 
 
    def __enter__(self):
        if not self.is_locked: 
            self.acquire()
        return self
 
 
    def __exit__(self, type, value, traceback):
        self.release()