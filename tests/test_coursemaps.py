from lxml import etree
import pytest

from barnhunt.css import InlineCSS
from barnhunt.coursemaps import (
    Layer,
    is_hidden,
    prune_hidden,
    slow_is_hidden,
    )


def test_find_layers(svg1):
    from barnhunt.coursemaps import _find_layers
    layers = _find_layers(svg1.root)
    assert len(layers) == 2
    assert layers[0].id == 'layer2'
    assert layers[1].id == 'layer'


def get_display(elem):
    css = InlineCSS(elem.get('style'))
    return css.get('display')


class TestLayer(object):
    def test_id(self, svg1):
        layer = Layer(svg1.sublayer)
        assert layer.id == 'sublayer'

    def test_label(self, svg1):
        layer = Layer(svg1.layer)
        assert layer.label == 'Level 1'

    def test_sublayers(self, svg1):
        layer = Layer(svg1.layer)
        assert len(layer.sublayers) == 1
        assert layer.sublayers[0].id == 'sublayer'

    def test_show(self, svg1):
        layer = Layer(svg1.layer)
        layer.show()
        assert get_display(svg1.layer) == 'inline'
        assert svg1.sublayer.get('style') is None

    def test_show_recursive(self, svg1):
        layer = Layer(svg1.layer)
        layer.show(recursive=True)
        assert get_display(svg1.layer) == 'inline'
        assert get_display(svg1.sublayer) == 'inline'

    def test_hide(self, svg1):
        layer = Layer(svg1.layer)
        layer.hide()
        assert get_display(svg1.layer) == 'none'
        assert svg1.sublayer.get('style') is None

    def test_repr(self, svg1):
        layer = Layer(svg1.sublayer)
        assert repr(layer) == '<Layer sublayer>'


@pytest.mark.parametrize("style", [
    "display:none",
    "foo: bar; display : none ; baz:boo",
    ])
@pytest.mark.parametrize("is_hidden", [
    is_hidden,
    slow_is_hidden,
    ])
def test_is_hidden(style, is_hidden):
    attrib = {'style': style} if style is not None else {}
    elem = etree.Element('s', attrib=attrib)
    assert is_hidden(elem)


@pytest.mark.parametrize("style", [
    None,
    "",
    "display:inline",
    "foo: bar; baz:boo",
    "foo: bar; display : inline ; baz:boo",
    ])
@pytest.mark.parametrize("is_hidden", [
    is_hidden,
    slow_is_hidden,
    ])
def test_is_not_hidden(style, is_hidden):
    attrib = {'style': style} if style is not None else {}
    elem = etree.Element('s', attrib=attrib)
    assert not is_hidden(elem)


def test_prune_hidden():
    tree = etree.ElementTree()
    tree._setroot(etree.fromstring('<a><b style="display:none;"/></a>'))
    assert etree.tostring(prune_hidden(tree)) == b'<a/>'
