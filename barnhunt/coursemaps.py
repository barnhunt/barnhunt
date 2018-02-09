import logging
import re

import jinja2

from .compat import enum
from .inkscape import svg
from .templating import LayerAdapter, is_string_literal, render_template

log = logging.getLogger()


class TemplateRenderer(object):
    def __init__(self, layer_info):
        self.layer_info = layer_info

    def __call__(self, tree, context):
        tree = svg.copy_etree(tree)
        for elem in tree.iter(svg.SVG_TSPAN_TAG):
            if elem.text and not is_string_literal(elem.text):
                local_context = self._get_local_context(elem, context)
                try:
                    elem.text = render_template(elem.text, local_context)
                except jinja2.TemplateError as ex:
                    log.error("Error expanding template in SVG file: %s" % ex)
        return tree

    def _get_local_context(self, elem, parent_context):
        context = parent_context.copy()
        layer = svg.parent_layer(elem)
        if layer is not None:
            info = self.layer_info(layer)
            layer = LayerAdapter(layer, info.label)
        context['layer'] = layer
        return context


class CourseMaps(object):
    context = {
        'course': None,
        'overlay': None,
        }

    def __init__(self, layer_info, context=None):
        self.layer_info = layer_info
        if context is not None:
            self.context = self.context.copy()
            self.context.update(context)

    def __call__(self, tree):
        for path, hidden_layers in self._iter_overlays(tree.getroot()):
            context = self._get_context(path)
            # Copy tree, omitting hidden layers
            pruned = svg.copy_etree(tree, omit_elements=hidden_layers)
            # Ensure all remaining layers are marked for display
            for layer in svg.walk_layers(pruned.getroot()):
                svg.ensure_visible(layer)
            yield context, pruned

    def _get_context(self, path):
        def layer_adapter(elem):
            info = self.layer_info(elem)
            return LayerAdapter(elem, label=info.label)

        context = self.context.copy()
        if path:
            # The top layer overlay is the "course"
            context['course'] = layer_adapter(path[0])
            # The lowest level overlay is the "overlay"
            if len(path) > 1:
                context['overlay'] = layer_adapter(path[-1])
        return context

    def _iter_overlays(self, elem):
        overlays, cruft = self._find_overlays(elem)

        if len(overlays) == 0:
            yield [], cruft
            return

        for overlay in overlays:
            other_overlays = set(overlays).difference([overlay])
            for path, hidden in self._iter_overlays(overlay):
                yield [overlay] + path, hidden | cruft | other_overlays

    def _find_overlays(self, elem):
        overlays = []
        cruft = set()
        for node, children in svg.walk_layers2(elem):
            info = self.layer_info(node)
            if info.flags & LayerFlags.HIDDEN:
                cruft.add(node)
                children[:] = []
            elif info.flags & LayerFlags.OVERLAY:
                overlays.append(node)
                children[:] = []
        return overlays, cruft


class LayerFlags(enum.Flag):
    HIDDEN = enum.auto()
    OVERLAY = enum.auto()

    @property
    def flag_char(self):
        return self.name[0].lower()

    def __str__(self):
        return ''.join(
            flag.flag_char for flag in self.__class__ if self & flag)

    @classmethod
    def parse(cls, s):
        value = cls(0)
        lookup = dict((flag.flag_char, flag) for flag in cls)
        for c in set(s):
            flag = lookup.get(c)
            if flag is not None:
                value |= flag
            else:
                log.warning("unknown character '%s' in flags %r", c, s)
        return value


class FlaggedLayerInfo(object):
    def __init__(self, elem):
        flags, label = self._parse_label(svg.layer_label(elem))
        self.elem = elem
        self.flags = flags
        self.label = label

    @staticmethod
    def _parse_label(label):
        m = re.match(r'\[(?P<flags>\w+)\]\s*', label)
        if m:
            flags = LayerFlags.parse(m.group('flags'))
            label = label[m.end():]
        else:
            flags = LayerFlags(0)
        return flags, label


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
            and not is_ring(layer))


def is_overlay(layer):
    if not svg.is_layer(layer):
        return False
    parent = svg.parent_layer(layer)
    parent_label = None if parent is None else svg.layer_label(parent)
    return (
        parent_label == 'Overlays'
        and any(is_course(a) for a in svg.lineage(parent)))


class CompatLayerInfo(object):
    is_course = staticmethod(is_course)
    is_cruft = staticmethod(is_cruft)
    is_overlay = staticmethod(is_overlay)

    def __init__(self, elem):
        label = svg.layer_label(elem)
        if self.is_cruft(elem):
            flags = LayerFlags.HIDDEN
        elif self.is_course(elem) or self.is_overlay(elem):
            flags = LayerFlags.OVERLAY
        else:
            flags = LayerFlags(0)
        self.elem = elem
        self.flags = flags
        self.label = label


def dwim_layer_info(tree):
    """Deduce layout type.
    """
    def has_flags(elem):
        return FlaggedLayerInfo(elem).flags

    if not any(has_flags(elem) for elem in svg.walk_layers(tree.getroot())):
        # Old style with overlays and hidden layers identified by
        # matching layer labels against various regexps.
        return CompatLayerInfo
    else:
        # New style with flags in layer labels.
        # E.g. "[o] Overlay Layer Label", "[h] Hidden Layer"
        return FlaggedLayerInfo
