from lxml import etree
import pytest

from barnhunt.coursemaps import (  # noqa: F401
    is_course,
    is_cruft,
    is_layer,
    is_overlay,
    lineage,
    parent_layer,
    show_layer,
    walk_layers,
    CourseMaps,
    FilenameTemplateCompiler,
    )


def get_by_id(tree, id):
    matches = tree.xpath('//*[@id="%s"]' % id)
    assert len(matches) <= 1
    return matches[0] if matches else None

    getroot = getattr(tree, 'getroot', None)
    root = getroot() if getroot else tree
    if root.get('id') == id:
        return root
    return root.find('.//*[@id="%s"]' % id)


@pytest.mark.parametrize('predicate_name, expected_ids', [
    ('is_course', [
        't1novice',
        't1master',
        ]),
    ('is_cruft', [
        'cruft',
        ]),
    ('is_layer', [
        't1novice',
        't1master',
        'overlays',
        'blind1',
        'build',
        'ring',
        'cruft',
        ]),
    ('is_overlay', [
        'blind1',
        'build',
        ]),
    ])
def test_predicate(predicate_name, coursemap1, expected_ids):
    predicate = globals()[predicate_name]
    tree = coursemap1.tree
    matches = set(elem for elem in tree.iter() if predicate(elem))
    expected = set(get_by_id(tree, id) for id in expected_ids)
    assert matches == expected


def test_lineage(coursemap1):
    assert list(lineage(coursemap1.overlays)) == [
        coursemap1.overlays,
        coursemap1.t1master,
        coursemap1.root,
        ]


def test_walk_layers(coursemap1):
    layers = list(walk_layers(coursemap1.root))
    ids = [layer.get('id') for layer in layers]
    assert ids == [
        't1novice',
        't1master', 'overlays', 'build', 'blind1',
        'ring',
        'cruft',
        ]


def test_parent_layer(coursemap1):
    assert parent_layer(coursemap1.t1master) is None
    assert parent_layer(coursemap1.overlays) is coursemap1.t1master
    assert parent_layer(coursemap1.ring_leaf) is coursemap1.ring


@pytest.mark.parametrize('style, expected', [
    (None, None),
    ('display: none ;', 'display:inline;'),
    ('display: block;', 'display: block;'),
    ])
def test_show_layer(style, expected):
    attrib = {'style': style} if style is not None else {}
    elem = etree.Element('g', attrib=attrib)
    assert show_layer(elem) is elem
    assert elem.get('style') == expected


def test_friendly():
    from barnhunt.coursemaps import _friendly

    assert _friendly('a b') == 'a_b'
    assert _friendly('a/b') == 'a_b'


class TestCourseMaps(object):
    @pytest.fixture
    def coursemaps(self):
        return CourseMaps()

    def test_call(self, coursemaps, coursemap1, monkeypatch):
        tree = coursemap1.tree
        info = {
            'course': {'label': 'The Course'},
            'overlay': None,
            }
        hidden_layers = set()

        def _iter_maps(tree_):
            yield info, hidden_layers
        monkeypatch.setattr(coursemaps, 'iter_maps', _iter_maps)

        def _copy_etree(tree_, omit_elements):
            assert tree_ is tree
            assert omit_elements == hidden_layers
            return tree_
        monkeypatch.setattr('barnhunt.inkscape.svg.copy_etree',
                            _copy_etree)

        assert list(coursemaps(tree)) == [
            ('The_Course', tree),
            ]

    def test_CourseMaps(self, coursemaps, coursemap1):
        maps = list(coursemaps.iter_maps(coursemap1.tree))
        assert maps == [
            (
                {
                    'course': {'id': 't1novice', 'label': 'T1 Novice'},
                    'overlay': None,
                    },
                set([coursemap1.cruft, coursemap1.t1master])
                ),
            (
                {
                    'course': {'id': 't1master', 'label': 'T1 Master'},
                    'overlay': {'id': 'build', 'label': 'Build Notes'},
                    },
                set([coursemap1.cruft, coursemap1.t1novice, coursemap1.blind1])
                ),
            (
                {
                    'course': {'id': 't1master', 'label': 'T1 Master'},
                    'overlay': {'id': 'blind1', 'label': 'Blind 1'},
                    },
                set([coursemap1.cruft, coursemap1.t1novice, coursemap1.build])
                ),
            ]


def test_FilenameTemplateCompiler():
    compile = FilenameTemplateCompiler().compile
    assert compile('{{ foo|friendly }}').render(foo='x y') == 'x_y'
