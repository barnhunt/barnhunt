from io import BytesIO
from itertools import islice

from lxml import etree
import pytest
from six import string_types

from barnhunt import coursemaps
from barnhunt.coursemaps import (
    dwim_layer_info,
    render_templates,
    _get_local_context,
    CourseMaps,
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


def test_render_templates():
    xml = '<tspan xmlns="%(svg)s">{{ somevar }}</tspan>' % svg.NSMAP
    tree = etree.parse(BytesIO(xml.encode('utf-8')))
    result = render_templates(tree, {'somevar': 'foo'})
    assert result.getroot().text == 'foo'
    assert tree.getroot().text == '{{ somevar }}'


def test_render_templates_failure(caplog):
    xml = '<tspan xmlns="%(svg)s">{{ foo() }}</tspan>' % svg.NSMAP
    tree = etree.parse(BytesIO(xml.encode('utf-8')))
    result = render_templates(tree, {})
    assert result.getroot().text == '{{ foo() }}'
    assert "'foo' is undefined" in caplog.text


def test_get_local_context():
    xml = '''<g xmlns="%(svg)s"
                xmlns:inkscape="%(inkscape)s"
                inkscape:groupmode="layer"
                inkscape:label="The Layer">
               <tspan>{{ layer.label }}</tspan>
             </g>''' % svg.NSMAP
    tree = etree.parse(BytesIO(xml.encode('utf-8')))
    tspan = tree.getroot()[0]
    context = _get_local_context(tspan, dict(foo='bar'))
    assert context['foo'] == 'bar'
    assert context['layer'].label == 'The Layer'


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


@pytest.mark.usefixtures('dummy_svg')
class TestCourseMaps(object):
    @pytest.fixture
    def coursemaps(self):
        return CourseMaps(layer_info=FlaggedLayerInfo)

    @pytest.fixture
    def dummy_tree(self):
        Elem = DummyElem
        root = Elem(children=[
            Elem("[h] Hidden", [Elem("Hidden Child")]),
            Elem("Child", [
                Elem("[o] Overlay 1", [
                    Elem("[o] Overlay 1.1"),
                    Elem("[h] Hidden 1.2"),
                    Elem("[o] Overlay 1.3"),
                    ]),
                ]),
            Elem("[o] Overlay 2", [
                Elem("[o] Overlay 2.1"),
                ])
            ])
        return DummyETree(root)

    def test_init_with_context(self):
        coursemaps = CourseMaps(layer_info=FlaggedLayerInfo,
                                context={'foo': 'bar'})
        assert coursemaps.context['foo'] == 'bar'

    def test_call(self, coursemaps):
        Elem = DummyElem
        tree = DummyETree(
            root=Elem(children=[
                Elem("[h] Hidden", [Elem("Hidden Child")]),
                Elem("Layer", [Elem("Child")]),
                ])
            )
        result = list(coursemaps(tree))
        assert len(result) == 1
        context, pruned = result[0]
        assert context == {'course': None, 'overlay': None}
        assert pruned.root.children == [Elem("Layer", [Elem("Child")])]

        for layer in svg.walk_layers(pruned.root):
            assert layer.visible is True

    def test_get_context_no_overlays(self, coursemaps):
        path = []
        context = coursemaps._get_context(path)
        assert context['course'] is None
        assert context['overlay'] is None

    def test_get_context_one_overlay(self, coursemaps):
        path = [DummyElem("Foo")]
        context = coursemaps._get_context(path)
        assert context['course'].label == "Foo"
        assert context['overlay'] is None

    def test_get_context_nested_overlay(self, coursemaps):
        path = [DummyElem("Foo"), DummyElem("Bar")]
        context = coursemaps._get_context(path)
        assert context['course'].label == "Foo"
        assert context['overlay'].label == "Bar"

    def test_iter_overlays(self, coursemaps, dummy_tree):
        root = dummy_tree.getroot()
        result = list(coursemaps._iter_overlays(root))
        assert result == [
            (
                ["[o] Overlay 1", "[o] Overlay 1.1"],
                set(["[h] Hidden", "[h] Hidden 1.2", "[o] Overlay 1.3",
                     "[o] Overlay 2"])
                ),
            (
                ["[o] Overlay 1", "[o] Overlay 1.3"],
                set(["[h] Hidden", "[o] Overlay 1.1", "[h] Hidden 1.2",
                     "[o] Overlay 2"])
                ),
            (
                ["[o] Overlay 2", "[o] Overlay 2.1"],
                set(["[h] Hidden", "[o] Overlay 1"])
                ),
            ]

    @pytest.mark.usefixtures('dummy_svg')
    def test_find_overlays(self, coursemaps, dummy_tree):
        root = dummy_tree.getroot()
        overlays, cruft = coursemaps._find_overlays(root)
        assert overlays == ["[o] Overlay 1", "[o] Overlay 2"]
        assert cruft == set(["[h] Hidden"])


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
    assert str(flags) == s


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
    predicate = getattr(coursemaps, predicate_name)
    tree = coursemap1.tree
    matches = set(elem for elem in tree.iter() if predicate(elem))
    expected = set(get_by_id(tree, id) for id in expected_ids)
    assert matches == expected


@pytest.mark.parametrize('layer_label, label, flags', [
    ('[h] Hidden', "Hidden", LayerFlags.HIDDEN),
    ('[o] An Overlay', "An Overlay", LayerFlags.OVERLAY),
    ('Plain Jane', "Plain Jane", LayerFlags(0)),
    ])
@pytest.mark.usefixtures('dummy_svg')
def test_FlaggedLayerInfo(layer_label, label, flags):
    elem = DummyElem(layer_label)
    info = FlaggedLayerInfo(elem)
    assert info.elem is elem
    assert info.label == label
    assert info.flags is flags


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
