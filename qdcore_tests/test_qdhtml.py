from qdcore import qdhtml


def test_basic():
    page = qdhtml.HtmlPage()
    paragraph = page.body_content.append(qdhtml.HtmlContent("p"))
    paragraph.append(["This is text. ", (qdhtml.HtmlContent("b"), "Bold text. ")])
    print(page.render_html())
    # assert False
