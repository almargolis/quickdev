#
# bafExeController - program start-up environment
#
#   Provides a platform independent program environment for programs.
#

CGI_KEY_FILTER = bzUtil.LETTERSANDNUMBERS + "-_."

#
# IsCgi() and IsSLL() are probably not needed any more and
# may not be functional.
#


def IsCgi():
    wsCgiGatewayInterface = bzUtil.GetEnv("GATEWAY_INTERFACE")
    if wsCgiGatewayInterface == "":
        return False
    else:
        return True


def IsSsl():
    wsServerPort = bzUtil.GetEnv("SERVER_PORT")
    wsServerHttps = bzUtil.GetEnv("HTTPS")
    if wsServerPort == "443":
        wsServerHttps = "on"  # force Apache 1.2 SUEXEC bug
    if (wsServerPort == "443") and (wsServerHttps == "on"):
        return True
    else:
        return False


ModeConsole = "C"
ModeCgi = "A"


class ApacheCgi(object):
    def GetCgiEnvironment(self, QueryString=None, PostDataBlob=None, ScriptPath=""):
        self.cgiGatewayInterface = bzUtil.GetEnv("GATEWAY_INTERFACE")
        self.serverPort = bzUtil.GetEnv("SERVER_PORT")
        self.serverHttps = bzUtil.GetEnv("HTTPS")
        if QueryString:
            self.cgiQueryString = QueryString
            self.cgiRemoteAddr = ""
            self.cgiUserAgent = ""
            self.cgiScriptPath = ScriptPath
            self.redirectURL = ""
        else:
            self.cgiQueryString = bzUtil.GetEnv("QUERY_STRING")
            self.cgiRemoteAddr = bzUtil.GetEnv("REMOTE_ADDR")
            self.cgiUserAgent = bzUtil.GetEnv("HTTP_USER_AGENT")
            self.cgiScriptPath = bzUtil.GetEnv("SCRIPT_FILENAME")
            self.redirectURL = bzUtil.GetEnv("REDIRECT_URL")
        self.cgiScriptName = bzUtil.GetFileName(self.cgiScriptPath)
        self.SetMode()
        self.CollectCookies()
        self.CollectPostData(PostDataBlob=PostDataBlob)

    def SetMode(self):
        if self.cgiGatewayInterface == "":
            self.mode = ModeConsole
            self.printHtml = False
            self.isCgi = False
            self.isSsl = False
        else:
            self.mode = ModeCgi
            self.printHtml = True
            self.isCgi = True
            if self.serverPort == "443":
                self.serverHttps = "on"  # force Apache 1.2 SUEXEC bug
            if (self.serverPort == "443") and (self.serverHttps == "on"):
                self.isSsl = True
            else:
                self.isSsl = False

    def CollectCookies(self):
        self.activityId = None
        self.sessionId = None
        self.sessionCookie = None
        self.sessionCookieStatus = None
        self.cookiesEnabled = SessionCookiesUnknown  # at this time we have no idea
        self.cookieDataRaw = bafNv.bafNvTuple()
        self.cookieDataRaw.AssignDefaultValue(None)
        self.cgiHttpCookie = bzUtil.GetEnv("HTTP_COOKIE")
        wsCgiCookieLines = string.splitfields(self.cgiHttpCookie, ";")
        for wsCgiCookie in wsCgiCookieLines:
            wsPos = string.find(wsCgiCookie, "=")
            if wsPos < 0:
                continue  # no equal sign
            wsFldName = string.strip(wsCgiCookie[:wsPos])
            wsFldValue = string.strip(wsCgiCookie[wsPos + 1 :])
            self.cookieDataRaw[wsFldName] = bzHtml.CgiUnquote(wsFldValue)
            self.cookiesEnabled = SessionCookiesEnabled

    def CollectPostData(self, PostDataBlob=None):
        if PostDataBlob is not None:
            self.cgiRestfulVerb = RestfulVerb_Post
            self.cgiPostDataBlobLen = len(FormData)
            self.CgiPostDataBlob = PostDataBlob
        else:
            self.cgiRestfulVerb = bzUtil.GetEnv("REQUEST_METHOD")
            self.cgiPostDataBlobLen = int(bzUtil.GetEnv("CONTENT_LENGTH", 0))
            if (self.cgiRestfulVerb == RestfulVerb_Post) and (
                self.cgiPostDataBlobLen > 0
            ):
                wsUnicodeReader = codecs.getreader("utf-8")(sys.stdin)
                self.cgiPostDataBlob = wsUnicodeReader.read(self.cgiPostDataBlobLen)
            else:
                self.cgiPostDataBlob = ""

        wsContentType = bzUtil.GetEnv("CONTENT_TYPE", "")
        self.cgiMimeInfo = bzMime.bzMime(
            bzMime.ContentTypeKeyword + ": " + wsContentType
        )
        self.cgiContentType = self.cgiMimeInfo.mimeType
        if self.cgiContentType == bzMime.ContentTypeBrowserForm:
            self.cgiPostDataRaw = self.cgiMimeInfo.DecodeCgiBlob(self.cgiPostDataBlob)
        else:
            # Content-Type: application/x-www-form-urlencoded (bzMime.ContentTypeApplicationForm)
            self.cgiPostDataRaw = bafNv.bafNvTuple()
            wsCgiFormDataLines = self.cgiPostDataBlob.split("&")
            for wsCgiFormLine in wsCgiFormDataLines:
                wsPos = wsCgiFormLine.find("=")
                if wsPos < 0:  # no equal sign
                    self.cgiPostDataRaw[wsCgiFormLine] = True
                else:
                    wsFldName = wsCgiFormLine[:wsPos]
                    wsFldValue = wsCgiFormLine[wsPos + 1 :]
                    self.cgiPostDataRaw[wsFldName] = bzHtml.CgiUnquote(wsFldValue)

    def CollectGetData(self):
        self.cgiGetDataRaw = bafNv.bafNvTuple()
        self.cgiGetDataRaw.AssignDefaultValue(None)
        if self.cgiQueryString != "":
            wsCgiQueryList = string.splitfields(self.cgiQueryString, "&")
            for _ix, wsCgiQuery in enumerate(wsCgiQueryList):
                wsPos = string.find(wsCgiQuery, "=")
                if wsPos < 0:  # no equal sign
                    if _ix == 0:  # 1st is value of script name
                        self.cgiGetDataRaw[self.cgiScriptName] = wsCgiQuery
                    else:  # rest are flags
                        self.cgiGetDataRaw[wsCgiQuery] = True
                else:  # name=value
                    wsFldName = wsCgiQuery[:wsPos]
                    wsFldValue = wsCgiQuery[wsPos + 1 :]
                    self.cgiGetDataRaw[wsFldName] = bzHtml.CgiUnquote(wsFldValue)

        self.cgiButtonName = ""
        self.cgiButtonSuffix = ""
        self.cgiButtonMultiple = False

        for wsKey, wsData in list(self.cgiPostDataRaw.items()):
            wsSafeKey = bzUtil.Filter(wsKey, CGI_KEY_FILTER)
            if wsSafeKey[: bzHtml.ButtonPrefixLen] == bzHtml.ButtonPrefix:
                if self.cgiButtonName == "":
                    self.cgiButtonMultiple = True
                else:
                    self.cgiButtonName = wsSafeKey[bzHtml.ButtonPrefixLen :]
        if self.cgiButtonName[-bzHtml.ButtonSuffixLen :] in bzHtml.ButtonSuffixes:
            self.cgiButtonSuffix = self.cgiButtonName[-bzHtml.ButtonSuffixLen :]
            self.cgiButtonName = self.cgiButtonName[: -bzHtml.ButtonSuffixLen]

    def FilterCgiData(self, parmUnfilteredData):
        wsFilteredData = bafNv.bafNvTuple()
        wsFilteredData.AssignDefaultValue(None)
        for wsKey, wsData in list(parmUnfilteredData.items()):
            wsKey = bzUtil.Filter(wsKey, bzUtil.LETTERSANDNUMBERS + "-_.")
            wsData = bzUtil.FilterMultiLineText(wsData, parmExcept="<>")
            wsFilteredData[wsKey] = wsData
        return wsFilteredData
