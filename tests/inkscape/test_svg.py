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


def test_is_layer(coursemap1):
    tree = coursemap1.tree
    matches = set(filter(svg.is_layer, tree.iter()))
    assert set(elem.get('id') for elem in matches) == set([
        't1novice',
        't1master',
        'overlays',
        'blind1',
        'build',
        'ring',
        'cruft',
        ])


def test_lineage(coursemap1):
    assert list(svg.lineage(coursemap1.overlays)) == [
        coursemap1.overlays,
        coursemap1.t1master,
        coursemap1.root,
        ]


def test_walk_layers(coursemap1):
    layers = list(svg.walk_layers(coursemap1.root))
    ids = [layer.get('id') for layer in layers]
    assert ids == [
        't1novice',
        't1master', 'overlays', 'build', 'blind1',
        'ring',
        'cruft',
        ]


def test_walk_layers2(coursemap1):
    layers = []
    for elem, children in svg.walk_layers2(coursemap1.root):
        layers.append(elem)
        if elem.get('id') in ('t1master', 'cruft'):
            children[:] = []
    assert [layer.get('id') for layer in layers] == [
        't1novice',
        't1master',
        'ring',
        'cruft',
        ]


def test_parent_layer(coursemap1):
    assert svg.parent_layer(coursemap1.t1master) is None
    assert svg.parent_layer(coursemap1.overlays) is coursemap1.t1master
    assert svg.parent_layer(coursemap1.ring_leaf) is coursemap1.ring


@pytest.mark.parametrize("style, expected", [
    ("display:none", "display:inline;"),
    ("display:none; text-align:center;", "text-align:center;display:inline;"),
    ("display:hidden", "display:hidden"),
    (None, None),
    ])
def test_ensure_visible(style, expected):
    attrib = {'style': style} if style is not None else {}
    elem = etree.Element('g', attrib=attrib)
    svg.ensure_visible(elem)
    assert elem.get('style') == expected


def test_layer_label(coursemap1):
    assert svg.layer_label(coursemap1.cruft) == "Cruft"


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
