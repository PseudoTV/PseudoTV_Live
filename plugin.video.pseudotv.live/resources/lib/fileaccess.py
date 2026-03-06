#   Copyright (C) 2025 Lunatixz
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
ThreadLock       = Lock()

class FileAccess(object):
    
    @staticmethod
    def dumpJSON(item={}, idnt=None, sortkey=False, separators=(',', ':')):
        try:
            if item:
                if   isinstance(item,(str, bytes)): return item
                elif hasattr(item,'read'):          return json.dump(item)
                elif isinstance(item,dict):         return json.dumps(item, indent=idnt, sort_keys=sortkey, separators=separators)
        except Exception as e: pass
        return ''
        
        
    @staticmethod
    def loadJSON(item=""):
        try:
            if item:
                if   isinstance(item,dict):          return item
                elif hasattr(item,'read'):           return json.load(item)
                elif isinstance(item,(str, bytes)):  return json.loads(item)
        except Exception as e: pass
        return {}
        
        
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
        with FileLock(file), ThreadLock:
            try:
                fle = FileAccess.open(file, 'w')
                fle.write(FileAccess.dumpJSON(data, idnt=4, sortkey=False))
            except Exception as e: log('FileAccess: setJSON failed! %s\nfile = %s'%(e,file), xbmc.LOGERROR)
            finally:
                if hasattr(fle, 'close'): fle.close()
            return True


    @staticmethod
    def setURL(url, file):#todo settingscache?
        with FileLock(file), ThreadLock:
            try:
                contents = requestURL(url)
                fle = FileAccess.open(file, 'w')
                fle.write(contents)
            except Exception as e: log('FileAccess: setURL failed! %s\nurl = %s'%(e,url), xbmc.LOGERROR)
            finally:
                if hasattr(fle, 'close'): fle.close()
        return FileAccess.exists(file)
        
        
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
        if FileAccess.exists(path): xbmcvfs.listdir(path)
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
        log('FileAccess: copying %s to %s'%(orgfilename,newfilename))
        dir, file = os.path.split(newfilename)
        if not FileAccess.exists(dir): FileAccess.makedirs(dir)
        return xbmcvfs.copy(orgfilename, newfilename)


    @staticmethod
    def move(orgfilename, newfilename):
        log('FileAccess: moving %s to %s'%(orgfilename,newfilename))
        if FileAccess.copy(orgfilename, newfilename):
            return FileAccess.delete(orgfilename)
        

    @staticmethod
    def delete(filename):
        try: return xbmcvfs.delete(filename)
        except Exception as e: log('FileAccess: delete failed! %s'%(e), xbmc.LOGERROR)
        
        
    @staticmethod
    def exists(filename):
        if filename.startswith('stack://'):
            try: filename = (filename.split('stack://')[1].split(' , '))[0]
            except Exception as e: log('FileAccess: exists failed! %s'%(e), xbmc.LOGERROR)
        try:
            root, ext = os.path.splitext(filename)
            if not ext and not filename.endswith(("/","\\")): 
                filename = os.path.join(filename,'')
            exists = xbmcvfs.exists(filename)
        except UnicodeDecodeError:
            exists = os.path.exists(xbmcvfs.translatePath(filename))
        log('FileAccess: filename = %s, exists = %s'%(filename,exists))
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
    def rename(path, newpath):       
        log("FileAccess: rename %s to %s"%(path,newpath))
        if not FileAccess.exists(path):
            return False
        
        try:
            if xbmcvfs.rename(path, newpath):
                return True
        except Exception as e: 
            log("FileAccess: rename, failed! %s"%(e), xbmc.LOGERROR)

        try:
            if FileAccess.move(path, newpath):
                return True
        except Exception as e: 
            log("FileAccess: move, failed! %s"%(e), xbmc.LOGERROR)
           
        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                log("FileAccess: Modifying name")
                if path[0:6].lower() == 'smb://':
                    path = '\\\\' + path[6:]

                if newpath[0:6].lower() == 'smb://':
                    newpath = '\\\\' + newpath[6:]        
        
        if not os.path.exist(xbmcvfs.translatePath(path)):
            return False
        
        try:
            log("FileAccess: os.rename")
            os.rename(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath))
            return True
        except Exception as e: 
            log("FileAccess: os.rename, failed! %s"%(e), xbmc.LOGERROR)
 
        try:
            log("FileAccess: shutil.move")
            shutil.move(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath))
            return True
        except Exception as e: 
            log("FileAccess: shutil.move, failed! %s"%(e), xbmc.LOGERROR)

        log("FileAccess: OSError")
        raise OSError()


    @staticmethod
    def removedirs(path, force=True):
        if len(path) == 0: return False
        elif(xbmcvfs.exists(path)):
            return True
        try: 
            success = xbmcvfs.rmdir(dir, force=force)
            if success: return True
            else: raise
        except Exception: 
            try: 
                os.rmdir(xbmcvfs.translatePath(path))
                if os.path.exists(xbmcvfs.translatePath(path)):
                    return True
            except Exception: log("FileAccess: removedirs failed!", xbmc.LOGERROR)
            return False
            
            
    @staticmethod
    def makedirs(directory):
        try:  
            os.makedirs(xbmcvfs.translatePath(directory))
            return os.path.exists(xbmcvfs.translatePath(directory))
        except Exception:
            return FileAccess._makedirs(directory)
            
            
    @staticmethod
    def _makedirs(path):
        if len(path) == 0:
            return False

        if(xbmcvfs.exists(path)):
            return True

        success = xbmcvfs.mkdir(path)
        if success == False:
            if path == os.path.dirname(xbmcvfs.translatePath(path)): return False
            if FileAccess._makedirs(os.path.dirname(xbmcvfs.translatePath(path))):
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
        try:    return self.currentFile.read(bytes)
        except Exception: return self.currentFile.readBytes(bytes)
        
        
    def readBytes(self, bytes=0):
        return self.currentFile.readBytes(bytes)
        

    def write(self, data):
        if isinstance(data,bytes):
            data = data.decode(DEFAULT_ENCODING, 'backslashreplace')
        return self.currentFile.write(data)
        
        
    def close(self):
        return self.currentFile.close()


    def seek(self, bytes, offset=1):
        return self.currentFile.seek(bytes, offset)


    def size(self):
        return self.currentFile.size()


    def tell(self):
        try:    return self.currentFile.tell()
        except Exception: return self.currentFile.seek(0, 1)
        

    def readlines(self):
        try:    return ''.join(list(self.readline())).split('\n')
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
        self.release()
        
        
    def acquire(self):
        with self.thread_lock:
            start_time = time.time()
            while not self.monitor.abortRequested():
                try:
                    self.fd = FileAccess.open(self.lockfile, 'w')
                    self.is_locked = True #moved to ensure tag only when locked
                    break
                except OSError as e:
                    if e.errno != errno.EEXIST:                    return log("FileLock: Could not create lock.\n%s"%(e), xbmc.LOGERROR)
                    if self.timeout is None:                       return log("FileLock: Could not acquire lock.\n%s"%(e), xbmc.LOGERROR)
                    if (time.time() - start_time) >= self.timeout: return log("FileLock: Timeout occurred.\n%s"%(e), xbmc.LOGERROR)
                if self.monitor.waitForAbort(self.delay): break
 
 
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