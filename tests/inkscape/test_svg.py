from io import BytesIO

from lxml import etree
import pytest

from barnhunt.inkscape import svg


XML1 = b'''<root xmlns:foo="urn:example:foo">
  <a foo:attr="bar"><aa><aaa/></aa></a>
  <b/>
</root>'''


@pytest.fixture
def tree1():
    return etree.parse(BytesIO(XML1))


class Test_copy_etree(object):
    def test_copy(self, tree1):
        copy1 = svg.copy_etree(tree1)
        assert etree.tostring(copy1) == etree.tostring(tree1)
        assert copy1 is not tree1
        assert copy1.getroot() is not tree1.getroot()

    def test_update_nsmap(self, tree1):
        copy1 = svg.copy_etree(tree1,
                               update_nsmap={'bar': 'urn:example:bar'})
        copy1.find('b').set('{urn:example:bar}y', 'z')
        assert b'<b bar:y="z"/>' in etree.tostring(copy1)

    def test_omit_elements(self, tree1):
        copy1 = svg.copy_etree(tree1, omit_elements=(tree1.find('aa')))
        assert copy1.find('aa') is None
        assert copy1.find('aaa') is None
