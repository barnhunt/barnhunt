from __future__ import annotations

import logging
import os
from itertools import chain
from itertools import count
from typing import BinaryIO
from typing import Collection
from typing import Iterable
from typing import Iterator
from typing import NamedTuple
from typing import Sequence

import jinja2
from lxml import etree

from .inkscape import svg
from .layerinfo import dwim_layer_info
from .layerinfo import LayerFlags
from .layerinfo import LayerInfoParser
from .templating import FileAdapter
from .templating import get_element_context
from .templating import is_string_literal
from .templating import render_template
from .templating import TemplateContext

log = logging.getLogger()


class Coursemap(NamedTuple):
    sort_order: int
    tree: svg.ElementTree
    context: TemplateContext
    basename: str
    description: str


class TemplateRenderer:
    def __init__(self, layer_info_parser: LayerInfoParser):
        self.parse_layer_info = layer_info_parser

    def __call__(
        self, tree: svg.ElementTree, context: TemplateContext
    ) -> svg.ElementTree:
        tree = svg.copy_etree(tree)
        for elem in tree.iter(svg.SVG_TSPAN_TAG):
            if elem.text and not is_string_literal(elem.text):
                if not self._is_hidden(elem):
                    local_context = self._get_local_context(elem, context)
                    try:
                        elem.text = render_template(elem.text, local_context)
                    except jinja2.TemplateError as ex:
                        log.error(f"Error expanding template in SVG file: {ex!s}")
        return tree

    def _is_hidden(self, elem: svg.Element) -> bool:
        return any(
            self._is_hidden_layer(ancestor) for ancestor in svg.ancestor_layers(elem)
        )

    def _is_hidden_layer(self, elem: svg.LayerElement) -> bool:
        assert svg.is_layer(elem)
        info = self.parse_layer_info(elem)
        return (info.flags & LayerFlags.HIDDEN) == LayerFlags.HIDDEN

    def _get_local_context(
        self, elem: svg.Element, parent_context: TemplateContext
    ) -> TemplateContext:
        context = parent_context.copy()
        context.update(get_element_context(elem, self.parse_layer_info))
        return context


class CourseMaps:
    default_context = {
        "overlays": (),
        "course": None,
        "overlay": None,
    }

    def __init__(
        self,
        layer_info_parser: LayerInfoParser,
        context: TemplateContext | None = None,
    ):
        self.parse_layer_info = layer_info_parser
        self.context = dict()
        if context is not None:
            self.context.update(context)
        self.context.update(self.default_context)

    def __call__(
        self, tree: svg.ElementTree
    ) -> Iterator[tuple[TemplateContext, svg.ElementTree]]:
        for path, hidden_layers in self._iter_overlays(tree.getroot()):
            base_context = self._get_context(path)
            for basename in self._get_output_basenames(path):
                if basename:
                    omit_elements = hidden_layers.union(
                        self._find_exclusions(basename, tree.getroot())
                    )
                else:
                    omit_elements = hidden_layers
                # Copy tree, omitting hidden layers
                pruned = svg.copy_etree(tree, omit_elements=omit_elements)
                # Ensure all remaining layers are marked for display
                for layer in svg.walk_layers(pruned.getroot()):
                    svg.ensure_visible(layer)
                if basename:
                    context = {**base_context, "output_basename": basename}
                else:
                    context = base_context
                yield context, pruned

    def _get_context(self, path: Sequence[svg.LayerElement]) -> TemplateContext:
        context = self.context.copy()
        if path:
            overlay = path[-1]
            local_context = get_element_context(overlay, self.parse_layer_info)
            local_context.pop("layer", None)
            context.update(local_context)
        return context

    def _get_output_basenames(
        self, path: Sequence[svg.LayerElement]
    ) -> Iterable[str] | tuple[None]:
        if path:
            overlay = path[-1]
            for layer in chain((overlay,), svg.ancestor_layers(overlay)):
                layer_info = self.parse_layer_info(layer)
                if layer_info.output_basenames:
                    return layer_info.output_basenames
        return (None,)

    def _iter_overlays(
        self, elem: svg.Element
    ) -> Iterator[tuple[list[svg.LayerElement], set[svg.LayerElement]]]:
        overlays, cruft = self._find_overlays(elem)

        if len(overlays) == 0:
            yield [], cruft
            return

        for overlay in overlays:
            other_overlays = set(overlays).difference([overlay])
            for path, hidden in self._iter_overlays(overlay):
                yield [overlay] + path, hidden | cruft | other_overlays

    def _find_overlays(
        self, elem: svg.Element
    ) -> tuple[list[svg.LayerElement], set[svg.LayerElement]]:
        overlays = []
        cruft = set()
        for node, children in svg.walk_layers2(elem):
            info = self.parse_layer_info(node)
            if info.flags & LayerFlags.HIDDEN:
                cruft.add(node)
                children[:] = []
            elif info.flags & LayerFlags.OVERLAY:
                overlays.append(node)
                children[:] = []
        return overlays, cruft

    def _find_exclusions(
        self, output_basename: str, elem: svg.Element
    ) -> Iterator[svg.LayerElement]:
        def get_includes(node: svg.LayerElement) -> Collection[str]:
            return self.parse_layer_info(node).include_in

        for node, children in svg.walk_layers2(elem):
            info = self.parse_layer_info(node)
            exclude = output_basename in info.exclude_from
            if not exclude and output_basename not in info.include_in:
                exclude = any(
                    output_basename in get_includes(sibling)
                    for sibling in svg.sibling_layers(node)
                )
            if exclude:
                yield node
                children[:] = []


BASENAME_TMPL = (
    "{% if output_basename -%}"
    "  {{ output_basename }}"
    "{% else -%}"
    '  {{ overlays|map("safepath")|join("/") }}'
    "{% endif %}"
)

DESCRIPTION_TMPL = (
    "{{ svgfile.name }}"
    "{% if overlays -%}"
    '  :{{ overlays|join("/") }}'
    "{% endif %}"
)


def _hash_dev_ino(svgfile: BinaryIO) -> int:
    st = os.fstat(svgfile.fileno())
    return hash((st.st_dev, st.st_ino))


def iter_coursemaps(svgfiles: Iterable[BinaryIO]) -> Iterator[Coursemap]:
    """Iterate over all coursemaps in svgfiles.

    Returns an iterable of (tree, context, basename, description) tuples,
    one for each map to be exported, for coursemaps in svgfiles.
    """
    counter = count()
    for svgfile in svgfiles:
        tree = etree.parse(svgfile)
        layer_info_parser = dwim_layer_info(tree)

        random_seed = svg.get_random_seed(tree)
        if random_seed is None:
            log.warning("%s: no random-seed is set in SVG file", svgfile.name)
            random_seed = _hash_dev_ino(svgfile)

        # Expand jinja templates in text within SVG file
        file_context = {
            "random_seed": random_seed,
            "svgfile": FileAdapter(svgfile),
        }

        render_templates = TemplateRenderer(layer_info_parser)
        # FIXME: tree = render_templates(tree, file_context)

        coursemapper = CourseMaps(layer_info_parser, file_context)
        for context, map_tree in coursemapper(tree):
            rendered_tree = render_templates(map_tree, context)
            yield Coursemap(
                sort_order=next(counter),
                tree=rendered_tree,
                context=context,
                basename=render_template(BASENAME_TMPL, context),
                description=render_template(DESCRIPTION_TMPL, context),
            )
