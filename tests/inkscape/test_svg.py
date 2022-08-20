from io import BytesIO

import pytest
from lxml import etree

from barnhunt.inkscape import svg


XML1 = b"""<root xmlns:foo="urn:example:foo">
  <a foo:attr="bar"><aa><aaa/></aa></a>
  <b/>
</root>"""


@pytest.fixture
def tree1():
    return etree.parse(BytesIO(XML1))


SVG1 = b"""<svg xmlns:test="http://dairiki.org/testing"
                xmlns:bh="http://dairiki.org/barnhunt/inkscape-extensions"
                xmlns="http://www.w3.org/2000/svg"
                test:attr="test attr value"
                bh:random-seed="42"></svg>"""


@pytest.fixture
def svgtree1():
    return etree.parse(BytesIO(SVG1))


def test_is_layer(coursemap1):
    tree = coursemap1.tree
    matches = set(filter(svg.is_layer, tree.iter()))
    assert {elem.get("id") for elem in matches} == {
        "t1novice",
        "t1master",
        "overlays",
        "blind1",
        "build",
        "ring",
        "cruft",
    }


def test_lineage(coursemap1):
    assert list(svg.lineage(coursemap1.overlays)) == [
        coursemap1.overlays,
        coursemap1.t1master,
        coursemap1.root,
    ]


def test_walk_layers(coursemap1):
    layers = list(svg.walk_layers(coursemap1.root))
    ids = [layer.get("id") for layer in layers]
    assert ids == [
        "t1novice",
        "t1master",
        "overlays",
        "build",
        "blind1",
        "ring",
        "cruft",
    ]


def test_walk_layers2(coursemap1):
    layers = []
    for elem, children in svg.walk_layers2(coursemap1.root):
        layers.append(elem)
        if elem.get("id") in ("t1master", "cruft"):
            children[:] = []
    assert [layer.get("id") for layer in layers] == [
        "t1novice",
        "t1master",
        "ring",
        "cruft",
    ]


def test_parent_layer(coursemap1):
    assert svg.parent_layer(coursemap1.t1master) is None
    assert svg.parent_layer(coursemap1.overlays) is coursemap1.t1master
    assert svg.parent_layer(coursemap1.ring_leaf) is coursemap1.ring


@pytest.mark.parametrize(
    "style, expected",
    [
        ("display:none", "display:inline;"),
        ("display:none; text-align:center;", "text-align:center;display:inline;"),
        ("display:hidden", "display:hidden"),
        (None, None),
    ],
)
def test_ensure_visible(style, expected):
    attrib = {"style": style} if style is not None else {}
    elem = etree.Element("g", attrib=attrib)
    svg.ensure_visible(elem)
    assert elem.get("style") == expected


def test_layer_label(coursemap1):
    assert svg.layer_label(coursemap1.cruft) == "Cruft"


class Test_copy_etree:
    def test_copy(self, tree1):
        copy1 = svg.copy_etree(tree1)
        assert etree.tostring(copy1) == etree.tostring(tree1)
        assert copy1 is not tree1
        assert copy1.getroot() is not tree1.getroot()

    def test_update_nsmap(self, tree1):
        copy1 = svg.copy_etree(tree1, update_nsmap={"bar": "urn:example:bar"})
        copy1.find("b").set("{urn:example:bar}y", "z")
        assert b'<b bar:y="z"/>' in etree.tostring(copy1)

    def test_omit_elements(self, tree1):
        copy1 = svg.copy_etree(tree1, omit_elements=(tree1.find("aa")))
        assert copy1.find("aa") is None
        assert copy1.find("aaa") is None


@pytest.mark.parametrize(
    "attr, expect",
    [
        ("attr", "test attr value"),
        ("unknown", "DEFVAL"),
    ],
)
def test_get_svg_attrib(svgtree1, attr, expect):
    attr = etree.QName("http://dairiki.org/testing", attr)
    assert svg.get_svg_attrib(svgtree1, attr, "DEFVAL") == expect


def test_get_svg_attrib_raises_value_error(tree1):
    with pytest.raises(ValueError):
        svg.get_svg_attrib(tree1, "attr")


def test_set_svg_attrib(svgtree1):
    attr = etree.QName("http://dairiki.org/testing", "newattr")
    svg.set_svg_attrib(svgtree1, attr, "new value")
    assert svgtree1.getroot().get(attr) == "new value"


def test_set_svg_attrib_raises_value_error(tree1):
    with pytest.raises(ValueError):
        svg.set_svg_attrib(tree1, "attr", "value")


def test_get_random_seed(svgtree1):
    assert svg.get_random_seed(svgtree1) == 42


def test_get_random_seed_default(svgtree1):
    del svgtree1.getroot().attrib[svg.BH_RANDOM_SEED]
    assert svg.get_random_seed(svgtree1, "missing") == "missing"


def test_get_random_seed_raise_value_error(svgtree1):
    svgtree1.getroot().attrib[svg.BH_RANDOM_SEED] = "not an int"
    with pytest.raises(ValueError) as excinfo:
        svg.get_random_seed(svgtree1)
    assert "Expected integer" in str(excinfo.value)


def test_set_random_seed(svgtree1):
    svg.set_random_seed(svgtree1, 42)
    assert svgtree1.getroot().attrib[svg.BH_RANDOM_SEED] == "42"


def test_set_random_seed_raises_value_error(svgtree1):
    with pytest.raises(ValueError):
        svg.set_random_seed(svgtree1, "42")
