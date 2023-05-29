# httpautomation - idioms of requests and beutiful soup

import codecs
import bs4
from bs4 import BeautifulSoup
import os
import re
import requests
import shutil
import urllib.parse

from . import qdhtml


class bafCrawlerResponse(object):
    def __init__(self):
        self.content = None


class Crawler:
    def __init__(self, ExeController=None):
        self.exeController = ExeController
        self.findIx = 0  # last succesful find
        self.nextCharIx = 0  # start of next thing
        self.crawl_session = requests.Session()
        self.crawlCredentials = None
        self.crawl_response = None
        self.crawlPage = None  # page being analyzed
        self.crawlPageLen = 0
        self.parse_tree = None  # beutiful soup tree
        self.crawlFromCache = False
        self.savePath = None
        self.scrapeUrlsTable = None
        if self.exeController is not None:
            self.scrapeUrlsTable = self.exeController.OpenDbTable("ScrapeUrls")

    def FindNextText(self, parmText, Ix=None):
        if Ix is not None:
            self.nextCharIx = Ix  # reset even if no match
        wsIx = self.crawlPage.find(parmText, self.nextCharIx)
        if wsIx < 0:
            return False
        self.findIx = wsIx
        self.nextCharIx = wsIx + len(parmText)
        return True

    def GetElementText(self, parmElement):
        if self.FindNextText("<" + parmElement):
            if self.FindNextText(">"):
                wsStart = self.nextCharIx
                if self.FindNextText("</" + parmElement):
                    wsEnd = self.findIx
                    return self.crawlPage[wsStart:wsEnd]
        return None

    def FindHrefs(self, href, element="a"):
        elements = self.parse_tree.find_all(href=re.compile(href))
        return elements

    def FindTables(self):
        """
        Create a list of all table elements in a parse tree.

        Embedded tables are included in the list. This mainly
        is the case for tables used for layout.
        """
        tables = self.parse_tree.find_all("table")
        return tables

    def FindDataTables(self, require_headers=True):
        """
        Create a list of data tables.

        Try to eliminate tables used for layout. This won't be perfect, but may
        eliminate noise on some pages.
        """
        data_tables = []
        all_tables = self.parse_tree.find_all("table")
        for this in all_tables:
            child_table = this.find("table")
            if child_table is None:
                if require_headers:
                    header = this.find("th")
                    if header is not None:
                        # the table has at least one header cell
                        data_tables.append(this)
                else:
                    # get any table that doesn't have a child table
                    data_tables.append(this)
        return data_tables

    def FindTableContent(
        self, data_tables_only=True, require_headers=True, textize=False
    ):
        content = []
        if data_tables_only:
            tables = self.FindDataTables(require_headers=require_headers)
        else:
            tables = self.FindTables()
        for this_table in tables:
            this_table_content = []
            content.append(this_table_content)
            for this_row in this_table.find_all("tr"):
                this_row_content = []
                this_table_content.append(this_row_content)
                for this_col in this_row.find_all(["td", "th"]):
                    if textize:
                        this_row_content.append(this_col.text)
                    else:
                        this_row_content.append(this_col)
        return content

    def BFindStr(self, parmPattern, Ascii=False):
        for wsIx, this in enumerate(parmPattern):
            wsString = None
            if isinstance(this, tuple):
                wsFunction = "find"
                if len(this) > 1:
                    wsString = re.compile(this[1])
            else:
                wsFunction = this
            if wsIx == 0:
                wsResult = self.parse_tree.find(this[0], string=wsString)
                if wsResult is None:
                    return None
            else:
                if wsFunction == "sibling":
                    wsResult = wsResult.next_sibling
                elif wsFunction == "find":
                    wsResult = wsResult.find_next(this[0], string=wsString)
                else:
                    raise Exception("Unknown function type '%s'" % (wsFunction))
            print("BBB", wsFunction, wsString, wsResult)
            if wsResult is None:
                return None
            if isinstance(wsResult, bs4.element.NavigableString):
                wsResult = wsResult.strip()
            else:
                wsResult = wsResult.text.strip()
            if Ascii:
                return wsResult.encode("ascii")
            else:
                return wsResult

    def create_child_simple_html(self, html_document, parse_tree_node):
        start_new_block = True
        if parse_tree_node.name in ["div", "span"]:
            start_new_block = False
        if (parse_tree_node.name == "a") and (html_document.linkTranslator is None):
            start_new_block = False
        if start_new_block:
            html_document.push(qdhtml.HtmlContent(parse_tree_node.name))
        for this in parse_tree_node.children:
            if isinstance(this, bs4.element.Tag):
                self.create_child_simple_html(html_document, this)
            else:
                # This should be a string
                html_document.append(this.string)
        if start_new_block:
            html_document.pop()

    def create_simple_html(
        self, root_node=None, start_after=None, stop_at=None, url_translator=None
    ):
        """
        Create simplified html from a parsed page. The resulting document has no formatting
        (no css) and links (html <a>) are either converted to simple text or created with
        a translated HREF url.

        This would typlically be used to convert a scraped product page description
        to a format suitable for EBay with no external references or for your own
        product page where urls point to your own site rather than the manufacturers.
        """

        #
        # This is somewhat broken as I re-implement in 2022 as part of QucikDev
        # -- the url translator capability is gone
        # -- we might want to create a full html document instead of just a snippet
        #
        if root_node is None:
            root_node = self.parse_tree
        if root_node is None:
            return None
        html_document = qdhtml.HtmlSnippet()  # url_translator=url_translator)
        if stop_at is not None:
            wsStopFirstTag = stop_at[0]
            wsStopSecondTag = stop_at[1]
            wsStopString = stop_at[2]
        if start_after is None:
            wsStarted = True  # start from the beginning
        else:
            wsStarted = False
        wsFirstStringFound = False
        for this in root_node.children:
            if not wsStarted:
                if this is start_after:
                    wsStarted = True  # This is the price, start after this
            else:
                if stop_at is not None:
                    if isinstance(this, bs4.element.Tag):
                        if this.name == wsStopFirstTag:
                            wsCheck2 = this.contents[0]
                            if wsCheck2.name == wsStopSecondTag:
                                if wsCheck2.string.find(wsStopString) >= 0:
                                    break
            # print id(this), ": ", this.__class__.__name__, " >> ", this.name, " >> ", id(this.parent), " >> ", this
            if isinstance(this, bs4.element.Tag):
                self.create_child_simple_html(html_document, this)
            else:
                # This should be a string
                wsStr = this.string
                print("SSS", wsFirstStringFound, wsStr)
                if not wsFirstStringFound:
                    # This cleans up leading newlines and spaces that led to an empty <p> block which
                    # effects spacing. this works because AppendStr() ignores empty strings.
                    wsStr = wsStr.lstrip()
                    if wsStr != "":
                        wsFirstStringFound = True
                    html_document.append(wsStr)
        return html_document

    def GetBlob(self, Url, Scheme=None, Binary=True, Tree=False, UseCache=True):
        self.Load(Url=Url, Scheme=Scheme, Binary=Binary, Tree=Tree, UseCache=UseCache)
        return self.crawlPage

    def GetText(self, url, Scheme=None, Binary=False, Tree=False, UseCache=False):
        self.Load(url=url, Scheme=Scheme, Binary=Binary, Tree=Tree, UseCache=UseCache)
        return self.crawlPage

    def GetAndSaveBinaryFile(
        self, url, fn=None, Scheme=None, Binary=True, Tree=False, UseCache=True
    ):
        # https://stackoverflow.com/questions/16694907/download-large-file-in-python-with-requests
        # It would be nice to integrate with Load() -- but no time today
        if fn is None:
            fn = url.split("/")[-1]
        fn = os.path.abspath(os.path.expanduser(fn))
        with self.crawl_session.get(url, stream=True) as r:
            with open(fn, "wb") as f:
                shutil.copyfileobj(r.raw, f)
        return fn

    def GetAndSaveTextFile(
        self, url, fn, Scheme=None, Binary=False, Tree=False, UseCache=False
    ):
        self.Load(url=url, Scheme=Scheme, Binary=Binary, Tree=Tree, UseCache=UseCache)
        if self.savePath is None:
            wsFn = fn
        else:
            wsFn = os.path.join(self.savePath, fn)
        o = codecs.open(wsFn, mode="w", encoding="utf-8")
        o.write(self.crawlPage)
        o.close
        return self.crawlPage

    #
    def website_login(self, credentials):
        self.crawlCredentials = credentials
        self.Load(
            url=credentials.login_page_url,
            Data=None,
            DataGet=True,
            Tree=True,
            UseCache=False,
        )
        forms = self.parse_tree.find_all("form")
        login_form = forms[0]
        form_action = urllib.parse.urljoin(
            credentials.login_page_url, login_form["action"]
        )
        form_method = login_form["method"]
        if form_method == "post":
            form_data_get = False
        else:
            form_data_get = True
        submit_field = None
        login_fields = login_form.find_all("input")
        login_data = {}
        input_fields = []
        for this in login_fields:
            print(this)
            this_field_name = this["name"]
            if this["type"] == "hidden":
                login_data[this_field_name] = this["value"]
            elif this["type"] == "submit":
                assert submit_field is None
                submit_field = this
                login_data[this_field_name] = this["value"]
            else:
                input_fields.append(this_field_name)
        credentials.get_login_data(login_data, input_fields)
        print(login_data)
        self.Load(
            url=form_action,
            Data=login_data,
            DataGet=form_data_get,
            Tree=True,
            UseCache=False,
        )
        print(self.crawl_responseCode)
        print(self.crawlPage)

    def load_blob(self, blob, Tree=True):
        self.crawlPage = blob
        if Tree:
            self.parse_tree = BeautifulSoup(self.crawlPage, "lxml")
        else:
            self.parse_tree = None
        if self.parse_tree is None:
            return False
        else:
            return True

    def LoadFile(self, filename, Tree=True):
        with open(filename, "r", encoding="utf8") as f:
            blob = f.read()
        self.LoadBlob(blob, Tree=Tree)

    def Load(
        self,
        url=None,
        Scheme=None,
        Binary=False,
        Data=None,
        DataGet=False,
        start_after=None,
        Tree=True,
        ScrapeUrlsUdi=None,
        UseCache=False,
    ):
        """
        Load a url.

        ScrapeUrlsUdi and UseCache support a accessing recently retrived urls from a
        cache database. This makes web crawlers and scrapers more efficient.
        """
        # Need to add code to handle redirects
        if Scheme is None:
            fqn_url = url
        else:
            wsPos = url.find(":")
            if wsPos >= 0:
                url = url[wsPos + 1 :]
            fqn_url = Scheme + ":" + url
        if ScrapeUrlsUdi is not None:
            wsScrapeUrlRecord = self.scrapeUrlsTable.LookupTuple("Udi", ScrapeUrlsUdi)
        elif UseCache:
            wsScrapeUrlRecord = self.scrapeUrlsTable.LookupTuple("Url", fqn_url)
        else:
            wsScrapeUrlRecord = None
        if wsScrapeUrlRecord is not None:
            self.crawlFromCache = True
            wsScrapeUdi = wsScrapeUrlRecord["Udi"]
            wsScrapeContentFileName = "C" + bzUtil.Str(wsScrapeUdi)
            self.crawl_response = bafCrawlerResponse()
            wsF = open("/exports/Catalog/Scrape/" + wsScrapeContentFileName, "rb")
            self.crawl_response.content = wsF.read()
            self.crawl_response.url = wsScrapeUrlRecord["Url"]
            self.crawl_responseCode = wsScrapeUrlRecord["ResponseCode"]
            wsF.close()
            if Binary:
                self.crawlPage = self.crawl_response.content
            else:
                self.crawlPage = self.crawl_response.content.decode("utf-8")
        else:
            self.crawlFromCache = False
            if (Data is None) or DataGet:
                self.crawl_response = self.crawl_session.get(fqn_url, params=Data)
            else:
                self.crawl_response = self.crawl_session.post(fqn_url, data=Data)
            self.crawl_responseCode = self.crawl_response.status_code
            if UseCache and (self.crawl_responseCode == 200):
                wsScrapeUrlRecord = {
                    "Url": fqn_url,
                    "ResponseCode": self.crawl_responseCode,
                }
                if not self.scrapeUrlsTable.Post(wsScrapeUrlRecord):
                    self.exeController.errs.AddDevCriticalMessage(
                        "Unable to Post() %s %s "
                        % (fqn_url, self.scrapeUrlsTable._lastErrorMsg)
                    )
                    return False
                wsScrapeUdi = wsScrapeUrlRecord["Udi"]
                wsScrapeContentFileName = "C" + bzUtil.Str(wsScrapeUdi)
                wsF = open("/exports/Catalog/Scrape/" + wsScrapeContentFileName, "wb")
                wsF.write(self.crawl_response.content)
                wsF.close()
        if Binary:
            self.crawlPage = self.crawl_response.content
        else:
            self.crawlPage = self.crawl_response.content.decode("utf-8")
        self.crawlPageLen = len(self.crawlPage)
        self.nextCharIx = 0
        if self.crawlPageLen < 1:
            return False
        if start_after is not None:
            return self.FindNextText(start_after)
        if Tree:
            self.parse_tree = BeautifulSoup(self.crawlPage, "lxml")
        else:
            self.parse_tree = None
        return True


class HttpCredentials(object):
    __slots__ = (
        "login_page_url",
        "user_id",
        "user_id_field_name",
        "password",
        "password_field_name",
    )

    def __init__(self, user_id, password, login_page_url=None):
        self.user_id = user_id
        self.user_id_field_name = None
        self.password = password
        self.password_field_name = None
        self.login_page_url = login_page_url

    def get_login_data(self, login_data, input_fields):
        def match_field(form_field_name, fragments):
            mname = form_field_name.lower()
            for this in fragments:
                if mname.find(this) >= 0:
                    return True
            return False

        def put_field(form_field_name):
            assert form_field_name not in login_data
            if self.password_field_name is None:
                if match_field(form_field_name, ["pass"]):
                    self.password_field_name = form_field_name
            if self.password_field_name is not None:
                if self.password_field_name == form_field_name:
                    login_data[form_field_name] = self.password
                    return
            if self.user_id_field_name is None:
                if match_field(form_field_name, ["name", "id", "email"]):
                    self.user_id_field_name = form_field_name
            if self.user_id_field_name is not None:
                if self.user_id_field_name == form_field_name:
                    login_data[form_field_name] = self.user_id
                    return
            assert False, "Unknown login form field '{}'".format(form_field_name)

        for this in input_fields:
            put_field(this)


class HttpAutomate(object):
    __slots__ = (
        "crawler",
        "login_credentials",
    )

    def __init__(self, login_credentials=None):
        self.crawler = Crawler()
        self.login_credentials = login_credentials

    def login(self):
        self.crawler.website_login(self.login_credentials)
