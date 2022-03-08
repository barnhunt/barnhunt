import os

import jinja2
from lxml import etree
import pytest
import stat

from barnhunt.inkscape import svg
from barnhunt.templating import (
    FileAdapter,
    LayerAdapter,
    _hash_string,
    get_element_context,
    is_string_literal,
    random_rats,
    render_template,
    safepath,
    )


@pytest.fixture
def toplevel():
    elem = etree.Element(svg.SVG_G_TAG, attrib={
        'id': 'toplevel',
        svg.INKSCAPE_GROUPMODE: 'layer',
        svg.INKSCAPE_LABEL: 'Parent',
        })
    return LayerAdapter(elem)


@pytest.fixture
def overlay(toplevel):
    elem = etree.SubElement(toplevel.elem, svg.SVG_G_TAG, attrib={
        'id': 'overlay',
        svg.INKSCAPE_GROUPMODE: 'layer',
        svg.INKSCAPE_LABEL: '[o|somefile] Overlay',
        })
    return LayerAdapter(elem)


@pytest.fixture
def sublayer(overlay):
    elem = etree.SubElement(overlay.elem, svg.SVG_G_TAG, attrib={
        'id': 'sublayer',
        svg.INKSCAPE_GROUPMODE: 'layer',
        svg.INKSCAPE_LABEL: 'Sublayer',
        })
    return LayerAdapter(elem)


class TestLayerAdapter:
    def test_id(self, sublayer):
        assert sublayer.id == 'sublayer'

    def test_label(self, sublayer):
        assert sublayer.label == 'Sublayer'

    def test_output_basenames(self, overlay, sublayer):
        assert overlay.output_basenames == ['somefile']
        assert sublayer.output_basenames is None

    def test_flagged_label(self, overlay):
        assert overlay.label == 'Overlay'

    def test_is_overlay(self, overlay, sublayer):
        assert overlay.is_overlay
        assert not sublayer.is_overlay

    def test_lineage(self, toplevel, overlay, sublayer):
        assert list(sublayer.lineage) == [sublayer, overlay, toplevel]

    def test_overlay(self, overlay, sublayer, toplevel):
        assert overlay.overlay == overlay
        assert sublayer.overlay == overlay
        assert toplevel.overlay is None

    def test_parent(self, sublayer):
        assert sublayer.parent.id == 'overlay'
        assert sublayer.parent.parent.id == 'toplevel'
        assert sublayer.parent.parent.parent is None

    def test_hash(self, sublayer):
        assert hash(sublayer) == _hash_string('sublayer')

    def test_eq(self, toplevel, sublayer):
        assert sublayer != toplevel
        assert sublayer == LayerAdapter(sublayer.elem)

    def test_repr(self, sublayer):
        assert repr(sublayer) == '<LayerAdapter id=sublayer>'

    def test_str(self, sublayer):
        assert str(sublayer) == 'Sublayer'


@pytest.mark.parametrize("s, h", [
    ("", 628939552449298973),
    ("Fü", 1702320224449935351),
    ])
def test_hash_string(s, h):
    assert _hash_string(s) == h


def test_get_element_context_one_overlay(coursemap2):
    novice = get_element_context(coursemap2.novice_title)
    assert novice['course'].label == "T1 Novice"
    assert novice.get('overlay') is None


def test_get_element_context_two_overlay(coursemap2):
    master = get_element_context(coursemap2.blind1_title)
    assert master['course'].label == "T1 Master"
    assert master['overlay'].label == "Blind 1"


def test_get_element_context_no_layers(coursemap2):
    context = get_element_context(coursemap2.root)
    assert context == {}


@pytest.mark.parametrize("id_", ["blind1_title", "novice_title"])
def test_get_element_context_output_basename(coursemap2, id_):
    elem = getattr(coursemap2, id_)
    context = get_element_context(elem)
    assert 'output_basenames' not in context


@pytest.fixture
def srcfile():
    return FileAdapter(open(__file__, 'rb'))


class TestFileAdapter:
    def test_name(self, srcfile):
        assert srcfile.name == __file__

    def test_basename(self, srcfile):
        assert srcfile.basename == os.path.basename(__file__)

    def test_stat(self, srcfile):
        assert srcfile.stat == os.stat(__file__)
        assert stat.S_ISREG(srcfile.stat.st_mode)

    def test_hash(self, srcfile):
        dev_ino = srcfile.stat.st_dev, srcfile.stat.st_ino
        assert hash(srcfile) == hash(dev_ino)

    def test_repr(self, srcfile):
        assert repr(srcfile) == f'<FileAdapter {__file__!r}>'

    def test_str(self, srcfile):
        assert str(srcfile) == __file__


class Test_random_rats:
    def check_plausibility(self, results):
        assert len(results) == 5
        assert all(1 <= r <= 5 for r in results)

    def test_basic(self):
        for n in range(20):
            context = {'random_seed': n}
            rats = random_rats(context)
            self.check_plausibility(rats)

    @pytest.mark.parametrize('varname', ['random_seed', 'layer'])
    def test_results_change_if_seed_changes(self, varname):
        noseed = random_rats({})
        assert any(noseed != random_rats({varname: n})
                   for n in range(20))
        assert noseed == random_rats({})

    def test_skip(self):
        noskip = random_rats({})
        rats = random_rats({}, skip=2)
        assert rats != noskip
        assert rats[:3] == noskip[2:]


@pytest.mark.parametrize("pathcomp, expected", [
    ("a b", "a_b"),
    ("a/b", "a_b"),
    ])
def test_safepath(pathcomp, expected):
    assert safepath(pathcomp) == expected


def test_safepath_coerces_to_text():
    assert safepath(42) == "42"


class Test_render_template:
    @pytest.mark.parametrize('tmpl, output', [
        ("foo", "foo"),
        ("{{ 'a b'|safepath }}", "a_b"),
        ("{{ rats(seed=0)|join(',') }}", "4,4,1,3,5"),
        ])
    def test_render(self, tmpl, output):
        context = {}
        assert render_template(tmpl, context) == output

    def test_strict_undefined(self):
        context = {}
        with pytest.raises(jinja2.UndefinedError):
            assert render_template('{{x}}', context,
                                   strict_undefined=True)


def test_is_string_literal_true():
    assert is_string_literal("Some String")


@pytest.mark.parametrize("tmpl", [
    '{{ somvar }}',
    '{% for x in [1] %}x{% endfor %}',
    '{% set x = 42 %}',
    '{# comment #}',
    ])
def test_is_string_literal_false(tmpl):
    assert not is_string_literal(tmpl)
