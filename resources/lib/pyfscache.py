#! /usr/bin/env python

import os
import hashlib
import cPickle
import time
import base64
import inspect
import xbmcvfs

__all__ = ["CacheError", "FSCache", "make_digest",
           "auto_cache_function", "cache_function", "to_seconds"]

class CacheError(Exception):
  pass

class TimeError(CacheError):
  pass

class LifetimeError(CacheError):
  pass

class CacheObject(object):
  """
  A wrapper for values, to allow for more elaborate control
  like expirations some time in the far, far, distant future,
  if ever. So don't count on it unless someone writes a patch.
  """
  def __init__(self, value, expiration=None):
    """
    Creates a new :class:`phyles.CacheObject` with an attribute
    ``value`` that is object passed by the `value` parameter. The
    `expiration` should be the number of seconds since the epoch.
    See the python :py:mod:`time` module for a discussion of the
    epoch. If `expiration` is excluded, the the :class:`CacheObject`
    object has no expiration.
    """
    self._value = value
    self._expiration = expiration
  def get_value(self):
    return self._value
  def get_expiration(self):
    return self._expiration
  def expired(self):
    """
    Returns ``True`` if the :class:`CacheObject` object has
    expired according to the system time.
    If the :class:`CacheObject` has an expiration of ``None``,
    then ``False`` is returned.
    """
    if self.expiration is None:
      r = False
    else:
      r = (self.expiration < time.time())
    return r
  value = property(get_value)
  expiration = property(get_expiration)

class FSCache(object):
  """
  A class that manages a filesystem cache. Works like
  a dictionary and can decorate functions to make them
  cached.

  A :class:`pyfscache.FSCache` object is instantiated
  with a `path` and optional lifetime keyword arguments:

  .. code-block:: python

      >>> c = FSCache('cache/dir', days=7)

  This command creates a new FSCache instance at the given
  `path` (``cache/dir``). Each item added by this cache
  has a lifetime of 7 days, starting when the item (not the cache)
  is created. If the `path` doesn't exist,
  one is made. New items added to the cache are given a lifetime
  expressed by the keyword arguments with potential keys of
  ``years``, ``months``, ``weeks``, ``days``,
  ``hours``, ``minutes``, ``seconds`` (see :func:`to_seconds`).
  If no keyword arguments are given, then the
  items added by the cache do not expire automatically.

  Creating an :class:`pyfscache.FSCache` object does not purge
  the cache in `path` if the cache already exists. Instead,
  the :class:`pyfscache.FSCache` object will begin to use the
  cache, loading items and storing items as necessary.

  .. code-block:: python

      >>> import os
      >>> import shutil
      >>> from pyfscache import *
      >>> if xbmcvfs.exists('cache/dir'):
      ...   shutil.rmtree('cache/dir')
      ... 
      >>> c = FSCache('cache/dir', days=7)
      >>> c['some_key'] = "some_value"
      >>> c['some_key']
      'some_value'
      >>> xbmcvfs.listdir('cache/dir')
      ['PXBZzwEy3XnbOweuMtoPj9j=PwkfAsTXexmW2v05JD']
      >>> c.expire('some_key')
      >>> xbmcvfs.listdir('cache/dir')
      []
      >>> c['some_key'] = "some_value"
      >>> @c
      ... def doit(avalue):
      ...   print "had to call me!"
      ...   return "some other value"
      ... 
      >>> doit('some input')
      had to call me!
      'some other value'
      >>> doit('some input')
      'some other value'
      >>> shutil.rmtree('cache/dir')
  """
  def __init__(self, path, **kwargs):
    """
    A :class:`pyfscache.FSCache` object is instantiated
    with a `path` and optional lifetime keyword arguments:

  .. code-block:: python

      >>> c = FSCache('cache/dir', days=7)

    Inits a new FSCache instance at the given `path`.
    If the `path` doesn't exist, one is made. New objects
    added to the cache are given a lifetime, expressed in the
    keyword arguments `kwargs` with potential keys of
    ``years``, ``months``, ``weeks``, ``days``,
    ``hours``, ``minutes``, ``seconds``. See :func:`to_seconds`.
    If no keyword arguments are given, then the lifetime
    is considered to be infinite.

    Creating a :class:`pyfscache.FSCache` object does not purge
    the cache in `path` if the cache already exists. Instead,
    the :class:`pyfscache.FSCache` object will begin to use the
    cache, loading items and storing items as necessary.
    """
    if kwargs:
      self._lifetime = to_seconds(**kwargs)
      if self._lifetime <= 0:
        msg = "Lifetime (%s seconds) is 0 or less." % self._lifetime
        raise LifetimeError, msg
    else:
      self._lifetime = None
    self._loaded = {}
    self._path = os.path.abspath(path)
    if not xbmcvfs.exists(self._path):
      xbmcvfs.mkdirs(self._path)
  def __getitem__(self, k):
    """
    Returns the object stored for the key `k`. Will
    load from the filesystem if not already loaded.
    """
    if k in self:
      digest = make_digest(k)
      value = self._loaded[digest].value
    else:
      msg = "No such key in cache: '%s'" % k
      raise KeyError(msg)
    return value
  def __setitem__(self, k, v):
    """
    Sets the object `v` to the key `k` and saves the
    object in the filesystem. This will raise an error
    if an attempt is made to set an object for a key `k`
    that already exists. To replace an item forcibly in this
    way, use :func:`update`, or first use :func`expire`.
    """
    digest = make_digest(k)
    path = os.path.join(self._path, digest)
    if (digest in self._loaded) or xbmcvfs.exists(path):
      tmplt = ("Object for key `%s` exists\n." +
               "Remove the old one before setting the new object.")
      msg = tmplt % str(k)
      raise CacheError, msg
    else:
      expiry = self.expiry()
      contents = CacheObject(v, expiration=expiry)
      dump(contents, path)
      self._loaded[digest] = contents
  def __delitem__(self, k):
    """
    Removes the object keyed by `k` from memory
    but not from the filesystem. To remove it from both the memory,
    and the filesystem, use `expire`.

    Synonymous with :func:`FSCache.unload`.
    """
    digest = make_digest(k)
    if digest in self._loaded:
      del(self._loaded[digest])
    else:
      msg = "Object for key `%s` has not been loaded" % str(k)
      raise CacheError, msg
  def __contains__(self, k):
    """
    Returns ``True`` if an object keyed by `k` is
    in the cache on the file system, ``False`` otherwise.
    """
    digest = make_digest(k)
    if digest in self._loaded:
      contents = self._loaded[digest]
      isin = True
    else:
      try:
        contents = self._load(digest, k)
        isin = True
      except CacheError:
        isin = False
    if isin:
      if contents.expired():
        self.expire(k)
        isin = False
    return isin
  def __call__(self, f):
    """
    Returns a cached function from function `f` using `self`
    as the cache. See :func:`auto_cache_function`.

    Imbues an :class:`FSCache` object with the ability to
    be a caching decorator.

    >>> acache = FSCache('cache-dir')
    >>> @acache
    ... def cached_by_decorator(a, b, c):
    ...    return list(a, b, c)
    ...
    >>> cached_by_decorator(1, 2, 3)
    [1, 2, 3]
    >>> cached_by_decorator(1, 2, 3)
    [1, 2, 3]
    """
    return auto_cache_function(f, self)
  def _load(self, digest, k):
    """
    Loads the :class:`CacheObject` keyed by `k` from the
    file system (residing in a file named by `digest`)
    and returns the object.

    This method is part of the implementation of :class:`FSCache`,
    so don't use it as part of the API.
    """
    path = os.path.join(self._path, digest)
    if xbmcvfs.exists(path):
      contents = load(path)
    else:
      msg = "Object for key `%s` does not exist." % (k,)
      raise CacheError, msg
    self._loaded[digest] = contents
    return contents
  def _remove(self, k):
    """
    Removes the cache item keyed by `k` from the file system.

    This method is part of the implementation of :class:`FSCache`,
    so don't use it as part of the API.
    """
    digest = make_digest(k)
    path = os.path.join(self._path, digest)
    if xbmcvfs.exists(path):
      xbmcvfs.delete(path)
    else:
      msg = "No object for key `%s` stored." % str(k)
      raise CacheError, msg
  def is_loaded(self, k):
    """
    Returns ``True`` if the item keyed by `k` has been loaded,
    ``False`` if not.
    """
    digest = make_digest(k)
    return digest in self._loaded
  def unload(self, k):
    """
    Removes the object keyed by `k` from memory
    but not from the filesystem. To remove the object
    keyed by `k` from both memory and permanently from the
    filesystem, use `expire`.

    Synonymous with deleting an item.
    """
    del self[k]
  def expire(self, k):
    """
    Use with care. This permanently removes the object keyed
    by `k` from the cache, both in the memory and in the filesystem.
    """
    self._remove(k)
    del self[k]
  def get_path(self):
    """
    Returns the absolute path to the file system cache represented
    by the instance.
    """
    return self._path
  def get_lifetime(self):
    """
    Returns the lifetime, in seconds, of new items in the cache.
    If new items do not expire, then ``None`` is returned.
    """
    return self._lifetime
  def update_item(self, k, v):
    """
    Use with care. Updates, both in memory and on the filesystem,
    the object for key `k` with the object `v`. If the key `k`
    already exists with a stored object, it will be replaced.
    """
    self.expire(k)
    self[k] = v
  def load(self, k):
    """
    Causes the object keyed by `k` to be loaded from the
    file system and returned. It therefore causes this object
    to reside in memory.
    """
    return self[k]
  def unload(self, k):
    """
    Removes the object keyed by `k` from memory
    but not from the filesystem. To remove it from both
    memory and permanently from the filesystem, use `expire`.
    """
    digest = make_digest(k)
    if digest in self._loaded:
      del(self._loaded[digest])
  def get_loaded(self):
    """
    Returns a list of keys for all objects that are loaded.
    """
    return self._loaded.keys()
  def get_names(self):
    """
    Returns the names of the files in the cache on the
    filesystem. These are not keys but one-way hashes
    (or "digests") of the keys created by :func:`make_digest`.
    """
    return xbmcvfs.listdir(self._path)
  def clear(self):
    """
    Unloads all loaded cache items from memory.
    All cache items remain on the disk, however.
    """
    self._loaded.clear()
  def purge(self):
    """
    Be careful, this empties the cache from both the filesystem
    and memory!
    """
    files = xbmcvfs.listdir(self._path)
    for f in files:
      path = os.path.join(self._path, f)
      xbmcvfs.delete(path)
    self.clear()
  def expiry(self):
    """
    Returns an expiry for the cache in seconds as if the start
    of the expiration period were the moment at which this
    the method is called.

    >>> import time
    >>> c = FSCache('cache/dir', seconds=60)
    >>> round(c.expiry() - time.time(), 3)
    60.0
    """
    if self.lifetime is None:
      x = None
    else:
      x = self.lifetime + time.time()
    return x
  path = property(get_path)
  lifetime = property(get_lifetime)

def make_digest(k):
  """
  Creates a digest suitable for use within an :class:`phyles.FSCache`
  object from the key object `k`.

  >>> adict = {'a' : {'b':1}, 'f': []}
  >>> make_digest(adict)
  'a2VKynHgDrUIm17r6BQ5QcA5XVmqpNBmiKbZ9kTu0A'
  """
  s = cPickle.dumps(k)
  h = hashlib.sha256(s).digest()
  b64 = base64.urlsafe_b64encode(h)[:-2]
  return b64.replace('-', '=')

def load(filename):
  """
  Helper function that simply pickle loads the first object
  from the file named by `filename`.
  """
  f = open(filename, 'rb')
  obj = cPickle.load(f)
  f.close()
  return obj

def dump(obj, filename):
  """
  Helper function that simply pickle dumps the object
  into the file named by `filename`.
  """
  f = open(filename, 'wb')
  cPickle.dump(obj, f, cPickle.HIGHEST_PROTOCOL)
  f.close()

def auto_cache_function(f, cache):
  """
  Creates a cached function from function `f`.
  The `cache` can be any mapping object, such as `FSCache` objects.

  The function arguments are expected to be well-behaved
  for python's :py:mod:`cPickle`. Or, in other words, 
  the expected values for the parameters (the arguments) should
  be instances new-style classes (i.e. inheriting from
  :class:`object`) or implement :func:`__getstate__` with
  well-behaved results.

  If the arguments to `f` are not expected to be well-behaved,
  it is best to use `cache_function` instead and create a custom keyer.
  """
  m = inspect.getmembers(f)
  try:
    fid = (f.func_name, inspect.getargspec(f))
  except (AttributeError, TypeError):
    fid = (f.__name__, repr(type(f)))
  def _f(*args, **kwargs):
    k = (fid, args, kwargs)
    if k in cache:
      result = cache[k]
    else:
      result = f(*args, **kwargs)
      cache[k] = result
    return result
  return _f

    
def cache_function(f, keyer, cache):
  """
  Takes any function `f` and a function that creates a key,
  `keyer` and caches the result in `cache`.

  The keys created by `keyer` should be well behaved for
  python's :py:mod:`cPickle`. See the documentation for
  :func:`auto_cache_funtion` for details.

  It is best to have a unique `keyer` for every function.
  """
  def _f(*args, **kwargs):
    k = keyer(*args, **kwargs)
    if k in cache:
      result = cache[k]
    else:
      result = f(*args, **kwargs)
      cache[k] = result
    return result
  return _f

def years_to_seconds(years):
  """
  Converts `years` to seconds.
  """
  return 3.15569e7 * years

def months_to_seconds(months):
  """
  Converts `months` to seconds.
  """
  return 2.62974e6 * months

def weeks_to_seconds(weeks):
  """
  Converts `weeks` to seconds.
  """
  return 604800.0 * weeks

def days_to_seconds(days):
  """
  Converts `days` to seconds.
  """
  return 86400.0 * days

def hours_to_seconds(hours):
  """
  Converts `hours` to seconds.
  """
  return 3600.0 * hours

def minutes_to_seconds(minutes):
  """
  Converts `minutes` to seconds.
  """
  return 60.0 * minutes

def seconds_to_seconds(seconds):
  """
  Converts `seconds` to seconds as a :class:`float`.
  """
  return float(seconds)

TIME_CONVERTERS = {"years" : years_to_seconds,
                   "months" : months_to_seconds,
                   "weeks" : weeks_to_seconds,
                   "days" : days_to_seconds,
                   "hours" : hours_to_seconds,
                   "minutes" : minutes_to_seconds,
                   "seconds" : seconds_to_seconds}

def to_seconds(**kwargs):
  """
  Converts keyword arguments to seconds.

  The the keyword arguments can have the following keys:

     - ``years`` (31,556,900 seconds per year)
     - ``months`` (2,629,740 seconds per month)
     - ``weeks`` (604,800 seconds per week)
     - ``days`` (86,400 seconds per day)
     - ``hours`` (3600 seconds per hour)
     - ``minutes`` (60 seconds per minute)
     - ``seconds``

  >>> to_seconds(seconds=15, minutes=20)
  1215.0
  >>> to_seconds(seconds=15.42, hours=10, minutes=18, years=2)
  63150895.42
  """
  seconds = []
  for k, v in kwargs.items():
    if k in TIME_CONVERTERS:
      seconds.append(TIME_CONVERTERS[k](v))
    else:
      msg = "Not a valid unit of time: '%s'" % k
      raise TimeError(msg)
  return sum(seconds)
