from io import BytesIO

import pytest
from lxml import etree

from barnhunt.inkscape import svg
from testlib import get_by_id
from testlib import get_by_ids
from testlib import svg_maker

XML1 = b"""<root xmlns:foo="urn:example:foo">
  <a foo:attr="bar"><aa><aaa/></aa></a>
  <b/>
</root>"""


@pytest.fixture
def tree1() -> svg.ElementTree:
    return etree.parse(BytesIO(XML1))


SVG1 = b"""<svg xmlns:test="http://dairiki.org/testing"
                xmlns:bh="http://dairiki.org/barnhunt/inkscape-extensions"
                xmlns="http://www.w3.org/2000/svg"
                test:attr="test attr value"
                bh:random-seed="42"></svg>"""


@pytest.fixture
def svgtree1() -> svg.ElementTree:
    return etree.parse(BytesIO(SVG1))


@pytest.fixture
def coursemap1() -> svg.ElementTree:
    layer = svg_maker.layer
    text = svg_maker.text
    return svg_maker.tree(
        layer("Cruft"),
        layer("Ring", visible=False, children=[text("Ring", "ring_leaf")]),
        layer(
            "T1 Master",
            children=[
                layer(
                    "Overlays",
                    children=[
                        layer("Blind 1"),
                        layer(
                            "Build Notes",
                            children=[
                                text("Build Text"),
                            ],
                        ),
                    ],
                )
            ],
        ),
        layer("T1 Novice"),
    )


def test_is_layer(coursemap1: svg.ElementTree) -> None:
    matches = set(filter(svg.is_layer, coursemap1.iter()))
    assert {elem.get("id") for elem in matches} == {
        "t1novice",
        "t1master",
        "overlays",
        "blind1",
        "buildnotes",
        "ring",
        "cruft",
    }


def test_lineage(coursemap1: svg.ElementTree) -> None:
    overlays, t1master = get_by_ids(coursemap1, ("overlays", "t1master"))
    root = coursemap1.getroot()
    assert list(svg.lineage(overlays)) == [overlays, t1master, root]


def test_walk_layers(coursemap1: svg.ElementTree) -> None:
    layers = list(svg.walk_layers(coursemap1.getroot()))
    ids = [layer.get("id") for layer in layers]
    assert ids == [
        "t1novice",
        "t1master",
        "overlays",
        "buildnotes",
        "blind1",
        "ring",
        "cruft",
    ]


def test_walk_layers2(coursemap1: svg.ElementTree) -> None:
    layers = []
    for elem, children in svg.walk_layers2(coursemap1.getroot()):
        layers.append(elem)
        if elem.get("id") in ("t1master", "cruft"):
            children[:] = []
    assert [layer.get("id") for layer in layers] == [
        "t1novice",
        "t1master",
        "ring",
        "cruft",
    ]


def test_parent_layer(coursemap1: svg.ElementTree) -> None:
    overlays, t1master, ring, ring_leaf = get_by_ids(
        coursemap1, ("overlays", "t1master", "ring", "ring_leaf")
    )
    assert svg.parent_layer(t1master) is None
    assert svg.parent_layer(overlays) is t1master
    assert svg.parent_layer(ring_leaf) is ring


def test_ancestor_layers(coursemap1: svg.ElementTree) -> None:
    buildtext, buildnotes, overlays, t1master = get_by_ids(
        coursemap1, ("buildtext", "buildnotes", "overlays", "t1master")
    )
    assert list(svg.ancestor_layers(buildtext)) == [buildnotes, overlays, t1master]
    assert list(svg.ancestor_layers(buildnotes)) == [overlays, t1master]


def test_sibling_layers(coursemap1: svg.ElementTree) -> None:
    cruft, ring, t1master, t1novice = get_by_ids(
        coursemap1, ("cruft", "ring", "t1master", "t1novice")
    )
    assert list(svg.sibling_layers(ring)) == [cruft, t1master, t1novice]


def test_sibling_layers_no_parent(coursemap1: svg.ElementTree) -> None:
    root = coursemap1.getroot()
    assert list(svg.sibling_layers(root)) == []


@pytest.mark.parametrize(
    "style, expected",
    [
        ("display:none", "display:inline;"),
        ("display:none; text-align:center;", "text-align:center;display:inline;"),
        ("display:hidden", "display:hidden"),
        (None, None),
    ],
)
def test_ensure_visible(style: str, expected: str) -> None:
    attrib = {"style": style} if style is not None else {}
    elem = etree.Element("g", attrib=attrib)
    svg.ensure_visible(elem)
    assert elem.get("style") == expected


@pytest.mark.parametrize(
    "style, expected",
    [
        (None, "display:none;"),
        ("display:inline; text-align:center;", "text-align:center;display:none;"),
        ("display:none;text-align:center;", "display:none;text-align:center;"),
        ("display:hidden", "display:none;"),
    ],
)
def test_set_hidden(style: str, expected: str) -> None:
    attrib = {"style": style} if style is not None else {}
    elem = etree.Element("g", attrib=attrib)
    svg.set_hidden(elem)
    elem_style = elem.get("style")
    assert elem_style is not None
    assert set(elem_style.split(";")) == set(expected.split(";"))


def test_layer_label(coursemap1: svg.ElementTree) -> None:
    cruft = get_by_id(coursemap1, "cruft")
    assert svg.is_layer(cruft)
    assert svg.layer_label(cruft) == "Cruft"


def test_find_clones() -> None:
    ref = svg_maker.group(id="source")
    use = svg_maker.use(href="#source")
    tree = svg_maker.tree(svg_maker.layer("Layer 1", children=[ref, use]))
    assert list(svg.find_clones(tree)) == [(use, ref)]


def test_find_clones_ignores_clones_in_defs() -> None:
    ref = svg_maker.group(id="source")
    use = svg_maker.use(href="#source")
    tree = svg_maker.tree(
        svg_maker.defs(use),
        svg_maker.layer("Layer 1", children=[ref]),
    )
    assert list(svg.find_clones(tree)) == []


def test_find_clones_ignores_sources_in_defs() -> None:
    ref = svg_maker.group(id="source")
    use = svg_maker.use(href="#source")
    tree = svg_maker.tree(
        svg_maker.defs(ref),
        svg_maker.layer("Layer 1", children=[use]),
    )
    assert list(svg.find_clones(tree)) == []


def test_find_hidden_clones_source_layers() -> None:
    use = svg_maker.use(href="#source")
    ref = svg_maker.group(id="source")
    use2 = svg_maker.use(href="#source2")
    ref2 = svg_maker.group(id="source2")
    use3 = svg_maker.use(href="#sym")
    sym = svg_maker.group(id="sym")
    layer2 = svg_maker.layer("Layer 2", children=[ref])
    tree = svg_maker.tree(
        svg_maker.defs(sym),
        svg_maker.layer("Layer 1", children=[use, use2, use3]),
        layer2,
        svg_maker.layer("Layer 3", children=[ref2]),
    )
    assert svg.find_hidden_clone_source_layers(tree, {layer2}) == {layer2}


def test_find_hidden_clones_source_layers_skips_hidden_clones() -> None:
    use = svg_maker.use(href="#source")
    ref = svg_maker.group(id="source")
    layer1 = svg_maker.layer("Layer 1", children=[use])
    layer2 = svg_maker.layer("Layer 2", children=[ref])
    tree = svg_maker.tree(layer1, layer2)
    assert svg.find_hidden_clone_source_layers(tree, {layer1, layer2}) == set()


def test_find_hidden_clones_source_layers_follows_hidden_clones() -> None:
    use = svg_maker.use(href="#use2")
    use2 = svg_maker.use(href="#source", id="use2")
    ref = svg_maker.group(id="source")
    layer1 = svg_maker.layer("Layer 1", children=[use])
    layer2 = svg_maker.layer("Layer 2", children=[use2])
    layer3 = svg_maker.layer("Layer 3", children=[ref])
    tree = svg_maker.tree(layer1, layer2, layer3)
    hidden_clone_source_layers = svg.find_hidden_clone_source_layers(
        tree, {layer2, layer3}
    )
    assert hidden_clone_source_layers == {layer2, layer3}


class Test_copy_etree:
    def test_copy(self, tree1: svg.ElementTree) -> None:
        copy1 = svg.copy_etree(tree1)
        assert etree.tostring(copy1) == etree.tostring(tree1)
        assert copy1 is not tree1
        assert copy1.getroot() is not tree1.getroot()

    def test_update_nsmap(self, tree1: svg.ElementTree) -> None:
        copy1 = svg.copy_etree(tree1, update_nsmap={"bar": "urn:example:bar"})
        b = copy1.find("b")
        assert b is not None
        b.set("{urn:example:bar}y", "z")
        assert '<b bar:y="z"/>' in etree.tostring(copy1).decode("utf8")

    def test_omit_elements(self, tree1: svg.ElementTree) -> None:
        copy1 = svg.copy_etree(tree1, omit_elements=(tree1.find("aa")))
        assert copy1.find("aa") is None
        assert copy1.find("aaa") is None


def test_EnsureId_returns_existing_id() -> None:
    elem = svg_maker.group(id="existing-id")
    tree = svg_maker.tree(
        svg_maker.layer("Layer 1", children=[elem]),
    )
    ensure_id = svg.EnsureId(tree)
    assert ensure_id(elem) == "existing-id"


def test_EnsureId_generates_unique_id() -> None:
    elems = [svg_maker.group() for _ in range(100)]
    tree = svg_maker.tree(
        svg_maker.layer("Layer 1", children=elems),
    )
    ensure_id = svg.EnsureId(tree, mindigits=0, sparedigits=0)
    ids = [ensure_id(elem) for elem in elems]
    print(f"ids={ids!r}")
    assert len(set(ids)) == len(elems)


@pytest.mark.parametrize(
    "attr, expect",
    [
        ("attr", "test attr value"),
        ("unknown", "DEFVAL"),
    ],
)
def test_get_svg_attrib(svgtree1: svg.ElementTree, attr: str, expect: str) -> None:
    attr = etree.QName("http://dairiki.org/testing", attr).text
    assert svg.get_svg_attrib(svgtree1, attr, "DEFVAL") == expect


def test_get_svg_attrib_raises_value_error(tree1: svg.ElementTree) -> None:
    with pytest.raises(ValueError):
        svg.get_svg_attrib(tree1, "attr")


def test_set_svg_attrib(svgtree1: svg.ElementTree) -> None:
    attr = etree.QName("http://dairiki.org/testing", "newattr")
    svg.set_svg_attrib(svgtree1, attr, "new value")
    assert svgtree1.getroot().get(attr) == "new value"


def test_set_svg_attrib_raises_value_error(tree1: svg.ElementTree) -> None:
    with pytest.raises(ValueError):
        svg.set_svg_attrib(tree1, "attr", "value")


def test_get_random_seed(svgtree1: svg.ElementTree) -> None:
    assert svg.get_random_seed(svgtree1) == 42


def test_get_random_seed_default(svgtree1: svg.ElementTree) -> None:
    del svgtree1.getroot().attrib[svg.BH_RANDOM_SEED]
    assert svg.get_random_seed(svgtree1, 13) == 13


def test_get_random_seed_raise_value_error(svgtree1: svg.ElementTree) -> None:
    svgtree1.getroot().attrib[svg.BH_RANDOM_SEED] = "not an int"
    with pytest.raises(ValueError) as excinfo:
        svg.get_random_seed(svgtree1)
    assert "Expected integer" in str(excinfo.value)


def test_set_random_seed(svgtree1: svg.ElementTree) -> None:
    svg.set_random_seed(svgtree1, 43)
    assert svgtree1.getroot().attrib[svg.BH_RANDOM_SEED] == "43"


def test_set_random_seed_raises_value_error(svgtree1: svg.ElementTree) -> None:
    with pytest.raises(ValueError):
        svg.set_random_seed(svgtree1, "44")  # type: ignore[arg-type]
