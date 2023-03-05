""" Helpers to operator on Inkscape SVG files.

"""
from __future__ import annotations

import copy
import dataclasses
import math
import random
from collections import deque
from functools import lru_cache
from itertools import islice
from typing import cast
from typing import Collection
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Mapping
from typing import NamedTuple
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
    "xlink": "http://www.w3.org/1999/xlink",
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
SVG_USE_TAG = _qname("svg:use")

INKSCAPE_GROUPMODE = _qname("inkscape:groupmode")
INKSCAPE_LABEL = _qname("inkscape:label")
XLINK_HREF = _qname("xlink:href")

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


def set_hidden(elem: Element) -> None:
    style = InlineCSS(elem.get("style"))
    style["display"] = "none"
    elem.set("style", style.serialize())


def layer_label(layer: LayerElement) -> str:
    """Get the label of on Inkscape layer"""
    return layer.get(INKSCAPE_LABEL) or ""


class CloneInfo(NamedTuple):
    elem: Element
    ref: Element


@lru_cache(128)
def _compile_xpath(xpath: str) -> etree.XPath:
    return etree.XPath(xpath, namespaces=NSMAP)


def find_clones(tree: ElementTree) -> Iterator[CloneInfo]:
    """Find clones in document.

    “Clones” are <svg:use> elements whose href points to an element outside of the
    <svg:defs> element.

    Returns an iterable of (elem, ref) pairs where ``elem`` is the <svg:use> element,
    and ``ref`` is the element referenced by the ``href``.
    """
    # catalog elements outside of <svg:defs>
    find_elems_outside_defs = _compile_xpath("//*[@id and not(ancestor::svg:defs)]")
    elems_by_id = {elem.get("id"): elem for elem in find_elems_outside_defs(tree)}

    find_clones_outside_defs = _compile_xpath("//svg:use[not(ancestor::svg:defs)]")
    for elem in find_clones_outside_defs(tree):
        href = elem.get("href") or elem.get(XLINK_HREF)
        if href is not None and href.startswith("#"):  # XXX: worry about "url(#foo)"?
            ref = elems_by_id.get(href[1:])
            if ref is not None:
                yield CloneInfo(elem, ref)


def find_hidden_clone_source_layers(
    tree: ElementTree, hidden_layers: Iterable[LayerElement]
) -> set[LayerElement]:
    """Find hidden layers containing sources for visible “clones”."""
    hidden_source_layers: set[LayerElement] = set()
    omitted_layers = set(hidden_layers)
    clones: deque[CloneInfo] = deque(find_clones(tree))
    hidden_clones: list[CloneInfo] = []

    def is_visible(elem: Element) -> bool:
        return omitted_layers.isdisjoint(ancestor_layers(elem))

    while clones:
        clone = clones.popleft()
        if not is_visible(clone.elem):
            hidden_clones.append(clone)
        elif not is_visible(clone.ref):
            ref_layer = parent_layer(clone.ref)
            assert ref_layer is not None
            hidden_source_layers.add(ref_layer)
            omitted_layers.remove(ref_layer)
            # recheck all the clones that were not visible
            clones.extend(hidden_clones)
            hidden_clones.clear()

    return hidden_source_layers


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


@dataclasses.dataclass
class EnsureId:
    """A helper to ensure that elements have id attributes.

    A instance of this class is a callable which may be applied to elements
    from ``tree``.  If the element has an id attribute set, it is returned;
    otherwise, a new unique id is assigned to the element and the new id is
    returned.

    """

    tree: ElementTree
    mindigits: int = 5
    sparedigits: int = 1
    _unique_ids: Iterator[str] | None = dataclasses.field(default=None, init=False)

    def __call__(self, elem: Element) -> str:
        id_ = elem.get("id")
        if not id_:
            if self._unique_ids is None:
                self._unique_ids = self._iter_unique_ids()
            id_ = next(self._unique_ids)
            elem.set("id", id_)
        return id_

    def _iter_unique_ids(self) -> Iterator[str]:
        seen = {elem.get("id") for elem in self.tree.iterfind("//*[@id]")}

        def random_id() -> str:
            return f"bh-{random.randint(1, 10 ** ndigits - 1):0{ndigits}d}"

        while True:
            mindigits = int(math.log10(max(len(seen), 1))) + 1
            ndigits = max(mindigits, self.mindigits) + self.sparedigits
            new_id = random_id()
            while new_id in seen:
                new_id = random_id()
            seen.add(new_id)
            yield new_id


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
