import logging
import re

import jinja2

from .inkscape import svg
from .templating import LayerAdapter, is_string_literal, render_template

log = logging.getLogger()


def render_templates(tree, context):
    tree = svg.copy_etree(tree)
    for elem in tree.iter(svg.SVG_TSPAN_TAG):
        if elem.text and not is_string_literal(elem.text):
            local_context = _get_local_context(elem, context)
            try:
                elem.text = render_template(elem.text, local_context)
            except jinja2.TemplateError as ex:
                log.error("Error expanding template in SVG file: %s" % ex)
    return tree


def _get_local_context(elem, parent_context):
    context = parent_context.copy()
    layer = svg.parent_layer(elem)
    if layer is not None:
        layer = LayerAdapter(layer)
    context['layer'] = layer
    return context


# Regexp which matches the label of the top-level "Ring" layer
# This layer is always displayed.
RING_re = re.compile(r'\bring\b', re.I)


def is_ring(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    label = svg.layer_label(layer)
    return (parent is None and RING_re.search(label))


# Regexp which matches the labels of the top-level "Course" layers
# This layer are displayed, one per coursemap.
COURSE_re = re.compile(
    r'\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b',
    re.I)


def is_course(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    label = svg.layer_label(layer)
    return parent is None and COURSE_re.search(label) and not is_ring(layer)


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

    def __call__(self, tree):
        for context, hidden_layers in self.iter_maps(tree):
            # Copy tree, omitting hidden layers
            pruned = svg.copy_etree(tree, omit_elements=hidden_layers)
            # Ensure all remaining layers are marked for display
            for layer in svg.walk_layers(pruned.getroot()):
                svg.ensure_visible(layer)
            yield context, pruned

    def iter_maps(self, tree):
        root = tree.getroot()
        layers = list(svg.walk_layers(root))
        assert set(layers) == set(root.iterfind('.//' + svg.LAYER_XP)), (
            "Walk_layers did not find all layer elements. "
            "My understanding of the inkscape SVG format may be flawed.")
        cruft = set(filter(self.is_cruft, layers))
        courses = list(filter(self.is_course, layers))

        for course in courses:
            other_courses = set(courses).difference([course])
            overlays = list(filter(self.is_overlay, svg.walk_layers(course)))
            if overlays:
                for overlay in overlays:
                    other_overlays = set(overlays).difference([overlay])
                    context = {
                        'course': LayerAdapter(course),
                        'overlay': LayerAdapter(overlay),
                        }
                    hidden = cruft | other_courses | other_overlays
                    assert hidden.isdisjoint(svg.lineage(overlay))
                    yield context, hidden
            else:
                context = {
                    'course': LayerAdapter(course),
                    'overlay': None,
                    }
                hidden = cruft | other_courses
                assert hidden.isdisjoint(svg.lineage(course))
                yield context, hidden
