from . import tupledata

class html_element(object):
    __slots__ = ('is_empty', 'name')
    def __init__(self, name):
        self.name = name
        self.is_empty = False

html_elements = tupledata.TupleData()
e = html_element('html')
html_elements.append(e.name, e)
e = html_element('body')
html_elements.append(e.name, e)

class HtmlContent(object):
    __slots__ = ('content', 'element_def', 'id')
    def __init__(self, element_name, page, id=None):
        self.content=[]
        self.element_def = html_elements[element_name]
        self.id = id
        if self.id is not None:
            page.ids[self.id] = self

    def append(self, content):
        self.content.append(content)
        return content

    def render_html(self):
        if self.element_def.is_empty:
            return self.render_open()
        rout = self.render_open()
        for this in self.content:
            if isinstance(this, HtmlContent):
                rout += this.render_html()
            else:
                rout += this
        rout += '</' + self.element_def.name + '>'
        return rout

    def render_open(self):
        rout = '<' + self.element_def.name
        if self.element_def.is_empty:
            rout += '/>'
        else:
            rout += '>'
        return rout

class HtmlPage(HtmlContent):
    __slots__ = ('body', 'ids')
    def __init__(self):
        self.ids = {}
        super().__init__('html', self)
        self.body = self.append(HtmlContent('body', self))
        self.body.append('Stuff')
