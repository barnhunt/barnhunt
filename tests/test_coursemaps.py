from io import BytesIO

from lxml import etree
import pytest

from barnhunt import coursemaps
from barnhunt.coursemaps import (
    render_templates,
    _get_local_context,
    CourseMaps,
    )
from barnhunt.inkscape import svg
from barnhunt.templating import LayerAdapter


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


class TestCourseMaps(object):
    @pytest.fixture
    def coursemaps(self):
        return CourseMaps()

    def test_call(self, coursemaps, coursemap1, monkeypatch):
        tree = coursemap1.tree
        context = {
            'course': LayerAdapter(coursemap1.t1novice),
            'overlay': None,
            }
        hidden_layers = set()

        def _iter_maps(tree_):
            yield context, hidden_layers
        monkeypatch.setattr(coursemaps, 'iter_maps', _iter_maps)

        def _copy_etree(tree_, omit_elements):
            assert tree_ is tree
            assert omit_elements == hidden_layers
            return tree_
        monkeypatch.setattr('barnhunt.inkscape.svg.copy_etree',
                            _copy_etree)

        assert list(coursemaps(tree)) == [
            (context, tree),
            ]

    def test_layers_unhidden(self, coursemaps, coursemap1):
        context, tree = next(coursemaps(coursemap1.tree))
        ring = tree.find('.//*[@id="ring"]')
        assert 'none' not in ring.get('style')

    def test_iter_maps(self, coursemaps, coursemap1):
        maps = list(coursemaps.iter_maps(coursemap1.tree))
        assert maps == [
            (
                {
                    'course': LayerAdapter(coursemap1.t1novice),
                    'overlay': None,
                    },
                set([coursemap1.cruft, coursemap1.t1master])
                ),
            (
                {
                    'course': LayerAdapter(coursemap1.t1master),
                    'overlay': LayerAdapter(coursemap1.build),
                    },
                set([coursemap1.cruft, coursemap1.t1novice, coursemap1.blind1])
                ),
            (
                {
                    'course': LayerAdapter(coursemap1.t1master),
                    'overlay': LayerAdapter(coursemap1.blind1),
                    },
                set([coursemap1.cruft, coursemap1.t1novice, coursemap1.build])
                ),
            ]
