#   Copyright (C) 2015 Jason Anderson, Kevin S. Graer
#
#
# This file is part of PseudoTV Live.
#
# PseudoTV is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PseudoTV is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PseudoTV.  If not, see <http://www.gnu.org/licenses/>.

import xbmc, xbmcvfs
import subprocess, os, shutil, base64
import time, threading
import random, os, codecs
import Globals

VFS_AVAILABLE = True
FILE_LOCK_MAX_FILE_TIMEOUT = 13
FILE_LOCK_NAME = "FileLock.dat"

class FileAccess:
    @staticmethod
    def log(msg, level = xbmc.LOGDEBUG):
        Globals.log('FileAccess: ' + msg, level)
    
    
    @staticmethod
    def open(filename, mode, encoding = "utf-8"):
        fle = 0
        FileAccess.log("trying to open " + filename)
        try:
            return VFSFile(filename, mode)
        except UnicodeDecodeError:
            return FileAccess.open(ascii(filename), mode, encoding)
        return fle


    @staticmethod
    def listdir(fle):
        FileAccess.log('listdir ' + fle)
        try:
            results = xbmcvfs.listdir(os.path.join(fle,''))
            return results
        except:
            return [],[]
            
    @staticmethod
    def mkdirs(fle):
        FileAccess.log('mkdirs ' + fle)
        try:
            xbmcvfs.mkdirs(fle)
            return True
        except:
            return False

    @staticmethod
    def delete(fle):
        FileAccess.log('deleting ' + fle)
        try:
            xbmcvfs.delete(fle)
            return True
        except:
            FileAccess._delete(fle)
           
    def _delete(fle):
        try:
            os.remove(xbmc.translatePath(fle))
            return True
        except:
            return False
            
            
    @staticmethod
    def copy(orgfilename, newfilename):
        FileAccess.log('copying ' + orgfilename + ' to ' + newfilename)
        xbmcvfs.copy(orgfilename, newfilename)
        return True


    @staticmethod
    def exists(filename):
        try:
            return xbmcvfs.exists(filename)
        except UnicodeDecodeError:
            return FileAccess.exists(ascii(filename))
        return False


    @staticmethod
    def _openSMB(filename, mode, encoding = "utf-8"):
        fle = 0

        if os.name.lower() == 'nt':
            newname = '\\\\' + filename[6:]
        elif os.name.lower() == 'posix':
            newname = '//' + filename[6:]
            return mountPosixSMB(newname)
        try:
            fle = codecs.open(newname, mode, encoding)
        except Exception,e:
            fle = 0
        return fle
        
        
    @staticmethod
    def mountPosixSMB(filename):
        if not os.path.exists(Globals.MOUNT_LOC):
            os.makedirs(Globals.MOUNT_LOC)

        if Globals.mountedFS == True:
            newfilename = xbmc.translatePath(os.path.join(Globals.MOUNT_LOC, os.path.split(filename)[1]))

            if os.path.exists(newfilename):
                return newfilename

            pipe = os.popen("umount \"" + Globals.MOUNT_LOC + "\"")
            Globals.mountedFS = False

        newfilename = mountFs(filename, 'cifs')

        if os.path.exists(newfilename):
            Globals.mountedFS = True
            return newfilename

        newfilename = mountFs(filename, 'smbfs')

        if os.path.exists(newfilename):
            Globals.mountedFS = True
            return newfilename

        return filename

        
    @staticmethod
    def mountFs(filename, fstype):
        dirpart, filename = os.path.split(filename)
        pipe = os.popen("mount -t " + fstype + " \"" + dirpart + "\" \"" + Globals.MOUNT_LOC + "\"")
        newfilename = xbmc.translatePath(os.path.join(Globals.MOUNT_LOC, filename))

        if os.path.exists(newfilename):
            return newfilename

        # Only try adding "Guest" if there is no username already there
        if dirpart.find('@') == -1:
            dirpart = "//Guest:@" + dirpart[2:]
            pipe = os.popen("mount -t " + fstype + " \"" + dirpart + "\" \"" + Globals.MOUNT_LOC + "\"")

            if os.path.exists(newfilename):
                return newfilename

        # Seperate the username and password and try that
        username = dirpart[2:dirpart.find(':')]
        password = dirpart[dirpart.find(':') + 1:dirpart.find('@')]
        dirpart = '//' + dirpart[dirpart.find('@') + 1:]
        pipe = os.popen("mount -t cifs \"" + dirpart + "\" \"" + Globals.MOUNT_LOC + "\" -o username=" + username + ",password=" + password)
        return newfilename
    
    
    @staticmethod
    def finish():
        if Globals.mountedFS == True:
            pipe = os.popen("umount \"" + Globals.MOUNT_LOC + "\"")
            Globals.mountedFS = False
            
            
    @staticmethod
    def existsSMB(filename):
        if os.name.lower() == 'nt':
            filename = '\\\\' + filename[6:]
            return FileAccess.exists(filename)
        return False


    @staticmethod
    def rename(path, newpath):
        FileAccess.log("rename " + path + " to " + newpath)

        try:
            if xbmcvfs.rename(path, newpath):
                return True
        except Exception,e:
            pass

        if path[0:6].lower() == 'smb://' or newpath[0:6].lower() == 'smb://':
            if os.name.lower() == 'nt':
                FileAccess.log("Modifying name")
                if path[0:6].lower() == 'smb://':
                    path = '\\\\' + path[6:]

                if newpath[0:6].lower() == 'smb://':
                    newpath = '\\\\' + newpath[6:]

        try:
            os.rename(path, newpath)
            FileAccess.log("os.rename")
            return True
        except Exception,e:
            pass

        try:
            shutil.move(path, newpath)
            FileAccess.log("shutil.move")
            return True
        except Exception,e:
            pass

        FileAccess.log("OSError")
        raise OSError()


    @staticmethod
    def makedirs(directory):
        try:
            os.makedirs(directory)
        except Exception,e:
            FileAccess._makedirs(directory)


    @staticmethod
    def _makedirs(path):
        if len(path) == 0:
            return False

        if(xbmcvfs.exists(path)):
            return True

        success = xbmcvfs.mkdir(path)

        if success == False:
            if path == os.path.dirname(path):
                return False

            if FileAccess._makedirs(os.path.dirname(path)):
                return xbmcvfs.mkdir(path)
        return xbmcvfs.exists(path)
        
        
class VFSFile:
    def __init__(self, filename, mode):
        Globals.log("VFSFile: trying to open " + filename)
        
        if mode == 'w':
            self.currentFile = xbmcvfs.File(filename, 'wb')
        else:        
            self.currentFile = xbmcvfs.File(filename)
        Globals.log("VFSFile: Opening " + filename, xbmc.LOGDEBUG)
        
        if self.currentFile == None:
            Globals.log("VFSFile: Couldnt open " + filename, xbmc.LOGERROR)


    def read(self, bytes):
        return self.currentFile.read(bytes)
        
        
    def write(self, data):
        if isinstance(data, unicode):
            data = bytearray(data, "utf-8")
            data = bytes(data)
    
        return self.currentFile.write(data)
        
        
    def close(self):
        return self.currentFile.close()
        
        
    def seek(self, bytes, offset):
        return self.currentFile.seek(bytes, offset)
        
        
    def size(self):
        loc = self.currentFile.size()
        return loc
        
        
    def readlines(self):
        return self.currentFile.read().split('\n')    
        
        
    def writelines(self):
        return self.currentFile.write().split('\n')
        
        
    def tell(self):
        loc = self.currentFile.seek(0, 1)
        return loc

        
class FileLock:
    def __init__(self):
        random.seed()
        FileAccess.makedirs(Globals.LOCK_LOC)
        self.lockFileName = Globals.LOCK_LOC + FILE_LOCK_NAME
        self.lockedList = []
        self.refreshLocksTimer = threading.Timer(4.0, self.refreshLocks)
        self.refreshLocksTimer.name = "RefreshLocks"
        self.refreshLocksTimer.start()
        self.isExiting = False
        self.grabSemaphore = threading.BoundedSemaphore()
        self.listSemaphore = threading.BoundedSemaphore()
        self.log("FileLock instance")


    def close(self):
        self.log("close")
        self.isExiting = True

        if self.refreshLocksTimer.isAlive():
            try:
                self.refreshLocksTimer.cancel()
                self.refreshLocksTimer.join()
            except Exception,e:
                pass

        for item in self.lockedList:
            self.unlockFile(item)


    def log(self, msg, level = xbmc.LOGDEBUG):
        Globals.log('FileLock: ' + msg, level)


    def refreshLocks(self):
        for item in self.lockedList:
            if self.isExiting:
                self.log("IsExiting")
                return False

            self.lockFile(item, True)

        self.refreshLocksTimer = threading.Timer(4.0, self.refreshLocks)

        if self.isExiting == False:
            self.refreshLocksTimer.name = "RefreshLocks"
            self.refreshLocksTimer.start()
            return True

        return False


    def lockFile(self, filename, block = False):
        self.log("lockFile " + filename)
        curval = -1
        attempts = 0
        fle = 0
        filename = filename.lower()
        locked = True
        lines = []

        while(locked == True and attempts < FILE_LOCK_MAX_FILE_TIMEOUT):
            locked = False

            if curval > -1:
                self.releaseLockFile()
                self.grabSemaphore.release()
                time.sleep(1)

            self.grabSemaphore.acquire()

            if self.grabLockFile() == False:
                self.grabSemaphore.release()
                return False

            try:
                fle = FileAccess.open(self.lockName, "r")
            except Exception,e:
                self.log("Unable to open the lock file")
                self.releaseLockFile()
                self.grabSemaphore.release()
                return False

            lines = fle.readlines()
            fle.close()
            val = self.findLockEntry(lines, filename)

            # If the file is locked:
            if val > -1:
                locked = True

                # If we're the ones that have the file locked, allow overriding it
                for item in self.lockedList:
                    if item == filename:
                        locked = False
                        block = False
                        break

                if curval == -1:
                    curval = val
                else:
                    if curval == val:
                        attempts += 1
                    else:
                        if block == False:
                            self.releaseLockFile()
                            self.grabSemaphore.release()
                            self.log("File is locked")
                            return False

                        curval = val
                        attempts = 0

        self.log("File is unlocked")
        self.writeLockEntry(lines, filename)
        self.releaseLockFile()
        existing = False

        for item in self.lockedList:
            if item == filename:
                existing = True
                break

        if existing == False:
            self.lockedList.append(filename)

        self.grabSemaphore.release()
        return True


    def grabLockFile(self):
        self.log("grabLockFile")

        # Wait a maximum of 20 seconds to grab file-lock file.  This long
        # timeout should help prevent issues with an old cache.
        for i in range(40):
            # Cycle file names in case one of them is sitting around in the directory
            self.lockName = Globals.LOCK_LOC + str(random.randint(1, 60000)) + ".lock"

            try:
                FileAccess.rename(self.lockFileName, self.lockName)
                fle = FileAccess.open(self.lockName, 'r')
                fle.close()
                return True
            except Exception,e:
                time.sleep(0.5)

        self.log("Creating lock file")
        
        try:
            fle = FileAccess.open(self.lockName, 'w')
            fle.close()
        except Exception,e:
            self.log("Unable to create a lock file")
            return False

        return True


    def releaseLockFile(self):
        self.log("releaseLockFile")

        # Move the file back to the original lock file name
        try:
            FileAccess.rename(self.lockName, self.lockFileName)
        except Exception,e:
            self.log("Unable to rename the file back to the original name")
            return False

        return True


    def writeLockEntry(self, lines, filename, addentry = True):
        self.log("writeLockEntry")
        # Make sure the entry doesn't exist.  This should only be the case
        # when the attempts count times out
        self.removeLockEntry(lines, filename)

        if addentry:
            try:
                lines.append(str(random.randint(1, 60000)) + "," + filename + "\n")
            except Exception,e:
                return False

        try:
            fle = FileAccess.open(self.lockName, 'w')
        except Exception,e:
            self.log("Unable to open the lock file for writing")
            return False

        flewrite = ''

        for line in lines:
            flewrite += line

        try:
            fle.write(flewrite)
        except Exception,e:
            self.log("Exception writing to the log file")

        fle.close()


    def findLockEntry(self, lines, filename):
        self.log("findLockEntry")

        # Read the file
        for line in lines:
            # Format is 'random value,filename'
            index = line.find(",")
            flenme = ''
            setval = -1

            # Valid line, get the value and filename
            if index > -1:
                try:
                    setval = int(line[:index])
                    flenme = line[index + 1:].strip()
                except Exception,e:
                    setval = -1
                    flenme = ''

            # The lock already exists
            if flenme == filename:
                self.log("entry exists, val is " + str(setval))
                return setval

        return -1


    def removeLockEntry(self, lines, filename):
        self.log("removeLockEntry")
        realindex = 0

        for i in range(len(lines)):
            index = lines[realindex].find(filename)

            if index > -1:
                del lines[realindex]
                realindex -= 1

            realindex += 1


    def unlockFile(self, filename):
        self.log("unlockFile " + filename)
        filename = filename.lower()
        found = False
        realindex = 0
        # First make sure we actually own the lock
        # Remove it from the list if we do
        self.listSemaphore.acquire()

        for i in range(len(self.lockedList)):
            if self.lockedList[realindex] == filename:
                del self.lockedList[realindex]
                found = True
                realindex -= 1

            realindex += 1

        self.listSemaphore.release()

        if found == False:
            self.log("Lock not found")
            return False

        self.grabSemaphore.acquire()

        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return False

        try:
            fle = FileAccess.open(self.lockName, "r")
        except Exception,e:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return False

        lines = fle.readlines()
        fle.close()
        self.writeLockEntry(lines, filename, False)
        self.releaseLockFile()
        self.grabSemaphore.release()
        return True


    def isFileLocked(self, filename, block = False):
        self.log("isFileLocked " + filename)
        filename = filename.lower()
        self.grabSemaphore.acquire()

        if self.grabLockFile() == False:
            self.grabSemaphore.release()
            return True

        try:
            fle = FileAccess.open(self.lockName, "r")
        except Exception,e:
            self.log("Unable to open the lock file")
            self.releaseLockFile()
            self.grabSemaphore.release()
            return True

        lines = fle.readlines()
        fle.close()
        retval = False

        if self.findLockEntry(lines, filename) > -1:
            retval = True

        self.releaseLockFile()
        self.grabSemaphore.release()
        return retval  