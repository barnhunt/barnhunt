""" Helpers to operator on Inkscape SVG files.

"""
from __future__ import annotations

import copy
from itertools import islice
from typing import cast
from typing import Collection
from typing import Iterator
from typing import List
from typing import Mapping
from typing import NewType
from typing import overload
from typing import TYPE_CHECKING

from lxml import etree

from .._compat import TypeGuard
from .css import InlineCSS

# XML element
Element = etree._Element
LayerElement = NewType("LayerElement", Element)

if TYPE_CHECKING:
    ElementTree = etree._ElementTree[Element]
else:
    ElementTree = object


NSMAP = {
    "svg": "http://www.w3.org/2000/svg",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "bh": "http://dairiki.org/barnhunt/inkscape-extensions",
}

etree.register_namespace("bh", NSMAP["bh"])  # type: ignore[attr-defined]


def _qname(tag: str) -> str:
    prefix, sep, localname = tag.rpartition(":")
    assert sep
    return f"{{{NSMAP[prefix]}}}{localname}"


SVG_SVG_TAG = _qname("svg:svg")
SVG_G_TAG = _qname("svg:g")
SVG_TEXT_TAG = _qname("svg:text")
SVG_TSPAN_TAG = _qname("svg:tspan")

INKSCAPE_GROUPMODE = _qname("inkscape:groupmode")
INKSCAPE_LABEL = _qname("inkscape:label")

LAYER_XP = f'{SVG_G_TAG}[@{INKSCAPE_GROUPMODE}="layer"]'

BH_RANDOM_SEED = _qname("bh:random-seed")


def walk_layers(elem: Element) -> Iterator[LayerElement]:
    """Iterate over all layers under elem.

    The layers are returned depth-first order, however at each level the
    layers are iterated over in reverse order.  (In the SVG tree, layers
    are listed from bottom to top in the stacking order.  We list them
    from top to bottom.)

    """
    for layer, _children in walk_layers2(elem):
        yield layer


def walk_layers2(elem: Element) -> Iterator[tuple[LayerElement, list[LayerElement]]]:
    """Iterate over all layers under elem.

    This is just like ``walk_layers``, except that it yields a
    sequence of ``(elem, children)`` pairs.  ``Children`` will be a
    list of the sub-layers of ``elem``.  It can be modified in-place
    to "prune" the traversal of the layer tree.

    """
    nodes = elem.findall("./" + LAYER_XP)
    while nodes:
        elem = LayerElement(nodes.pop())
        children = elem.findall("./" + LAYER_XP)
        children.reverse()
        yield elem, cast(List[LayerElement], children)
        nodes.extend(reversed(children))


def is_layer(elem: Element) -> TypeGuard[LayerElement]:
    """Is elem an Inkscape layer element?"""
    return elem.tag == SVG_G_TAG and elem.get(INKSCAPE_GROUPMODE) == "layer"


def lineage(elem: Element) -> Iterator[Element]:
    """Iterate over elem and its ancestors.

    The first element returned will be elem itself. Next comes elem's parent,
    then grandparent, and so on...

    """
    ancestor: Element | None = elem
    while ancestor is not None:
        yield ancestor
        ancestor = ancestor.getparent()


def parent_layer(elem: Element) -> LayerElement | None:
    """Find the layer which contains elem.

    Returns the element for the Inkscape layer which contains ``elem``.

    """
    return next(ancestor_layers(elem), None)


def ancestor_layers(elem: Element) -> Iterator[LayerElement]:
    """Iterate the ancestor layers of element.

    Yields, first, the layer that contains ``elem``, then the layer that
    contains that layer, and so on.

    """
    for parent in islice(lineage(elem), 1, None):
        if is_layer(parent):
            yield parent


def sibling_layers(elem: Element) -> Iterator[LayerElement]:
    """Iterate over sibling layers, *not* including self."""
    parent = elem.getparent()
    if parent is None:
        return
    for sibling in parent:
        if sibling is not elem and is_layer(sibling):
            yield sibling


def ensure_visible(elem: Element) -> None:
    style = InlineCSS(elem.get("style"))
    if style.get("display", "").strip() == "none":
        style["display"] = "inline"
        elem.set("style", style.serialize())


def layer_label(layer: LayerElement) -> str:
    """Get the label of on Inkscape layer"""
    return layer.get(INKSCAPE_LABEL) or ""


def copy_etree(
    tree: ElementTree,
    omit_elements: Collection[Element] | None = None,
    update_nsmap: Mapping[str | None, str] | None = None,
) -> ElementTree:
    """Copy an entire element tree, possibly making modifications.

    Any elements listed in ``omit_elements`` (along with the
    descendants of any such elements) will be omitted entirely from
    the copy.

    The namespace map of the copied root element will be augmented
    with any mappings specified by ``update_nsmap``.

    """
    omit_elems = set(omit_elements or ())

    def copy_elem(
        elem: Element, nsmap: Mapping[str | None, str] | None = None
    ) -> Element:
        if nsmap is None and omit_elems.isdisjoint(elem.iter()):
            # No descendants are in omit_elements.
            return copy.deepcopy(elem)  # speed optimization

        rv = etree.Element(elem.tag, attrib=elem.attrib, nsmap=nsmap)
        rv.text = elem.text
        rv.tail = elem.tail
        rv.extend(copy_elem(child) for child in elem if child not in omit_elems)
        return rv

    root = tree.getroot()
    rv = copy.copy(tree)
    assert rv.getroot() is root
    nsmap = root.nsmap
    if update_nsmap is not None:
        nsmap.update(update_nsmap)
    rv._setroot(copy_elem(root, nsmap=nsmap))
    return rv


def _svg_attrib(tree: ElementTree) -> etree._Attrib:
    svg_elem = tree.getroot()
    if svg_elem.tag != SVG_SVG_TAG:
        raise ValueError(f"Expected XML root to be an <svg> tag, not <{svg_elem.tag}>")
    return svg_elem.attrib


@overload
def get_svg_attrib(
    tree: ElementTree, attr: str | bytes | etree.QName, default: str
) -> str:
    ...


@overload
def get_svg_attrib(
    tree: ElementTree, attr: str | bytes | etree.QName, default: None = ...
) -> str | None:
    ...


def get_svg_attrib(
    tree: ElementTree, attr: str | bytes | etree.QName, default: str | None = None
) -> str | None:
    """Get XML attribute from root <svg> element.

    The attribute name, `attr`, should be namedspaced.

    Returns `default` (default `None`) if the attribute does not exist.

    """
    return _svg_attrib(tree).get(attr, default)


def set_svg_attrib(
    tree: ElementTree, attr: str | bytes | etree.QName, value: str
) -> None:
    """Get XML attribute on root <svg> element.

    The attribute specified by the namedspaced `attr` is set to `value`.

    `Tree` is modified *in place*.
    """
    _svg_attrib(tree)[attr] = value


@overload
def get_random_seed(tree: ElementTree, default: int) -> int:
    ...


@overload
def get_random_seed(tree: ElementTree, default: None = ...) -> int | None:
    ...


def get_random_seed(tree: ElementTree, default: int | None = None) -> int | None:
    value = get_svg_attrib(tree, BH_RANDOM_SEED)
    if value is None:
        return default
    try:
        return int(value, base=0)
    except ValueError as ex:
        raise ValueError(
            f"Expected integer, not {value!r} for /svg/@bh:random-seed"
        ) from ex


def set_random_seed(tree: ElementTree, value: int) -> None:
    set_svg_attrib(tree, BH_RANDOM_SEED, f"{value:d}")
