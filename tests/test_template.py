import re

from lxml import etree
import pytest

from barnhunt.template import Layer, TemplateExpander
from barnhunt import rats

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"
BH = "{http://www.dairiki.org/schema/barnhunt}"


def test_is_layer(svg1):
    from barnhunt.template import _is_layer

    assert not _is_layer(svg1.root)
    assert not _is_layer(svg1.leaf)
    assert _is_layer(svg1.layer)
    assert _is_layer(svg1.sublayer)


def test_find_containing_layer(svg1):
    from barnhunt.template import _find_containing_layer

    assert _find_containing_layer(svg1.root) is None
    assert _find_containing_layer(svg1.layer) is None
    assert _find_containing_layer(svg1.sublayer) is svg1.layer
    assert _find_containing_layer(svg1.leaf) is svg1.sublayer


class TestLayer(object):
    def test_id(self, svg1):
        assert Layer(svg1.layer).id == 'layer'

    def test_label(self, svg1):
        assert Layer(svg1.sublayer).label == 'Level 2'

    def test_parent(self, svg1):
        assert Layer(svg1.layer).parent is None
        assert Layer(svg1.sublayer).parent.id == 'layer'

    def test_hash(self, svg1):
        layer = svg1.layer
        sublayer = svg1.sublayer
        assert hash(Layer(layer, 1)) == hash(Layer(layer, 1))
        assert hash(Layer(layer, 1)) != hash(Layer(layer, 2))
        assert hash(Layer(layer, 1)) != hash(Layer(sublayer, 1))

    def test_rats(self, svg1):
        assert Layer(svg1.layer, 1).rats() \
            == rats.random_rats(seed=hash(Layer(svg1.layer, 1)))

    def test_repr(self, svg1):
        assert repr(Layer(svg1.layer)) == "<Layer id=layer>"


class TestTemplateExpander(object):
    def test_expand(self, svg1):
        rv = TemplateExpander().expand(svg1.tree)
        assert rv.find('.//*[@id="leaf"]').text == 'Layer: Level 2'

    def test_expand_elem(self):
        elem = etree.Element('foo')
        elem.text = '{{ 1 + 2 }}'
        TemplateExpander()._expand_elem(elem)
        assert elem.text == '3'

    def test_expand_rats(self):
        expand_elem = TemplateExpander()._expand_elem
        elem = etree.Element('foo')
        elem.text = '{{ rats() | join(",") }}'
        expand_elem(elem)
        rats1 = elem.text
        assert re.match(r'\A([1-5],){4}[1-5]\Z', rats1)
        for _ in range(100):
            expand_elem(elem)
            assert re.match(r'\A([1-5],){4}[1-5]\Z', elem.text)
            if elem.text != rats1:
                break
        else:
            pytest.fail("Rat numbers are always the same")

    def test_escapage(self):
        expand_elem = TemplateExpander()._expand_elem
        elem = etree.Element('foo')
        elem.text = '{{ "ab" | join("&") }}'
        expand_elem(elem)
        assert b'>a&amp;b</' in etree.tostring(elem)

    def test_get_context(self, svg1):
        context = TemplateExpander()._get_context(svg1.leaf)
        assert context['layer'].id == 'sublayer'

    def test_is_static(self):
        is_static = TemplateExpander()._is_static
        assert is_static("Foo Bar")
        assert is_static("Foo Bar {}")
        assert not is_static("{{ some_var }}")
        assert not is_static("Foo {{ x }} Bar")
        assert not is_static("{# comment #}")
        assert not is_static("{% set x=42 %}")
