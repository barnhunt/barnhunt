import logging
import os

import jinja2
from lxml import etree

from .inkscape import svg
from .layerinfo import (
    dwim_layer_info,
    LayerFlags,
    )
from .templating import (
    FileAdapter,
    get_element_context,
    is_string_literal,
    render_template,
    )

log = logging.getLogger()


class TemplateRenderer:
    def __init__(self, layer_info):
        self.layer_info = layer_info

    def __call__(self, tree, context):
        tree = svg.copy_etree(tree)
        for elem in tree.iter(svg.SVG_TSPAN_TAG):
            if elem.text and not is_string_literal(elem.text):
                if not self._is_hidden(elem):
                    local_context = self._get_local_context(elem, context)
                    try:
                        elem.text = render_template(elem.text, local_context)
                    except jinja2.TemplateError as ex:
                        log.error(
                            f"Error expanding template in SVG file: {ex!s}")
        return tree

    def _is_hidden(self, elem):
        return any(self._is_hidden_layer(ancestor)
                   for ancestor in svg.lineage(elem))

    def _is_hidden_layer(self, elem):
        if not svg.is_layer(elem):
            return False
        info = self.layer_info(elem)
        return (info.flags & LayerFlags.HIDDEN) == LayerFlags.HIDDEN

    def _get_local_context(self, elem, parent_context):
        context = parent_context.copy()
        context.update(get_element_context(elem, self.layer_info))
        return context


class CourseMaps:
    default_context = {
        'overlays': (),
        'course': None,
        'overlay': None,
        }

    def __init__(self, layer_info, context=None):
        self.layer_info = layer_info
        self.context = dict()
        if context is not None:
            self.context.update(context)
        self.context.update(self.default_context)

    def __call__(self, tree):
        for path, hidden_layers in self._iter_overlays(tree.getroot()):
            context = self._get_context(path)
            output_basename = context.get("output_basename")
            if output_basename:
                omit_elements = hidden_layers.union(
                    self._find_exclusions(output_basename, tree.getroot())
                )
            else:
                omit_elements = hidden_layers
            # Copy tree, omitting hidden layers
            pruned = svg.copy_etree(tree, omit_elements=omit_elements)
            # Ensure all remaining layers are marked for display
            for layer in svg.walk_layers(pruned.getroot()):
                svg.ensure_visible(layer)
            yield context, pruned

    def _get_context(self, path):
        context = self.context.copy()
        if path:
            overlay = path[-1]
            local_context = get_element_context(overlay, self.layer_info)
            local_context.pop('layer', None)
            context.update(local_context)
        return context

    def _iter_overlays(self, elem):
        overlays, cruft = self._find_overlays(elem)

        if len(overlays) == 0:
            yield [], cruft
            return

        for overlay in overlays:
            other_overlays = set(overlays).difference([overlay])
            for path, hidden in self._iter_overlays(overlay):
                yield [overlay] + path, hidden | cruft | other_overlays

    def _find_overlays(self, elem):
        overlays = []
        cruft = set()
        for node, children in svg.walk_layers2(elem):
            info = self.layer_info(node)
            if info.flags & LayerFlags.HIDDEN:
                cruft.add(node)
                children[:] = []
            elif info.flags & LayerFlags.OVERLAY:
                overlays.append(node)
                children[:] = []
        return overlays, cruft

    def _find_exclusions(self, output_basename, elem):
        for node, children in svg.walk_layers2(elem):
            info = self.layer_info(node)
            if output_basename in info.exclude_from:
                yield node
                children[:] = []


BASENAME_TMPL = ('{% if output_basename -%}'
                 '  {{ output_basename }}'
                 '{% else -%}'
                 '  {{ overlays|map("safepath")|join("/") }}'
                 '{% endif %}')

DESCRIPTION_TMPL = ('{{ svgfile.name }}'
                    '{% if overlays -%}'
                    '  :{{ overlays|join("/") }}'
                    '{% endif %}')


def _hash_dev_ino(svgfile):
    st = os.fstat(svgfile.fileno())
    return hash((st.st_dev, st.st_ino))


def iter_coursemaps(svgfiles):
    """ Returns an iterable of (context, tree) pairs for coursemaps in
    SVGFILES.

    """
    for svgfile in svgfiles:
        tree = etree.parse(svgfile)
        layer_info_class = dwim_layer_info(tree)

        random_seed = svg.get_random_seed(tree)
        if random_seed is None:
            log.warning("%s: no random-seed is set in SVG file", svgfile.name)
            random_seed = _hash_dev_ino(svgfile)

        # Expand jinja templates in text within SVG file
        file_context = {
            'random_seed': random_seed,
            'svgfile': FileAdapter(svgfile),
        }

        render_templates = TemplateRenderer(layer_info_class)
        tree = render_templates(tree, file_context)

        coursemapper = CourseMaps(layer_info_class, file_context)
        for context, tree in coursemapper(tree):
            yield {
                'tree': tree,
                'context': context,
                'basename': render_template(BASENAME_TMPL, context),
                'description': render_template(DESCRIPTION_TMPL, context)
                }
