import jinja2
import logging

from . import rats
from .etree_util import clone_etree

log = logging.getLogger()

# FIXME: abstract
SVG = "{http://www.w3.org/2000/svg}"
INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"
BH_NS = "http://www.dairiki.org/schema/barnhunt"
BH = "{%s}" % BH_NS


def _is_layer(elem):
    return (
        elem.tag == SVG + 'g'
        and elem.get(INKSCAPE + 'groupmode') == 'layer')


def _find_containing_layer(elem):
    ancestor = elem.getparent()
    while ancestor is not None:
        if _is_layer(ancestor):
            return ancestor
        ancestor = ancestor.getparent()
    return None


class Layer(object):
    def __init__(self, elem, hash_seed=None):
        assert _is_layer(elem)
        self._elem = elem
        self._hash_seed = hash_seed

    @property
    def id(self):
        return self._elem.get('id')

    @property
    def label(self):
        return self._elem.get(INKSCAPE + 'label')

    @property
    def parent(self):
        parent_elem = _find_containing_layer(self._elem)
        if parent_elem is None:
            return None
        return self.__class__(parent_elem, self._hash_seed)

    def rats(self, n=5, min=1, max=5):
        return rats.random_rats(n, min=min, max=max, seed=hash(self))

    def __hash__(self):
        assert self.id
        return hash((self.id, self._hash_seed))

    def __repr__(self):
        return "<%s id=%s>" % (self.__class__.__name__, self.id)


class TemplateExpander(object):
    GLOBALS = {
        'rats': rats.random_rats,
        }

    def __init__(self, hash_seed=None):
        env = jinja2.Environment(autoescape=False,
                                 undefined=jinja2.DebugUndefined)
        env.globals.update(self.GLOBALS)
        self.env = env
        self.hash_seed = hash_seed

    def expand(self, tree):
        tree = clone_etree(tree, update_nsmap={'bh': BH_NS})
        for elem in tree.iter(SVG + 'tspan'):
            self._expand_elem(elem)
        return tree

    def _expand_elem(self, elem):
        content = elem.get(BH + 'content')
        if content is None and elem.text:
            if not self._is_static(elem.text):
                content = elem.text
                elem.set(BH + 'content', content)
        if content is not None:
            log.debug("Expanding %r", content)
            tmpl = self.env.from_string(content)
            elem.text = tmpl.render(self._get_context(elem))

    def _get_context(self, elem):
        layer = _find_containing_layer(elem)
        if layer is not None:
            layer = Layer(layer, self.hash_seed)
        return {
            'layer': layer,
            }

    def _is_static(self, source):
        """Is ``source`` a simple string?

        Returns ``True`` only ``source`` is a simple string which does
        not contain any Jinja expressions or statements.

        """
        from jinja2 import nodes

        ast = self.env.parse(source)
        assert type(ast) == nodes.Template
        if len(ast.body) != 1 or type(ast.body[0]) != nodes.Output:
            return False
        output = ast.body[0]
        return (
            len(output.nodes) == 1
            and type(output.nodes[0]) == nodes.TemplateData
            )
