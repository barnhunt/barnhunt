import os
from io import BytesIO
from itertools import islice

import pytest
from lxml import etree

from barnhunt.coursemaps import _hash_dev_ino
from barnhunt.coursemaps import CourseMaps
from barnhunt.coursemaps import iter_coursemaps
from barnhunt.coursemaps import TemplateRenderer
from barnhunt.inkscape import svg
from barnhunt.layerinfo import FlaggedLayerInfo


def get_by_id(tree, id):
    matches = tree.xpath(f'//*[@id="{id}"]')
    assert len(matches) <= 1
    return matches[0] if matches else None

    getroot = getattr(tree, "getroot", None)
    root = getroot() if getroot else tree
    if root.get("id") == id:
        return root
    return root.find(f'.//*[@id="{id}"]')


@pytest.fixture
def template_renderer():
    return TemplateRenderer(FlaggedLayerInfo)


@pytest.mark.parametrize("hidden", [True, False])
def test_render_templates(template_renderer, hidden):
    repls = svg.NSMAP.copy()
    repls["flags"] = "[h] " if hidden else ""
    xml = (
        """<g xmlns="%(svg)s" xmlns:inkscape="%(inkscape)s"
                inkscape:groupmode="layer"
                inkscape:label="%(flags)sJunk">
               <tspan>{{ somevar }}</tspan>
              </g>"""
        % repls
    )
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    result = template_renderer(tree, {"somevar": "foo"})
    expected = "{{ somevar }}" if hidden else "foo"
    assert result.getroot()[0].text == expected
    assert tree.getroot()[0].text == "{{ somevar }}"


def test_render_templates_failure(template_renderer, caplog):
    xml = '<tspan xmlns="%(svg)s">{{ foo() }}</tspan>' % svg.NSMAP
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    result = template_renderer(tree, {})
    assert result.getroot().text == "{{ foo() }}"
    assert "'foo' is undefined" in caplog.text


def test_is_hidden(template_renderer):
    layer = etree.Element(
        svg.SVG_G_TAG,
        attrib={
            "id": "layer",
            svg.INKSCAPE_GROUPMODE: "layer",
            svg.INKSCAPE_LABEL: "[h] Layer",
        },
    )
    elem = etree.SubElement(layer, svg.SVG_TSPAN_TAG)
    assert template_renderer._is_hidden(elem)


def test_is_hidden_layer(template_renderer):
    elem = etree.Element(
        svg.SVG_G_TAG,
        attrib={
            "id": "layer",
            svg.INKSCAPE_GROUPMODE: "layer",
            svg.INKSCAPE_LABEL: "[h] Layer",
        },
    )
    assert template_renderer._is_hidden_layer(elem)


def test_is_hidden_layer_not_layer(template_renderer):
    elem = etree.Element(
        svg.SVG_G_TAG,
        attrib={
            "id": "non-layer",
            svg.INKSCAPE_GROUPMODE: "non-layer",
            svg.INKSCAPE_LABEL: "[h] Layer",
        },
    )
    assert not template_renderer._is_hidden_layer(elem)


def test_is_hidden_layer_not_hidden(template_renderer):
    elem = etree.Element(
        svg.SVG_G_TAG,
        attrib={
            "id": "layer",
            svg.INKSCAPE_GROUPMODE: "layer",
            svg.INKSCAPE_LABEL: "[o] Layer",
        },
    )
    assert not template_renderer._is_hidden_layer(elem)


def test_get_local_context(template_renderer):
    xml = (
        """<g xmlns="%(svg)s"
                xmlns:inkscape="%(inkscape)s"
                inkscape:groupmode="layer"
                inkscape:label="The Layer">
               <tspan>{{ layer.label }}</tspan>
             </g>"""
        % svg.NSMAP
    )
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    tspan = tree.getroot()[0]
    context = template_renderer._get_local_context(tspan, dict(foo="bar"))
    assert context["foo"] == "bar"
    assert context["layer"].label == "The Layer"


class DummyElem:
    parent = None

    def __init__(self, label=None, children=None, visible=None):
        if children is None:
            children = []
        else:
            for child in children:
                assert child.parent is None
                child.parent = self
        self.label = label
        self.children = children
        self.visible = True

    def get(self, attr, dflt=None):
        if attr == "id":
            return self.label.lower()
        return dflt

    def getparent(self):
        return self.parent

    def __eq__(self, other):
        if isinstance(other, str):
            # NB: doesn't check children
            return self.label == other
        # NB: visible is ignored
        return self.label == other.label and self.children == other.children

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.label)

    def __iter__(self):
        return iter(self.children)

    def __repr__(self):
        if self.children:
            detail = f"{self.label!r} {self.children!r}"
        else:
            detail = repr(self.label)
        return f"<{self.__class__.__name__}: {detail}>"


class DummyETree:
    def __init__(self, root):
        self.root = root

    def getroot(self):
        return self.root


def dummy_etree(layers):
    return DummyETree(root=DummyElem(children=layers))


class DummySvg:
    @staticmethod
    def copy_etree(tree, omit_elements):
        def copy_elem(elem):
            children = [
                copy_elem(child)
                for child in elem.children
                if child not in omit_elements
            ]
            return DummyElem(elem.label, children, elem.visible)

        return DummyETree(root=copy_elem(tree.getroot()))

    @staticmethod
    def ensure_visible(elem):
        elem.visible = True

    @staticmethod
    def is_layer(elem):
        return elem.label is not None

    @staticmethod
    def layer_label(elem):
        return elem.label

    @classmethod
    def parent_layer(cls, elem):
        for parent in islice(cls.lineage(elem), 1, None):
            if cls.is_layer(parent):
                return parent

    @staticmethod
    def lineage(elem):
        while elem is not None:
            yield elem
            elem = elem.parent

    @classmethod
    def walk_layers(cls, elem):
        for node, _children in cls.walk_layers2(elem):
            yield node

    @staticmethod
    def walk_layers2(elem):
        nodes = list(elem.children)
        while nodes:
            node = nodes.pop(0)
            children = list(node.children)
            yield node, children
            nodes[0:0] = children


@pytest.fixture
def dummy_svg(monkeypatch):
    dummy_svg = DummySvg()
    for attr in dir(dummy_svg):
        if not attr.startswith("_"):
            monkeypatch.setattr(svg, attr, getattr(dummy_svg, attr))
    return dummy_svg


@pytest.mark.usefixtures("dummy_svg")
class TestCourseMaps:
    @pytest.fixture
    def coursemaps(self):
        return CourseMaps(layer_info=FlaggedLayerInfo)

    @pytest.fixture
    def dummy_tree(self):
        Elem = DummyElem
        root = Elem(
            children=[
                Elem("[h] Hidden", [Elem("Hidden Child")]),
                Elem(
                    "Child",
                    [
                        Elem(
                            "[o] Overlay 1",
                            [
                                Elem("[o] Overlay 1.1"),
                                Elem("[h] Hidden 1.2"),
                                Elem("[o] Overlay 1.3"),
                            ],
                        ),
                    ],
                ),
                Elem(
                    "[o] Overlay 2",
                    [
                        Elem("[o] Overlay 2.1"),
                    ],
                ),
                Elem(
                    "Test",
                    [
                        Elem("[!base]Not in base"),
                    ],
                ),
            ]
        )
        return DummyETree(root)

    def test_init_with_context(self):
        coursemaps = CourseMaps(layer_info=FlaggedLayerInfo, context={"foo": "bar"})
        assert coursemaps.context["foo"] == "bar"

    def test_call(self, coursemaps):
        Elem = DummyElem
        tree = DummyETree(
            root=Elem(
                children=[
                    Elem("[h] Hidden", [Elem("Hidden Child")]),
                    Elem("Layer", [Elem("Child")]),
                ]
            )
        )
        result = list(coursemaps(tree))
        assert len(result) == 1
        context, pruned = result[0]
        assert context == {"course": None, "overlay": None, "overlays": ()}
        assert pruned.root.children == [Elem("Layer", [Elem("Child")])]

        for layer in svg.walk_layers(pruned.root):
            assert layer.visible is True

    def test_get_context_no_overlays(self, coursemaps):
        path = []
        context = coursemaps._get_context(path)
        assert context["course"] is None
        assert context["overlay"] is None

    def test_get_context_one_overlay(self, coursemaps):
        path = [DummyElem("[o] Foo")]
        context = coursemaps._get_context(path)
        assert len(context["overlays"]) == 1
        assert context["course"].label == "Foo"
        assert context["overlay"] is None

    def test_iter_overlays(self, coursemaps, dummy_tree):
        root = dummy_tree.getroot()
        result = list(coursemaps._iter_overlays(root))
        assert result == [
            (
                ["[o] Overlay 1", "[o] Overlay 1.1"],
                {"[h] Hidden", "[h] Hidden 1.2", "[o] Overlay 1.3", "[o] Overlay 2"},
            ),
            (
                ["[o] Overlay 1", "[o] Overlay 1.3"],
                {"[h] Hidden", "[o] Overlay 1.1", "[h] Hidden 1.2", "[o] Overlay 2"},
            ),
            (["[o] Overlay 2", "[o] Overlay 2.1"], {"[h] Hidden", "[o] Overlay 1"}),
        ]

    @pytest.mark.parametrize(
        "output_basename, exclusions",
        [
            ("base", {"[!base]Not in base"}),
            ("notbase", set()),
        ],
    )
    def test_find_exclusions(self, coursemaps, dummy_tree, output_basename, exclusions):
        root = dummy_tree.getroot()
        result = set(coursemaps._find_exclusions(output_basename, root))
        assert result == exclusions

    @pytest.mark.usefixtures("dummy_svg")
    def test_find_overlays(self, coursemaps, dummy_tree):
        root = dummy_tree.getroot()
        overlays, cruft = coursemaps._find_overlays(root)
        assert overlays == ["[o] Overlay 1", "[o] Overlay 2"]
        assert cruft == {"[h] Hidden"}


def test_hash_dev_ino():
    with open(__file__, "rb") as srcfile:
        st = os.stat(__file__)
        dev_ino = st.st_dev, st.st_ino
        assert _hash_dev_ino(srcfile) == hash(dev_ino)


# XXX: more unit tests for iter_coursemaps are probably in order
def test_iter_coursemaps_warns_if_no_random_seed(caplog, drawing_svg):
    svgfiles = [drawing_svg.open("rb")]
    for _ in iter_coursemaps(svgfiles):
        pass
    assert "no random-seed" in caplog.text
