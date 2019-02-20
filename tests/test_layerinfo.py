from itertools import islice

import pytest
from six import string_types

from barnhunt import layerinfo
from barnhunt.layerinfo import (
    dwim_layer_info,
    CompatLayerInfo,
    FlaggedLayerInfo,
    LayerFlags,
    )
from barnhunt.inkscape import svg


def get_by_id(tree, id):
    matches = tree.xpath('//*[@id="%s"]' % id)
    assert len(matches) <= 1
    return matches[0] if matches else None

    getroot = getattr(tree, 'getroot', None)
    root = getroot() if getroot else tree
    if root.get('id') == id:
        return root
    return root.find('.//*[@id="%s"]' % id)


class DummyElem(object):
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

    def __eq__(self, other):
        if isinstance(other, string_types):
            # NB: doesn't check children
            return self.label == other
        # NB: visible is ignored
        return self.label == other.label and self.children == other.children

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.label)

    def __repr__(self):
        if self.children:
            return "<%s: %r %r>" % (self.__class__.__name__,
                                    self.label, self.children)
        return "<%s: %r>" % (self.__class__.__name__, self.label)


class DummyETree(object):
    def __init__(self, root):
        self.root = root

    def getroot(self):
        return self.root


def dummy_etree(layers):
    return DummyETree(root=DummyElem(children=layers))


class DummySvg(object):
    @staticmethod
    def copy_etree(tree, omit_elements):
        def copy_elem(elem):
            children = [copy_elem(child) for child in elem.children
                        if child not in omit_elements]
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
        for node, children in cls.walk_layers2(elem):
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
        if not attr.startswith('_'):
            monkeypatch.setattr(svg, attr, getattr(dummy_svg, attr))
    return dummy_svg


@pytest.mark.parametrize('s, flags', [
    ("", LayerFlags(0)),
    ("h", LayerFlags.HIDDEN),
    ("o", LayerFlags.OVERLAY),
    ("ho", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ("hoo", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ("oh", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ])
def test_layerflags_parse(s, flags):
    assert LayerFlags.parse(s) == flags


def test_layerflags_parse_warns(caplog):
    assert LayerFlags.parse("hx") == LayerFlags.HIDDEN
    assert "unknown character" in caplog.text


@pytest.mark.parametrize('s, flags', [
    ("", LayerFlags(0)),
    ("h", LayerFlags.HIDDEN),
    ("o", LayerFlags.OVERLAY),
    ("ho", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ])
def test_layerflags_str(s, flags):
    assert set(str(flags)) == set(s)


@pytest.mark.parametrize('predicate_name, expected_ids', [
    ('is_ring', [
        'ring',
        ]),
    ('is_course', [
        't1novice',
        't1master',
        ]),
    ('is_cruft', [
        'cruft',
        ]),
    ('is_overlay', [
        'blind1',
        'build',
        ]),
    ])
def test_predicate(predicate_name, coursemap1, expected_ids):
    predicate = getattr(layerinfo, predicate_name)
    tree = coursemap1.tree
    matches = set(elem for elem in tree.iter() if predicate(elem))
    expected = set(get_by_id(tree, id) for id in expected_ids)
    assert matches == expected


@pytest.mark.parametrize('layer_label, label, flags, output_basename', [
    ('[h] Hidden', "Hidden", LayerFlags.HIDDEN, None),
    ('[o] An Overlay', "An Overlay", LayerFlags.OVERLAY, None),
    ('Plain Jane', "Plain Jane", LayerFlags(0), None),
    ('[o|foo] Another Overlay', "Another Overlay", LayerFlags.OVERLAY, "foo"),
    ])
@pytest.mark.usefixtures('dummy_svg')
def test_FlaggedLayerInfo(layer_label, label, flags, output_basename):
    elem = DummyElem(layer_label)
    info = FlaggedLayerInfo(elem)
    assert info.elem is elem
    assert info.label == label
    assert info.flags is flags
    assert info.output_basename == output_basename


@pytest.mark.usefixtures('dummy_svg')
class TestCompatLayerInfo(object):
    @pytest.mark.parametrize('label, flags', [
        ('Prototypes', LayerFlags.HIDDEN),
        ('Master 1', LayerFlags.OVERLAY),
        ('Test Ring', LayerFlags(0)),
        ])
    def test_init(self, label, flags):
        elem = DummyElem(label)
        info = CompatLayerInfo(elem)
        assert info.elem is elem
        assert info.label == label
        assert info.flags is flags

    def test_overlay(self):
        overlay = DummyElem("Test ovl")
        not_overlay = DummyElem("Test not ovl")
        DummyElem(children=[
            DummyElem("Master 2", [
                DummyElem("Overlays", [overlay]),
                DummyElem("Stuff", [not_overlay]),
                ]),
            ])

        info = CompatLayerInfo(overlay)
        assert info.flags is LayerFlags.OVERLAY

        info = CompatLayerInfo(not_overlay)
        assert info.flags is LayerFlags(0)


@pytest.mark.usefixtures('dummy_svg')
class Test_dwim_layer_info(object):
    @pytest.fixture
    def dummy_tree(self, leaf_label_1):
        Elem = DummyElem
        root = Elem(children=[
            Elem("Layer", [Elem(leaf_label_1)]),
            ])
        return DummyETree(root)

    @pytest.mark.parametrize('leaf_label_1', ["[h] Hidden"])
    def test_flagged_info(self, dummy_tree):
        assert dwim_layer_info(dummy_tree) is FlaggedLayerInfo

    @pytest.mark.parametrize('leaf_label_1', ["Not Flagged"])
    def test_compat_info(self, dummy_tree):
        assert dwim_layer_info(dummy_tree) is CompatLayerInfo
