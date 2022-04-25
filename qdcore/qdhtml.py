from . import qddict

TAG_SNIPPET = "__snippet__"


class html_element:
    __slots__ = ("is_empty", "name")

    def __init__(self, name):
        self.name = name
        self.is_empty = False


html_elements = qddict.QdDict()
for this in ["html", "body", "b", "h1", "p"]:
    e = html_element(this)
    html_elements.append(e.name, e)


class HtmlContent:
    __slots__ = ("content", "element_def", "id", "page")

    def __init__(self, element_name, id=None, page=None):
        self.content = []
        if element_name == TAG_SNIPPET:
            self.element_def = None
        else:
            self.element_def = html_elements[element_name]
        self.id = id
        self.page = page

    def __str__(self):
        return f"HtmlContent({self.element_def.name}, id={self.id})"

    def append(self, content):
        """
        Append content to the element. The content can be either elements
        or plain text.

        The appended content can either be a single element of a collection
        of elements. If the collection is a list, all the list members are
        appended directly to the referenced element. If the collection is a
        tuple, the zeroeth tuple member is appended to the referenced element and
        all subsequent members are appended to that element.
        """
        if isinstance(content, list):
            for this in content:
                self.append(this)
            return None
        elif isinstance(content, tuple):
            sub_content = self.append_one_item(content[0])
            print("base", sub_content.__class__.__name__)
            sub_content.append(list(content[1:]))
            return sub_content
        else:
            return self.append_one_item(content)

    def append_one_item(self, content):
        if isinstance(content, HtmlContent):
            content.page = self.page
            if content.id is not None:
                self.page.ids.append(content.id, content)
        self.content.append(content)
        print("new", content)
        return content

    def render_html(self):
        if self.element_def is not None:
            if self.element_def.is_empty:
                return self.render_open()
            rout = self.render_open()
        else:
            rout = ""
        for this in self.content:
            if isinstance(this, HtmlContent):
                rout += this.render_html()
            else:
                rout += this
        if self.element_def is not None:
            rout += "</" + self.element_def.name + ">"
        return rout

    def render_open(self):
        rout = "<" + self.element_def.name
        if self.element_def.is_empty:
            rout += "/>"
        else:
            rout += ">"
        return rout


class HtmlPage:
    __slots__ = ("active_element", "body", "element_stack", "ids")

    def __init__(self, is_snippet=False):
        self.element_stack = []
        self.ids = qddict.QdDict()
        if is_snippet:
            self.body = HtmlContent(TAG_SNIPPET, page=self)
        else:
            self.body = HtmlContent("body", page=self)
        self.active_element = self.body

    def append(self, content):
        return self.active_element.append(content)

    def push(self, content):
        self.element_stack.append(self.active_element)
        self.active_element = self.active_element.append(content)
        return self.active_element

    def pop(self):
        self.active_element = self.element_stack.pop()
        return self.active_element

    def render_html(self):
        return self.body.render_html()


class HtmlSnippet(HtmlPage):
    def __init__(self):
        super().__init__(is_snippet=True)
