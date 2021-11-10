""" Helpers to operator on Inkscape SVG files.

"""
import copy
from itertools import islice

from lxml import etree

from .css import InlineCSS

NSMAP = {
    'svg': "http://www.w3.org/2000/svg",
    'inkscape': "http://www.inkscape.org/namespaces/inkscape",
    'bh': 'http://dairiki.org/barnhunt/inkscape-extensions',
    }

etree.register_namespace('bh', NSMAP['bh'])

SVG_SVG_TAG = etree.QName(NSMAP['svg'], 'svg')
SVG_G_TAG = etree.QName(NSMAP['svg'], 'g')
SVG_TSPAN_TAG = etree.QName(NSMAP['svg'], 'tspan')

INKSCAPE_GROUPMODE = etree.QName(NSMAP['inkscape'], 'groupmode')
INKSCAPE_LABEL = etree.QName(NSMAP['inkscape'], 'label')

LAYER_XP = f'{SVG_G_TAG}[@{INKSCAPE_GROUPMODE}="layer"]'

BH_RANDOM_SEED = etree.QName(NSMAP['bh'], 'random-seed')


def walk_layers(elem):
    """Iterate over all layers under elem.

    The layers are returned depth-first order, however at each level the
    layers are iterated over in reverse order.  (In the SVG tree, layers
    are listed from bottom to top in the stacking order.  We list them
    from top to bottom.)

    """
    for elem, children in walk_layers2(elem):
        yield elem


def walk_layers2(elem):
    """Iterate over all layers under elem.

    This is just like ``walk_layers``, except that it yields a
    sequence of ``(elem, children)`` pairs.  ``Children`` will be a
    list of the sub-layers of ``elem``.  It can be modified in-place
    to "prune" the traversal of the layer tree.

    """
    nodes = elem.findall('./' + LAYER_XP)
    while nodes:
        elem = nodes.pop()
        children = elem.findall('./' + LAYER_XP)
        children.reverse()
        yield elem, children
        nodes.extend(reversed(children))


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


def _svg_attrib(tree):
    svg_elem = tree.getroot()
    if svg_elem.tag != SVG_SVG_TAG:
        raise ValueError(
            f"Expected XML root to be an <svg> tag, not <{svg_elem.tag}>")
    return svg_elem.attrib


def get_svg_attrib(tree, attr, default=None):
    """Get XML attribute from root <svg> element.

    The attribute name, `attr`, should be namedspaced.

    Returns `default` (default `None`) if the attribute does not exist.

    """
    return _svg_attrib(tree).get(attr, default)


def set_svg_attrib(tree, attr, value):
    """Get XML attribute on root <svg> element.

    The attribute specified by the namedspaced `attr` is set to `value`.

    `Tree` is modified *in place*.
    """
    _svg_attrib(tree)[attr] = value


def get_random_seed(tree, default=None):
    value = get_svg_attrib(tree, BH_RANDOM_SEED)
    if value is None:
        return default
    try:
        return int(value, base=0)
    except ValueError as ex:
        raise ValueError(
            f"Expected integer, not {value!r} for /svg/@bh:random-seed"
        ) from ex


def set_random_seed(tree, value):
    set_svg_attrib(tree, BH_RANDOM_SEED, f"{value:d}")
