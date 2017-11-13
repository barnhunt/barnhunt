from io import BytesIO

from lxml import etree

from barnhunt.etree_util import clone_etree


def ETREE(raw_bytes):
    return etree.parse(BytesIO(raw_bytes))


def test_clone():
    tree = ETREE(b'''
    <root xmlns:foo="http://example.com/">
    <a foo:attr="x"/>
    </root>''')

    clone = clone_etree(tree)
    assert etree.tostring(clone) == etree.tostring(tree)


def test_augment_nsmap():
    tree = ETREE(b'<root><a/></root>')
    nsmap = {'x': 'http://example.com/#x'}
    clone = clone_etree(tree, update_nsmap=nsmap)
    clone.find('a').set('{http://example.com/#x}y', 'z')
    assert etree.tostring(clone) \
        == b'<root xmlns:x="http://example.com/#x"><a x:y="z"/></root>'


def test_prune():
    tree = ETREE(b'<root><a/><b><c/></b></root>')
    clone = clone_etree(tree, prune_p=lambda elem: elem.tag == 'b')
    assert etree.tostring(clone) == b'<root><a/></root>'
