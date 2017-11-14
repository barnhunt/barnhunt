""" Helpers to operator on Inkscape SVG files.

"""
import copy

from lxml import etree


def copy_etree(tree, omit_elements=None, update_nsmap=None):
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
