"""
.. module:: pastebin
   :synopsis: This module contains the main class to be instantiated to use pastebin.com functionality

.. moduleauthor:: Ferdinand Silva <ferdinandsilva@ferdinandsilva.com>

"""
import re
import requests
from xml.dom.minidom import parseString
from pastebin_options import OPTION_PASTE, OPTION_LIST, OPTION_TRENDS, OPTION_DELETE, OPTION_USER_DETAILS
from pastebin_constants import PASTEBIN_API_POST_URL, PASTEBIN_API_LOGIN_URL, PASTEBIN_RAW_URL
from pastebin_exceptions import PastebinBadRequestException, PastebinNoPastesException, PastebinFileException, PastebinHTTPErrorException
import binascii


class PastebinPython(object):
    """This is the main class to be instantiated to use pastebin.com functionality

    """

    def __init__(self, **kwargs):
        """You need to put your **API Key** when instantiating this class

        :param kwargs: keyword arguments to set settings that can be use to call pastebin.com API function
        :type kwargs: dict
        :returns: class -- :class:`pastebin_python.pastebin.PastebinPython`

        **Example:**::

            >>> pasteBin = PastebinPython(api_dev_key='123456789')
            >>> print pasteBin.api_dev_key
            123456789

        """

        self.api_dev_key = binascii.a2b_base64(kwargs.get('api_dev_key', ''))
        self.__api_user_key = kwargs.get('api_user_key', '')
        self.__api_user_paste_list = []
        self.api_session = requests.session()
        self.web_session = requests.session()

    @property
    def api_user_key(self):
        """This is where the api_user_key is stored after calling :meth:`pastebin_python.pastebin.PastebinPython.createAPIUserKey`

        :returns: str -- the api_user_key

        """
        return self.__api_user_key

    @property
    def api_user_paste_list(self):
        """This where the list of pastes of the current user is stored after calling :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes`

        :returns: list -- current user pastes list

        """
        return self.__api_user_paste_list

    def createPaste(self, api_paste_code, api_paste_name='', api_paste_format='', api_paste_private='', api_paste_expire_date=''):
        """This will create a new paste

        :param api_paste_code: this is the text that will be written inside your paste
        :type api_paste_code: str
        :param api_paste_name: this will be the name / title of your paste
        :type api_paste_name: str
        :param api_paste_format: this will be the syntax highlighting value, values to be assign can be found at :mod:`pastebin_python.pastebin_formats`
        :type api_paste_format: str
        :param api_paste_private: this makes a paste public or private, values to be assign can be found at :mod:`pastebin_python.pastebin_constants`
        :type api_paste_private: int
        :param api_paste_expire_date: this sets the expiration date of your paste, values to be assign can be found at :mod:`pastebin_python.pastebin_constants`
        :type api_paste_expire_date: str
        :returns: str -- pastebin.com paste URL
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`

        .. note::

            *api_paste_code* is the only required parameter

        """
        api_user_key = self.api_user_key if self.api_user_key else ""
        api_paste_code = api_paste_code.encode('utf-8') if api_paste_code else ""

        postData = {
            'api_option': OPTION_PASTE,
            'api_dev_key': self.api_dev_key
        }

        localVar = locals()

        for k, v in localVar.items():
            if re.search('^api_',k) and v != "":
                postData[k] = v

        return self.__processRequest('POST', PASTEBIN_API_POST_URL, postData)

    def createPasteFromFile(self, filename, api_paste_name='', api_paste_format='', api_paste_private='', api_paste_expire_date=''):
        """Almost the same as :meth:`pastebin_python.pastebin.PastebinPython.createPaste` ,the only difference is that the value of *api_paste_code* came from the file you opened

        :param filename: the full path of the file
        :type filename: str
        :param api_paste_name: this will be the name / title of your paste
        :type api_paste_name: str
        :param api_paste_format: this will be the syntax highlighting value, values to be assign can be found at :mod:`pastebin_python.pastebin_formats`
        :type api_paste_format: str
        :param api_paste_private: this makes a paste public or private, values to be assign can be found at :mod:`pastebin_python.pastebin_constants`
        :type api_paste_private: int
        :param api_paste_expire_date: this sets the expiration date of your paste, values to be assign can be found at :mod:`pastebin_python.pastebin_constants`
        :type api_paste_expire_date: str
        :returns: str -- pastebin.com paste URL
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinFileException`

        .. note::

            *filename* is the only required field

        """

        try:
            fileToOpen = open(filename, 'r')
            fileToPaste = fileToOpen.read()
            fileToOpen.close()

            return self.createPaste(fileToPaste, api_paste_name, api_paste_format, api_paste_private, api_paste_expire_date)
        except IOError as e:
            raise PastebinFileException( str(e))

    def __processRequest(self, method, url, data):
        """A private function that is responsible of calling/executing the pastebin.com functionality

        :param url: the url of the pastebin.com **API**
        :type url: str
        :param data: the data to be POSTed to the pastebin.com **API**
        :type data: dict
        :returns: str -- the successfull output of the pastebin.com **API** if no exception raised
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`, :exc:`pastebin_python.pastebin_exceptions.PastebinNoPastesException`

        """
        if url == PASTEBIN_API_LOGIN_URL:
            web_data = {'submit_hidden': 'submit_hidden',
                        'user_name': data['api_user_name'],
                        'user_password': data['api_user_password'],
                        'submit': 'Login', }
            self.web_session.get('http://pastebin.com/login')
            self.web_session.post('http://pastebin.com/login.php', data=web_data)

        if url == PASTEBIN_RAW_URL:
            req = self.web_session.get(url % data)
        else:
            req = self.api_session.request(method, url, data=data)

        response = req.content
        if re.search('^Bad API request', response):
            raise PastebinBadRequestException(response)
        elif re.search('^No pastes found', response):
            raise PastebinNoPastesException

        return response

    def createAPIUserKey(self, api_user_name, api_user_password):
        """This is used to request an *api_user_key* which can be used to create a paste as a logged in user

        :param api_user_name: this is the pastebin.com username
        :type api_user_name: str
        :param api_user_password: this is the pastebin.com password
        :type api_user_password: str
        :returns: str -- unique user session key
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`

        .. note::

            If successfull the unique user session key will be assigned to the private variable *__api_user_key* and can be get with the property *api_user_key*

        """

        postData = {
            'api_dev_key': self.api_dev_key,
            'api_user_name': api_user_name,
            'api_user_password': api_user_password
        }

        self.__api_user_key = self.__processRequest('POST', PASTEBIN_API_LOGIN_URL, postData)
        self.__api_user_paste_list = []
        return self.__api_user_key

    def listUserPastes(self, api_results_limit=50):
        """This will list pastes created by a user

        :param api_results_limit: this is not required but the min value should be 1 and the max value should be 1000
        :type api_results_limit: int
        :returns: list -- the list of of pastes in a dictionary type
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`, :exc:`pastebin_python.pastebin_exceptions.PastebinNoPastesException`

        .. note::

            Need to call the :meth:`pastebin_python.pastebin.PastebinPython.createAPIUserKey` first before calling this function
            Pastes list will be stored to the private variable *__api_user_paste_list* and can be retrieve by the property *api_user_key*

        """

        postData = {
            'api_dev_key': self.api_dev_key,
            'api_user_key': self.api_user_key,
            'api_results_limit': api_results_limit,
            'api_option': OPTION_LIST
        }

        pastesList = self.__processRequest('POST', PASTEBIN_API_POST_URL, postData)
        self.__api_user_paste_list = self.__parseXML(pastesList)

        return self.__api_user_paste_list

    def listTrendingPastes(self):
        """This will list the 18 currently trending pastes

        :returns: list -- the 18 currently trending pastes in a dictionary format
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`

        """

        postData = {
            'api_dev_key': self.api_dev_key,
            'api_option': OPTION_TRENDS
        }

        trendsList = self.__processRequest('POST', PASTEBIN_API_POST_URL, postData)
        trendsList = self.__parseXML(trendsList)

        return trendsList

    def __parseUser(self, xmlString):
        """This will parse the xml string returned by the function :meth:`pastebin_python.pastebin.PastebinPython.getUserInfos`

        :param xmlString: this is the returned xml string from :meth:`pastebin_python.pastebin.PastebinPython.getUserInfos`
        :type xmlString: str
        :returns: list -- user info in a dictionary format

        """
        retList = []
        userElement = xmlString.getElementsByTagName('user')[0]

        retList.append({
            'user_name':userElement.getElementsByTagName('user_name')[0].childNodes[0].nodeValue,
            'user_avatar_url':userElement.getElementsByTagName('user_avatar_url')[0].childNodes[0].nodeValue,
            'user_account_type':userElement.getElementsByTagName('user_account_type')[0].childNodes[0].nodeValue
            })

        formatElement = userElement.getElementsByTagName('user_format_short')
        if formatElement:
            retList[0]['user_format_short'] = formatElement[0].childNodes[0].nodeValue

        expireElement = userElement.getElementsByTagName('user_expiration')
        if expireElement:
            retList[0]['user_expiration'] = expireElement[0].childNodes[0].nodeValue

        privateElement = userElement.getElementsByTagName('user_private')
        if privateElement:
            retList[0]['user_private'] = privateElement[0].childNodes[0].nodeValue

        websiteElement = userElement.getElementsByTagName('user_website')
        if websiteElement:
            retList[0]['user_website'] = websiteElement[0].childNodes[0].nodeValue

        emailElement = userElement.getElementsByTagName('user_email')
        if emailElement:
            retList[0]['user_email'] = emailElement[0].childNodes[0].nodeValue

        locationElement = userElement.getElementsByTagName('user_location')
        if locationElement:
            retList[0]['user_location'] = locationElement[0].childNodes[0].nodeValue

        return retList

    def __parsePaste(self, xmlString):
        """This will parse the xml string returned by the the function :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes` or :meth:`pastebin_python.pastebin.PastebinPython.listTrendingPastes`

        :param xmlString: this is the returned xml string from :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes` or :meth:`pastebin_python.pastebin.PastebinPython.listTrendingPastes`
        :type xmlString: str
        :returns: list -- pastes info in a dictionary format

        """
        retList = []
        pasteElements = xmlString.getElementsByTagName('paste')

        for pasteElement in pasteElements:
            try:
                paste_title = pasteElement.getElementsByTagName('paste_title')[0].childNodes[0].nodeValue
            except IndexError:
                paste_title = ""

            retList.append({
                'paste_title': paste_title,
                'paste_key': pasteElement.getElementsByTagName('paste_key')[0].childNodes[0].nodeValue,
                'paste_date': pasteElement.getElementsByTagName('paste_date')[0].childNodes[0].nodeValue,
                'paste_size': pasteElement.getElementsByTagName('paste_size')[0].childNodes[0].nodeValue,
                'paste_expire_date': pasteElement.getElementsByTagName('paste_expire_date')[0].childNodes[0].nodeValue,
                'paste_private': pasteElement.getElementsByTagName('paste_private')[0].childNodes[0].nodeValue,
                'paste_format_long': pasteElement.getElementsByTagName('paste_format_long')[0].childNodes[0].nodeValue,
                'paste_format_short': pasteElement.getElementsByTagName('paste_format_short')[0].childNodes[0].nodeValue,
                'paste_url': pasteElement.getElementsByTagName('paste_url')[0].childNodes[0].nodeValue,
                'paste_hits': pasteElement.getElementsByTagName('paste_hits')[0].childNodes[0].nodeValue,
            })

        return retList


    def __parseXML(self, xml, isPaste=True):
        """This will handle all of the xml string parsing

        :param xml: xml string
        :type xml: str
        :param isPaste: if True then it will parse the pastes info else it will parse the user info
        :type isPaste: bool
        :returns: list -- info in a dictionary format

        """
        retList = []
        xmlString = parseString("<pasteBin>%s</pasteBin>" % xml)

        if isPaste:
            retList = self.__parsePaste(xmlString)
        else:
            retList = self.__parseUser(xmlString)

        return retList


    def deletePaste(self, api_paste_key):
        """This will delete pastes created by certain users

        :param api_paste_key: this is the paste key that which you can get in the :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes` function
        :type api_paste_key: str
        :returns: bool -- True if the deletion is successfull else False

        .. note::

            Before calling this function, you need to call the :meth:`pastebin_python.pastebin.PastebinPython.createAPIUserKey` first then call the :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes`

        """
        postData = {
            'api_dev_key': self.api_dev_key,
            'api_user_key': self.api_user_key,
            'api_paste_key': api_paste_key,
            'api_option': OPTION_DELETE
        }

        try:
            retMsg = self.__processRequest('POST', PASTEBIN_API_POST_URL, postData)
        except PastebinBadRequestException as e:
            retMsg = str(e)

        if re.search('^Paste Removed', retMsg):
            return True

        return False


    def getUserInfos(self):
        """You can obtain a users personal info and certain settings by calling this function

        :returns: list -- user info in a dictionary format
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinBadRequestException`

        .. note::

            You need to call the :meth:`pastebin_python.pastebin.PastebinPython.createAPIUserKey` before calling this function

        """

        postData = {
            'api_dev_key': self.api_dev_key,
            'api_user_key': self.api_user_key,
            'api_option': OPTION_USER_DETAILS
        }

        retData = self.__processRequest('POST', PASTEBIN_API_POST_URL, postData)
        retData = self.__parseXML(retData, False)

        return retData

    def getPasteRawOutput(self, api_paste_key):
        """This will get the raw output of the paste

        :param api_paste_key: this is the paste key that which you can get in the :meth:`pastebin_python.pastebin.PastebinPython.listUserPastes` function
        :type api_paste_key: str
        :returns: str -- raw output of the paste
        :raises: :exc:`pastebin_python.pastebin_exceptions.PastebinHTTPErrorException`

        """

        try:
            retMsg = self.__processRequest('GET', PASTEBIN_RAW_URL, api_paste_key)
        except PastebinBadRequestException as e:
            retMsg = str(e)

        return retMsg.decode('utf-8')
