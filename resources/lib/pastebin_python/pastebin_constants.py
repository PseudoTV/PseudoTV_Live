"""
.. module:: pastebin_constants
	:synopsis: This module contains the constants that can be used in the :meth:`pastebin.PastebinPython.__processPost` , :meth:`pastebin.PastebinPython.createPaste` and :meth:`pastebin.PastebinPython.createPasteFromFile`

.. moduleauthor:: Ferdinand Silva <ferdinandsilva@ferdinandsilva.com>

"""
PASTEBIN_URL = "http://pastebin.com/" #: The pastebin.com base url
PASTEBIN_RAW_URL = "%s%s" % (PASTEBIN_URL, "raw.php?i=%s")
PASTEBIN_API_URL = "%s%s" % (PASTEBIN_URL, "api/") #: The pastebin.com API base URL
PASTEBIN_API_POST_URL = "%s%s" % (PASTEBIN_API_URL, "api_post.php") #: The pastebin.com API POST URL
PASTEBIN_API_LOGIN_URL = "%s%s" % (PASTEBIN_API_URL, "api_login.php") #: The pastebin.com API login URL

PASTE_PUBLIC = 0 #:
PASTE_UNLISTED = 1  #:
PASTE_PRIVATE = 2  #:

EXPIRE_NEVER = "N"  #:
EXPIRE_10_MIN = "10M"  #:
EXPIRE_1_HOUR = "1H"  #:
EXPIRE_1_DAY = "1D"  #:
EXPIRE_1_MONTH = "1M"  #: