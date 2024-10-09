#   Copyright (C) 2024 Lunatixz
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

from globals    import *

#constants 
DEFAULT_ENCODING           = "utf-8"
FILE_LOCK_MAX_FILE_TIMEOUT = 10
FILE_LOCK_NAME             = "pseudotv"

#variables
DEBUG_ENABLED       = REAL_SETTINGS.getSetting('Enable_Debugging').lower() == 'true'
       
def log(event, level=xbmc.LOGDEBUG):
    if not DEBUG_ENABLED and level != xbmc.LOGERROR: return #todo use debug level filter
    if level == xbmc.LOGERROR: event = '%s\n%s'%(event,traceback.format_exc())
    xbmc.log('%s-%s-%s'%(ADDON_ID,ADDON_VERSION,event),level)
    
class FileAccess:
    @staticmethod
    def open(filename, mode, encoding=DEFAULT_ENCODING):
        fle = 0
        log("FileAccess: trying to open %s"%filename)
        try: return VFSFile(filename, mode)
        except UnicodeDecodeError: return FileAccess.open(filename, mode, encoding)
        return fle


    @staticmethod
    def listdir(path):
        return xbmcvfs.listdir(path)


    @staticmethod
    def translatePath(path):
        if '@' in path: path = path.split('@')[1]
        return xbmcvfs.translatePath(path)


    @staticmethod
    def copyFolder(path, newpath, verbose=None):
        log('FileAccess: copying folder %s to %s'%(path,newpath))
        return shutil.copytree(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath), copy_function=verbose)


    @staticmethod
    def moveFolder(path, newpath):
        log('FileAccess: moving folder %s to %s'%(path,newpath))
        return shutil.move(xbmcvfs.translatePath(path), xbmcvfs.translatePath(newpath))


    @staticmethod
    def copy(orgfilename, newfilename):
        log('FileAccess: copying %s to %s'%(orgfilename,newfilename))
        dir, file = os.path.split(newfilename)
        if not FileAccess.exists(dir): FileAccess.makedirs(dir)
        return xbmcvfs.copy(orgfilename, newfilename)


    @staticmethod
    def move(orgfilename, newfilename):
        log('FileAccess: moving %s to %s'%(orgfilename,newfilename))
        if xbmcvfs.copy(orgfilename, newfilename):
            return xbmcvfs.delete(orgfilename)
        return False
        

    @staticmethod
    def delete(filename):
        return xbmcvfs.delete(filename)
        
        
    @staticmethod
    def exists(filename):
        if filename.startswith('stack://'):
            try: filename = (filename.split('stack://')[1].split(' , '))[0]
            except Exception as e: log('FileAccess: exists failed! %s'%(e), xbmc.LOGERROR)
        try:
            return xbmcvfs.exists(filename)
        except UnicodeDecodeError:
            return os.path.exists(xbmcvfs.translatePath(filename))
        return False


    @staticmethod
    def openSMB(filename, mode, encoding=DEFAULT_ENCODING):
        fle = 0
        if os.name.lower() == 'nt':
            newname = '\\\\' + filename[6:]
            try:    fle = codecs.open(newname, mode, encoding)
            except: fle = 0
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
        except: 
            try: 
                os.rmdir(xbmcvfs.translatePath(path))
                if os.path.exists(xbmcvfs.translatePath(path)):
                    return True
            except: log("FileAccess: removedirs failed!", xbmc.LOGERROR)
            return False
            
            
    @staticmethod
    def makedirs(directory):
        try:  
            os.makedirs(xbmcvfs.translatePath(directory))
            return os.path.exists(xbmcvfs.translatePath(directory))
        except:
            return FileAccess._makedirs(directory)
            
            
    @staticmethod
    def _makedirs(path):
        if len(path) == 0:
            return False

        if(xbmcvfs.exists(path)):
            return True

        success = xbmcvfs.mkdir(path)
        if success == False:
            if path == os.path.dirname(xbmcvfs.translatePath(path)):
                return False

            if FileAccess._makedirs(os.path.dirname(xbmcvfs.translatePath(path))):
                return xbmcvfs.mkdir(path)
        return xbmcvfs.exists(path)


class VFSFile:
    def __init__(self, filename, mode):
        log("VFSFile: trying to open %s"%filename)
        if mode == 'w':
            if not FileAccess.exists(filename): 
                FileAccess.makedirs(os.path.split(filename)[0])
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:
            self.currentFile = xbmcvfs.File(filename, 'r')
        log("VFSFile: Opening %s"%filename, xbmc.LOGDEBUG)

        if self.currentFile == None:
            log("VFSFile: Couldnt open %s"%filename, xbmc.LOGERROR)


    def read(self, bytes=0):
        try:    return self.currentFile.read(bytes)
        except: return self.currentFile.readBytes(bytes)
        
        
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


    def readlines(self):
        return self.currentFile.read().split('\n')


    def readline(self):
        return self.currentFile.read().split('\n')


    def tell(self):
        try:    return self.currentFile.tell()
        except: return self.currentFile.seek(0, 1)
        

class FileLock(object):
    # https://github.com/dmfrey/FileLock
    """ A file locking mechanism that has context-manager support so 
        you can use it in a with statement. This should be relatively cross
        compatible as it doesn't rely on msvcrt or fcntl for the locking.
    """
 
    def __init__(self, file_name=FILE_LOCK_NAME, timeout=FILE_LOCK_MAX_FILE_TIMEOUT, delay: float=0.5):
        """ Prepare the file locker. Specify the file to lock and optionally
            the maximum timeout and the delay between each attempt to lock.
        """
        if timeout is not None and delay is None:
            raise ValueError("If timeout is not None, then delay must not be None.")
            
        self.is_locked = False
        self.file_name = file_name
        self.lockpath  = self.checkpath()
        self.lockfile  = os.path.join(self.lockpath, "%s.lock" % self.file_name)
        self.timeout   = timeout
        self.delay     = delay
 
 
    def checkpath(self):
        lockpath = os.path.join(REAL_SETTINGS.getSetting('User_Folder'))
        if not FileAccess.exists(lockpath):
            if FileAccess.makedirs(lockpath):
                return lockpath
            else:#fallback to local folder.
                #todo log error with lock path
                lockpath = os.path.join(SETTINGS_LOC,'cache')
                if not FileAccess.exists(lockpath):
                    FileAccess.makedirs(lockpath)
        return lockpath
        
        
    def acquire(self):
        """ Acquire the lock, if possible. If the lock is in use, it check again
            every `wait` seconds. It does this until it either gets the lock or
            exceeds `timeout` number of seconds, in which case it throws 
            an exception.
        """
        start_time = time.time()
        while not xbmc.Monitor().abortRequested():
            if xbmc.Monitor().waitForAbort(self.delay): break
            else:
                try:
                    self.fd = FileAccess.open(self.lockfile, 'w')
                    self.is_locked = True #moved to ensure tag only when locked
                    break;
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise
                    if self.timeout is None:
                        raise FileLockException("Could not acquire lock on {}".format(self.file_name))
                    if (time.time() - start_time) >= self.timeout:
                        raise FileLockException("Timeout occured.")
 
 
    def release(self):
        """ Get rid of the lock by deleting the lockfile. 
            When working in a `with` statement, this gets automatically 
            called at the end.
        """
        if self.is_locked:
            self.fd.close()
            self.is_locked = False
 
 
    def __enter__(self):
        """ Activated when used in the with statement. 
            Should automatically acquire a lock to be used in the with block.
        """
        if not self.is_locked:
            self.acquire()
        return self
 
 
    def __exit__(self, type, value, traceback):
        """ Activated at the end of the with statement.
            It automatically releases the lock if it isn't locked.
        """
        if self.is_locked:
            self.release()
 
 
    def __del__(self):
        """ Make sure that the FileLock instance doesn't leave a lockfile
            lying around.
        """
        self.release()
        FileAccess.delete(self.lockfile)
        

class FileLockException(Exception):
    pass