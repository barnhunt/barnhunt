import copy

from lxml import etree


def _never_prune(elem):
    return False


def clone_etree(tree, prune_p=_never_prune, update_nsmap=None):
    clone = copy.copy(tree)
    assert clone.getroot() is tree.getroot()
    clone._setroot(clone_elem(tree.getroot(), prune_p, update_nsmap))
    return clone


def clone_elem(elem, prune_p=_never_prune, update_nsmap=None):
    def _clone(elem):
        clone = etree.Element(elem.tag, attrib=elem.attrib)
        clone.text = elem.text
        clone.tail = elem.tail
        clone.extend(_clone(child) for child in elem if not prune_p(child))
        return clone

    nsmap = dict(elem.nsmap)
    if update_nsmap:
        nsmap.update(update_nsmap)

    clone = etree.Element(elem.tag, attrib=elem.attrib, nsmap=nsmap)
    clone.text = elem.text
    clone.tail = elem.tail
    clone.extend(_clone(child) for child in elem if not prune_p(child))
    return clone
