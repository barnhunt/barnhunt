""" Helpers to operator on Inkscape SVG files.

"""
import copy
from itertools import islice

from lxml import etree

from .css import InlineCSS

NSMAP = {
    'svg': "http://www.w3.org/2000/svg",
    'inkscape': "http://www.inkscape.org/namespaces/inkscape",
    }

SVG_G_TAG = '{%(svg)s}g' % NSMAP
SVG_TSPAN_TAG = '{%(svg)s}tspan' % NSMAP

INKSCAPE_GROUPMODE = '{%(inkscape)s}groupmode' % NSMAP
INKSCAPE_LABEL = '{%(inkscape)s}label' % NSMAP

LAYER_XP = '{%(svg)s}g[@{%(inkscape)s}groupmode="layer"]' % NSMAP


def walk_layers(elem):
    """Iterate over all layers under elem.

    The layers are returned depth-first order, however at each level the
    layers are iterated over in reverse order.  (In the SVG tree, layers
    are listed from bottom to top in the stacking order.  We list them
    from top to bottom.)

    """
    nodes = elem.findall('./' + LAYER_XP)
    while nodes:
        elem = nodes.pop()
        yield elem
        nodes.extend(elem.iterfind('./' + LAYER_XP))


def sublayers(elem):
    """Iterate over direct sub-layers of elem.

    The layers iterated over in reverse order.  (In the SVG tree, layers
    are listed from bottom to top in the stacking order.  We list them
    from top to bottom.)

    """
    return reversed(elem.findall('./' + LAYER_XP))


def is_layer(elem):
    """Is elem an Inkscape layer element?
    """
    return elem.tag == SVG_G_TAG and elem.get(INKSCAPE_GROUPMODE) == 'layer'


def lineage(elem):
    """Iterate over elem and its ancestors.

    The first element returned will be elem itself. Next comes elem's parent,
    then grandparent, and so on...

    """
    while elem is not None:
        yield elem
        elem = elem.getparent()


def parent_layer(elem):
    """Find the layer which contains elem.

    Returns the element for the Inkscape layer which contains ``elem``.

    """
    for parent in islice(lineage(elem), 1, None):
        if is_layer(parent):
            return parent
    return None


def ensure_visible(elem):
    style = InlineCSS(elem.get('style'))
    if style.get('display', '').strip() == 'none':
        style['display'] = 'inline'
        elem.set('style', style.serialize())
    return elem


def layer_label(layer):
    """Get the label of on Inkscape layer
    """
    return layer.get(INKSCAPE_LABEL) or ''


def copy_etree(tree, omit_elements=None, update_nsmap=None):
    """Copy an entire element tree, possibly making modifications.

    Any elements listed in ``omit_elements`` (along with the
    descendants of any such elements) will be omitted entirely from
    the copy.

    The namespace map of the copied root element will be augmented
    with any mappings specified by ``update_nsmap``.

    """
    omit_elements = set(omit_elements if omit_elements is not None else ())

    def copy_elem(elem, **kwargs):
        if not kwargs and omit_elements.isdisjoint(elem.iter()):
            # No descendants are in omit_elements.
            return copy.deepcopy(elem)  # speed optimization
        rv = etree.Element(elem.tag, attrib=elem.attrib, **kwargs)
        rv.text = elem.text
        rv.tail = elem.tail
        rv.extend(copy_elem(child) for child in elem
                  if child not in omit_elements)
        return rv

    root = tree.getroot()
    rv = copy.copy(tree)
    assert rv.getroot() is root
    nsmap = root.nsmap
    if update_nsmap is not None:
        nsmap.update(update_nsmap)
    rv._setroot(copy_elem(root, nsmap=nsmap))
    return rv
