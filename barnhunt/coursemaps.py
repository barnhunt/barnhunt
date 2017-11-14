import logging
import re

import jinja2

from .inkscape import svg

log = logging.getLogger()


# Regexp which matches the labels of the top-level "Course" layers
# This layer are displayed, one per coursemap.
COURSE_re = re.compile(
    r'\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b',
    re.I)


def is_course(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    return parent is None and COURSE_re.search(svg.layer_label(layer))


# Regexp which matches the label of the top-level "Ring" layer
# This layer is always displayed.
RING_re = re.compile(r'\bring\b', re.I)


def is_cruft(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    return (parent is None
            and not is_course(layer)
            and RING_re.search(svg.layer_label(layer)) is None)


def is_overlay(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    return parent is not None and svg.layer_label(parent) == 'Overlays'


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
            pruned = svg.copy_etree(tree, omit_elements=hidden_layers)
            for layer in svg.walk_layers(pruned.getroot()):
                svg.ensure_visible(layer)
            yield basename, pruned

    def iter_maps(self, tree):
        root = tree.getroot()
        layers = list(svg.walk_layers(root))
        assert set(layers) == set(root.iterfind('.//' + svg.LAYER_XP)), (
            "Walk_layers did not find all layer elements. "
            "My understanding of the inkscape SVG format may be flawed.")
        cruft = set(filter(self.is_cruft, layers))
        courses = list(filter(self.is_course, layers))

        def _info(layer):
            return {
                'label': svg.layer_label(layer),
                'id': layer.get('id'),
                }

        for course in courses:
            other_courses = set(courses).difference([course])
            overlays = list(filter(self.is_overlay, svg.walk_layers(course)))
            if overlays:
                for overlay in overlays:
                    other_overlays = set(overlays).difference([overlay])
                    info = {
                        'course': _info(course),
                        'overlay': _info(overlay),
                        }
                    hidden = cruft | other_courses | other_overlays
                    assert hidden.isdisjoint(svg.lineage(overlay))
                    yield info, hidden
            else:
                info = {
                    'course': _info(course),
                    'overlay': None,
                    }
                hidden = cruft | other_courses
                assert hidden.isdisjoint(svg.lineage(course))
                yield info, hidden


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
