from __future__ import annotations

from typing import Iterable
from typing import overload

from lxml import etree
from lxml.builder import ElementMaker

from barnhunt._compat import Literal
from barnhunt.inkscape import svg


@overload
def get_by_id(
    tree: svg.ElementTree, id: str, raising: Literal[False]
) -> svg.Element | None:
    ...


@overload
def get_by_id(
    tree: svg.ElementTree, id: str, raising: Literal[True] = ...
) -> svg.Element:
    ...


def get_by_id(
    tree: svg.ElementTree, id: str, raising: bool = True
) -> svg.Element | None:
    elems: list[svg.Element] = tree.xpath("//*[@id=$id]", id=id)
    if len(elems) == 1:
        return elems[0]
    elif len(elems) > 1:
        raise ValueError(f"Multiple elements found for id {id!r}")
    elif raising:
        raise KeyError(id)
    return None


def get_by_ids(tree: svg.ElementTree, ids: Iterable[str]) -> Iterable[svg.Element]:
    for id in ids:
        yield get_by_id(tree, id)


_nsmap: dict[str | None, str] = dict(svg.NSMAP.items())
_nsmap[None] = svg.NSMAP["svg"]

_e = ElementMaker(namespace=_nsmap[None], nsmap=_nsmap)


class SvgMaker:
    @staticmethod
    def tree(*elems: svg.Element) -> svg.ElementTree:
        return etree.ElementTree(_e.svg({"id": "root"}, *elems))

    @staticmethod
    def layer(
        label: str,
        id: str | None = None,
        children: Iterable[svg.Element] | None = None,
        visible: bool = True,
    ) -> svg.LayerElement:
        layer = _e.g(
            {
                svg.INKSCAPE_GROUPMODE: "layer",
                svg.INKSCAPE_LABEL: label,
                "id": id or "".join(word.lower() for word in label.split()),
            }
        )
        if not visible:
            layer.set("style", "display: hidden;")
        if children is not None:
            layer.extend(children)
        assert svg.is_layer(layer)
        return layer

    @staticmethod
    def text(label: str, id: str | None = None) -> svg.Element:
        attrib = {"id": id or "".join(word.lower() for word in label.split())}
        return _e.text(_e.tspan(attrib, label))


svg_maker = SvgMaker()
