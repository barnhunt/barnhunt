from barnhunt.coursemaps import Layer


def test_find_layers(svg1):
    from barnhunt.coursemaps import _find_layers
    layers = _find_layers(svg1.root)
    assert len(layers) == 2
    assert layers[0].id == 'layer2'
    assert layers[1].id == 'layer'


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
        assert svg1.layer.get('style') == 'display:inline'
        assert svg1.sublayer.get('style') is None

    def test_show_merges_style(self, svg1):
        svg1.layer.set('style', 'display:none;text-align:center')
        layer = Layer(svg1.layer)
        layer.show()
        assert svg1.layer.get('style') == 'text-align:center;display:inline'

    def test_show_reursive(self, svg1):
        layer = Layer(svg1.layer)
        layer.show(recursive=True)
        assert svg1.layer.get('style') == 'display:inline'
        assert svg1.sublayer.get('style') == 'display:inline'

    def test_hide(self, svg1):
        layer = Layer(svg1.layer)
        layer.hide()
        assert svg1.layer.get('style') == 'display:none'
        assert svg1.sublayer.get('style') is None

    def test_repr(self, svg1):
        layer = Layer(svg1.sublayer)
        assert repr(layer) == '<Layer sublayer>'
