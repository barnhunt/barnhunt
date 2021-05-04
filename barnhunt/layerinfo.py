import enum
import logging
import re

from .inkscape import svg

log = logging.getLogger()


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
        label = svg.layer_label(elem)
        flags, output_basename, label = self._parse_label(label)
        self.elem = elem
        self.flags = flags
        self.output_basename = output_basename
        self.label = label

    @staticmethod
    def _parse_label(label):
        m = re.match(r'\['
                     r'  (?P<flags>\w+)'
                     r'  (?:\|*(?P<output_basename>\w[-\w\d]*))?'
                     r'\]\s*',
                     label, re.X)
        if m:
            flags = LayerFlags.parse(m.group('flags'))
            output_basename = m.group('output_basename')
            label = label[m.end():]
        else:
            flags = LayerFlags(0)
            output_basename = None
        return flags, output_basename, label


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
        self.output_basename = None
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
