from . import qddict

TAG_SNIPPET = "__snippet__"


class html_element:
    __slots__ = ("is_empty", "name")

    def __init__(self, name):
        self.name = name
        self.is_empty = False


html_elements = qddict.QdDict()
for this in ["html", "body", "b", "div", "form", "h1", "label", "p"]:
    e = html_element(this)
    html_elements.append(e.name, e)
for this in ["hr", "img", "input"]:
    e = html_element(this)
    e.is_empty = True
    html_elements.append(e.name, e)


class HtmlContent:
    __slots__ = ("attrs", "content", "element_def", "id", "page")

    def __init__(self, element_name, content=None, id=None, page=None):
        self.attrs = []
        self.content = []
        if element_name == TAG_SNIPPET:
            self.element_def = None
        else:
            if element_name in html_elements:
                self.element_def = html_elements[element_name]
            else:
                raise ValueError(f"Unsupported element '<{element_name}>'")
        self.id = id
        self.page = page
        if id is not None:
            self.attrs.append(("id", id))
        self.attrs
        if content is not None:
            self.append(content)

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
        for this_attr in self.attrs:
            if isinstance(this_attr, tuple):
                rout += f' {this_attr[0]}="{this_attr[1]}"'
            else:
                rout += f" {this_attr}"  # use for "required" by HtmlInputText()
        if self.element_def.is_empty:
            rout += "/>"
        else:
            rout += ">"
        return rout


class HtmlForm(HtmlContent):
    def __init__(self, action, method="post", id=None, enctype="multipart/form-data"):
        super().__init__("form", id=id)
        self.attrs.append(("action", action))
        self.attrs.append(("method", method))
        self.attrs.append(("enctype", enctype))


class HtmlButton(HtmlContent):
    def __init__(self, value, id=None):
        super().__init__("input", id=id)
        self.attrs.append(("type", "submit"))
        self.attrs.append(("value", value))


class HtmlInputText(HtmlContent):
    def __init__(self, name, id=None):
        if id is None:
            id = name
        super().__init__("input", id=id)
        self.attrs.append(("type", "text"))
        self.attrs.append(("name", name))
        self.attrs.append("required")


class HtmlLabel(HtmlContent):
    def __init__(self, for_id, content):
        super().__init__("label", content=content)
        self.attrs.append(("for", for_id))


class HtmlPage:
    """
    This is a container for a full page or snippet of html.
    """

    __slots__ = (
        "active_element",
        "body_content",
        "html_content",
        "html_str",
        "ids",
        "is_snippet",
    )

    def __init__(self, is_snippet=False):
        self.html_str = None
        self.ids = qddict.QdDict()
        self.is_snippet = is_snippet
        if is_snippet:
            self.html_content = HtmlContent(TAG_SNIPPET, page=self)
        else:
            self.html_content = HtmlContent("html", page=self)
        self.body_content = self.html_content.append(HtmlContent("body", page=self))
        self.active_element = self.body_content

    def append_html_content(self, html_content):
        self.html_content.append(html_content)

    def render_html(self, file_path=None):
        self.html_str = ""
        if not self.is_snippet:
            self.html_str += (
                "<!DOCTYPE html>\n"  # DOCTYPE doesn't follow normal HTML pattern
            )
        self.html_str += self.html_content.render_html()
        if file_path is not None:
            f = open(file_path, "w")
            f.write(self.html_str)
            f.close()
        return self.html_str


class HtmlSnippet(HtmlPage):
    def __init__(self):
        super().__init__(is_snippet=True)
