import logging
import re

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
        style = elem.get('style') or ''
        bits = [bit for bit in style.split(';')
                if bit.strip() and not bit.strip().startswith('display:')]
        bits.append('display:%s' % visibility)
        elem.set('style', ';'.join(bits))

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
                    yield labels, self.tree
            else:
                labels = (course.label,)
                yield labels, self.tree

    __iter__ = iter_maps
