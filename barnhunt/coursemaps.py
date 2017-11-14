from itertools import islice
import logging
import re

import jinja2

from .css import InlineCSS
from .inkscape import svg

log = logging.getLogger()

# FIXME: abstract
NSMAP = {
    'svg': "http://www.w3.org/2000/svg",
    'inkscape': "http://www.inkscape.org/namespaces/inkscape",
    }
SVG_G = '{%(svg)s}g' % NSMAP
INKSCAPE_GROUPMODE = '{%(inkscape)s}groupmode' % NSMAP
INKSCAPE_LABEL = '{%(inkscape)s}label' % NSMAP

LAYER_XP = '{%(svg)s}g[@{%(inkscape)s}groupmode="layer"]' % NSMAP


def walk_layers(elem):
    """ Iterate of all layers under elem.

    The layers are returned depth-first order, however at each level the
    layers are interated over in reverse order.  (In the SVG tree, layers
    are listed from bottom to top in the stacking order.  We list them
    from top to bottom.)

    """
    nodes = elem.findall('./' + LAYER_XP)
    while nodes:
        elem = nodes.pop()
        yield elem
        nodes.extend(elem.iterfind('./' + LAYER_XP))


def is_layer(elem):
    return elem.tag == SVG_G and elem.get(INKSCAPE_GROUPMODE) == 'layer'


def lineage(elem):
    while elem is not None:
        yield elem
        elem = elem.getparent()


def parent_layer(elem):
    for parent in islice(lineage(elem), 1, None):
        if is_layer(parent):
            return parent
    return None


def layer_label(layer):
    return layer.get(INKSCAPE_LABEL) or ''


# Regexp which matches the labels of the top-level "Course" layers
# This layer are displayed, one per coursemap.
COURSE_re = re.compile(
    r'\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b',
    re.I)


def is_course(layer):
    if not is_layer(layer):
        return False
    parent = parent_layer(layer)
    return parent is None and COURSE_re.search(layer_label(layer))


# Regexp which matches the label of the top-level "Ring" layer
# This layer is always displayed.
RING_re = re.compile(r'\bring\b', re.I)


def is_cruft(layer):
    if not is_layer(layer):
        return False
    parent = parent_layer(layer)
    label = layer.get(INKSCAPE_LABEL) or ''
    return (parent is None
            and RING_re.search(label) is None
            and COURSE_re.search(label) is None)


def is_overlay(layer):
    if not is_layer(layer):
        return False
    parent = parent_layer(layer)
    return parent is not None and layer_label(parent) == 'Overlays'


class CourseMaps(object):
    is_course = staticmethod(is_course)
    is_cruft = staticmethod(is_cruft)
    is_overlay = staticmethod(is_overlay)

    def __init__(self):
        self.basename_tmpl = _compile_template(
            '{{ course.label|friendly }}'
            '{% if overlay %}/{{ overlay.label|friendly }}{% endif %}'
            )

    def __call__(self, tree):
        for info, hidden_layers in self.iter_maps(tree):
            basename = self.basename_tmpl.render(info)
            yield basename, svg.copy_etree(tree, omit_elements=hidden_layers)

    def iter_maps(self, tree):
        root = tree.getroot()
        layers = list(walk_layers(root))
        assert set(layers) == set(root.iterfind('.//' + LAYER_XP)), (
            "Walk_layers did not find all layer elements. "
            "My understanding of the inkscape SVG format may be flawed.")
        cruft = set(filter(self.is_cruft, layers))
        courses = list(filter(self.is_course, layers))

        def _info(layer):
            return {
                'label': layer_label(layer),
                'id': layer.get('id'),
                }

        for course in courses:
            other_courses = set(courses).difference([course])
            overlays = list(filter(self.is_overlay, walk_layers(course)))
            if overlays:
                for overlay in overlays:
                    other_overlays = set(overlays).difference([overlay])
                    info = {
                        'course': _info(course),
                        'overlay': _info(overlay),
                        }
                    hidden = cruft | other_courses | other_overlays
                    assert course in lineage(overlay)
                    assert hidden.isdisjoint(lineage(overlay))
                    yield info, hidden
            else:
                info = {
                    'course': _info(course),
                    'overlay': None,
                    }
                hidden = cruft | other_courses
                assert hidden.isdisjoint(lineage(course))
                yield info, hidden


def show_layer(elem):
    style = InlineCSS(elem.get('style'))
    if style.get('display', '').strip() == 'none':
        style['display'] = 'inline'
        elem.set('style', style.serialize())
    return elem


def _friendly(path_comp):
    """ Replace shell-unfriendly characters with underscore.
    """
    return re.sub(r"[\000-\040/\\\177\s]", '_', path_comp,
                  flags=re.UNICODE)


class FilenameTemplateCompiler(object):
    FILTERS = {
        'friendly': _friendly,
        }

    def __init__(self):
        env = jinja2.Environment(autoescape=False,
                                 undefined=jinja2.StrictUndefined)
        env.filters.update(self.FILTERS)
        self.env = env

    def compile(self, tmpl_string):
        return self.env.from_string(tmpl_string)


_compile_template = FilenameTemplateCompiler().compile
