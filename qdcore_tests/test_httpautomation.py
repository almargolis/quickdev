from qdcore import httpautomation

sample_1_src = """
<h1 class="what">Heading</h1>
<p>Text. <b style="size: 24px">Bold stuff.</b></p>
"""


def test_simple_html_1():
    crawler = httpautomation.Crawler()
    crawler.load_blob(sample_1_src)
    html_document = crawler.create_simple_html()
    print(html_document.render_html())
    # assert False
