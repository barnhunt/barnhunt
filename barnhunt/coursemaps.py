import logging

import jinja2

from .inkscape import svg
from .layerinfo import LayerFlags
from .templating import LayerAdapter, is_string_literal, render_template

log = logging.getLogger()


class TemplateRenderer(object):
    def __init__(self, layer_info):
        self.layer_info = layer_info

    def __call__(self, tree, context):
        tree = svg.copy_etree(tree)
        for elem in tree.iter(svg.SVG_TSPAN_TAG):
            if elem.text and not is_string_literal(elem.text):
                local_context = self._get_local_context(elem, context)
                try:
                    elem.text = render_template(elem.text, local_context)
                except jinja2.TemplateError as ex:
                    log.error("Error expanding template in SVG file: %s" % ex)
        return tree

    def _get_local_context(self, elem, parent_context):
        context = parent_context.copy()
        layer = svg.parent_layer(elem)
        if layer is not None:
            layer = LayerAdapter(layer, self.layer_info)
        context['layer'] = layer

        if layer is not None:
            # Some shorthand
            overlays = []
            for ancestor in layer.lineage:
                if ancestor.is_overlay:
                    overlays.insert(0, ancestor)
            context['overlays'] = overlays
            if overlays:
                # Course is the outermost containing overlay
                context['course'] = overlays[0]
            if len(overlays) > 1:
                # Overlay is the nearest containing overlay
                context['overlay'] = overlays[-1]

        return context


class CourseMaps(object):
    context = {
        'course': None,
        'overlay': None,
        }

    def __init__(self, layer_info, context=None):
        self.layer_info = layer_info
        if context is not None:
            self.context = self.context.copy()
            self.context.update(context)

    def __call__(self, tree):
        for path, hidden_layers in self._iter_overlays(tree.getroot()):
            context = self._get_context(path)
            # Copy tree, omitting hidden layers
            pruned = svg.copy_etree(tree, omit_elements=hidden_layers)
            # Ensure all remaining layers are marked for display
            for layer in svg.walk_layers(pruned.getroot()):
                svg.ensure_visible(layer)
            yield context, pruned

    def _get_context(self, path):
        def layer_adapter(elem):
            return LayerAdapter(elem, self.layer_info)

        context = self.context.copy()
        overlays = [layer_adapter(overlay) for overlay in path]
        context['overlays'] = overlays
        if overlays:
            # The top layer overlay is the "course"
            context['course'] = overlays[0]
        if len(overlays) > 1:
            # The lowest level overlay is the "overlay"
            context['overlay'] = overlays[-1]
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
