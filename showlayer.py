import logging
import re

import click
from lxml import etree


log = logging.getLogger('')

SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"


class Layer(object):
    def __init__(self, id, label, sublayers):
        self.id = id
        self.label = label
        self.sublayers = sublayers

    def __repr__(self):
        return "Layer(%r, %r, %r)" % (self.id, self.label, self.sublayers)

    def __str__(self):
        return self.id

    def __unicode__(self):
        return self.id


def _parse(svgfile):

    def parse_layers(parent):
        layers = []
        for g in parent.findall(SVG + 'g'):
            if g.get(INKSCAPE + 'groupmode') == 'layer':
                id = g.get('id')
                label = g.get(INKSCAPE + 'label')
                sublayers = parse_layers(g)
                print id, label, sublayers
                layers.append(Layer(id, label, sublayers))
        return layers

    tree = etree.parse(svgfile)
    return parse_layers(tree.getroot())


class Map(object):
    def __init__(self, title, layers):
        self.title = title
        self.layers = layers

    def __iter__(self):
        layers = self.layers
        while layers:
            layer = layers.pop()
            layers.extend(layer.sublayers)
            yield layer.id



class Drawing(object):
    def __init__(self, layers):
        RING = re.compile(r'\bring\b', re.I)
        COURSE = re.compile(
            r'\b(instinct|novice|open|senior|master|crazy ?8|c8)\b',
            re.I)

        rings = [layer for layer in layers if RING.search(layer.label)]
        if len(rings) != 1:
            if len(rings) > 1:
                raise RuntimeError("Multiple ring layers found")
            else:
                raise RuntimeError("No ring layers found")

        courses = [layer for layer in layers if COURSE.search(layer.label)]

        self.layers = layers
        self.ring = rings[0]
        self.courses = courses

    def iter_maps(self):
        for course in self.courses:
            # FIXME: make more robust
            coursemap = course.sublayers[0]
            overlays = course.sublayers[-1]
            if overlays.label != 'Overlays':
                log.warn("No overlays found in course %s(%s)",
                         course.label, course.id)
                continue
            for overlay in overlays.sublayers:
                title = '%s-%s' % (course.label, overlay.label)
                yield Map(title, [overlay, coursemap, self.ring])

    __iter__ = iter_maps


@click.command()
@click.argument('svgfile', type=click.File('r'))
def layers(svgfile):
    layers = _parse(svgfile)
    for map in Drawing(layers):
        print map.title, list(map)


if __name__ == '__main__':
    layers()
