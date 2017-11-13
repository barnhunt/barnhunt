import logging
import re

from .css import InlineCSS
from .etree_util import clone_etree

log = logging.getLogger()

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"


def _find_layers(elem):
    layers = []
    for g in elem.findall(SVG + 'g'):
        if g.get(INKSCAPE + 'groupmode') == 'layer':
            layers.insert(0, Layer(g))
    return layers


class Layer(object):
    def __init__(self, elem):
        self.elem = elem
        self.sublayers = _find_layers(elem)

    @property
    def id(self):
        return self.elem.get('id')

    @property
    def label(self):
        return self.elem.get(INKSCAPE + 'label')

    def _set_display(self, visibility):
        elem = self.elem
        style = InlineCSS(elem.get('style'))
        style['display'] = visibility
        elem.set('style', style.serialize())

    def walk(self):
        """ Depth first traversal of self and sublayers.
        """
        layers = [self]
        while layers:
            layer = layers.pop(0)
            layers[:0] = layer.sublayers
            yield layer

    def show(self, recursive=False):
        layers = self.walk() if recursive else [self]
        for layer in layers:
            layer._set_display('inline')

    def hide(self):
        self._set_display('none')

    def __repr__(self):
        return "<Layer %s>" % self.id


class CourseMaps(object):
    def __init__(self, tree):
        RING = re.compile(r'\bring\b', re.I)
        COURSE = re.compile(
            r'\b(instinct|novice|open|senior|master|crazy ?8s?|c8)\b',
            re.I)

        # XXX: make a working copy of the tree.
        # We modify it in place, then clone it (pruning hidden nodes)
        # to generate the returned trees.
        # This is a bit hokey ---
        # It would be nice not to have to modify the input tree.
        tree = clone_etree(tree)
        root = tree.getroot()

        layers = _find_layers(root)

        rings = [layer for layer in layers if RING.search(layer.label)]
        if len(rings) != 1:
            if len(rings) > 1:
                raise RuntimeError("Multiple ring layers found")
            else:
                raise RuntimeError("No ring layers found")
        ring = rings[0]

        for layer in layers:
            layer.hide()
        ring.show(recursive=True)

        courses = [layer for layer in layers if COURSE.search(layer.label)]

        self.tree = tree
        self.root = root
        self.ring = ring
        self.courses = courses

    def iter_maps(self):

        for course in self.courses:
            log.debug("Processing course %r", course.label)
            # Hide other courses
            for layer in self.courses:
                layer.hide()
            # Show this course and all sublayers (for now)
            course.show(recursive=True)

            # Find "Overlays" layer
            for overlays in course.sublayers:
                if overlays.label == 'Overlays':
                    break
            else:
                overlays = None
                log.debug("No overlays found in course %r", course.label)

            if overlays:
                for overlay in overlays.sublayers:
                    # Hide other overlays
                    for layer in overlays.sublayers:
                        layer.hide()
                    overlay.show()
                    labels = (course.label, overlay.label)
                    yield labels, prune_hidden(self.tree)
            else:
                labels = (course.label,)
                yield labels, prune_hidden(self.tree)

    __iter__ = iter_maps


def slow_is_hidden(elem):
    # This is correct but very slow.
    style = elem.get('style')
    if style:
        display = InlineCSS(style).get('display')
        return display and display.strip() == 'none'
    else:
        return False


HIDDEN_re = re.compile(
    r'(?: \A | ; ) \s* display \s* : \s* none \s* (?: \Z | ; )',
    re.X)


def is_hidden(elem):
    style = elem.get('style')
    return style and HIDDEN_re.search(style)


def prune_hidden(tree):
    return clone_etree(tree, is_hidden)
