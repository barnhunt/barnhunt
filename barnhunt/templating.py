from functools import partial
import hashlib
import jinja2
import logging
import os
import random
import re

from six import python_2_unicode_compatible, text_type

from .layerinfo import FlaggedLayerInfo, LayerFlags
from .inkscape import svg

log = logging.getLogger()


@python_2_unicode_compatible
class LayerAdapter(object):
    """Adapt an Inkscape SVG layer element for ease of use in templates
    """

    def __init__(self, elem, layer_info_class=FlaggedLayerInfo):
        self.elem = elem
        self._layer_info_class = layer_info_class
        self._info = layer_info_class(elem)

    @property
    def id(self):
        return self.elem.get('id')

    @property
    def label(self):
        return self._info.label

    @property
    def output_basename(self):
        return self._info.output_basename

    @property
    def is_overlay(self):
        return bool(self._info.flags & LayerFlags.OVERLAY)

    @property
    def parent(self):
        parent = svg.parent_layer(self.elem)
        if parent is None:
            return None
        return LayerAdapter(parent, self._layer_info_class)

    @property
    def lineage(self):
        layer = self
        while layer:
            yield layer
            layer = layer.parent

    @property
    def overlay(self):
        for layer in self.lineage:
            if layer.is_overlay:
                return layer

    def __hash__(self):
        assert self.id
        return _hash_string(self.id)

    def __eq__(self, other):
        return type(other) is type(self) \
            and other.elem == self.elem \
            and other._layer_info_class == self._layer_info_class

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "<%s id=%s>" % (self.__class__.__name__, self.id)

    def __str__(self):
        return self.label


def _hash_string(s):
    """A deterministic string hashing function.

    (Python's hash() can depend on the setting of PYTHONHASHSEED.)
    """
    bytes_ = s.encode('utf8')
    return hash(int(hashlib.sha1(bytes_).hexdigest(), 16))


def get_element_context(elem, layer_info_class=FlaggedLayerInfo):
    for layer in svg.lineage(elem):
        if svg.is_layer(layer):
            break
    else:
        return {}

    layer = LayerAdapter(layer, layer_info_class)
    overlays = []
    for ancestor in layer.lineage:
        if ancestor.is_overlay:
            overlays.insert(0, ancestor)

    context = {
        'layer': layer,
        'overlays': tuple(overlays),
        }
    if overlays:
        # Course is the outermost containing overlay
        context['course'] = overlays[0]
    if len(overlays) > 1:
        # Overlay is the innermost containing overlay, but only if is
        # distinct from course.
        context['overlay'] = overlays[-1]
    return context


@python_2_unicode_compatible
class FileAdapter(object):
    """Adapt a file object for ease of use in templates
    """
    def __init__(self, fp):
        self._fp = fp

    @property
    def name(self):
        return self._fp.name

    @property
    def basename(self):
        return os.path.basename(self.name)

    @property
    def stat(self):
        fd = self._fp.fileno()
        return os.fstat(fd)

    def __hash__(self):
        st = self.stat
        return hash((st.st_dev, st.st_ino))

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self.name)

    def __str__(self):
        return self.name


global_rng = random.Random()


def default_random_seed(context):
    random_seed = context.get('random_seed')
    svgfile = context.get('svgfile')
    layer = context.get('layer')
    return hash((random_seed, svgfile, layer))


@jinja2.contextfunction
def random_rats(context, n=5, min=1, max=5, seed=None, skip=0):
    """Generate random rat numbers.

    Returns a tuple of ``n`` random integers in the range [``min``,
    ``max``].

    By default, on a given Inkscape layer in a given file, this
    function will attempt to return the same result each time it is
    called.  See the description of the ``seed`` parameter, below, for
    more details.

    The hash of the value specified for ``seed`` is used to seed
    the random number generator used to generate the rat counts.
    The same counts will be generated for the same seed.

    If no ``seed`` is specified, the value of ``hash(random_seed,
    svgfile, layer)``, where ``random_seed``, ``svgfile`` and
    ``layer`` are obtained from the current template context (with any
    missing values be replace by ``None``), will be used for the seed.
    The hash of ``svgfile`` depends on the device and inode number of
    the input SVG file.  The hash of ``layer`` depends on the XML id
    of the layer.

    As a special case, passing ``seed``=``False`` will cause a global
    random number generator to be used, and it will not be reseeded.
    As a result subsequent calls with ``seed`` set to ``False`` will
    generate different rat counts.

    A positive value is passed for ``skip`` will cause that many
    random number to be generated and discarded before picking the
    ``n`` random numbers which are finally used.  This can be used to
    generate independentt sets of random numbers all based on the same
    seed.

    """
    if seed is None:
        seed = default_random_seed(context)
    rng = random.Random(seed) if seed is not False else global_rng

    rand = partial(rng.randint, min, max)
    for _ in range(skip):
        rand()
    return tuple(rand() for _ in range(n))


def safepath(path_comp):
    """A jinja filter to replace shell-unfriendly characters with underscore.
    """
    return re.sub(r"[\000-\040/\\\177\s]", '_', text_type(path_comp),
                  flags=re.UNICODE)


GLOBALS = {
    'rats': random_rats,
    }

FILTERS = {
    'safepath': safepath,
    }


def make_jinja2_environment(undefined=jinja2.Undefined):
    env = jinja2.Environment(autoescape=False, undefined=undefined)
    env.globals.update(GLOBALS)
    env.filters.update(FILTERS)
    return env


default_env = make_jinja2_environment()
strict_env = make_jinja2_environment(undefined=jinja2.StrictUndefined)


def render_template(tmpl_string, context, strict_undefined=False):
    """Render string template.
    """
    env = strict_env if strict_undefined else default_env
    tmpl = env.from_string(tmpl_string)
    return tmpl.render(context)


def is_string_literal(tmpl_string):
    """Is ``tmpl_string`` a simple string literal.

    Returns ``False`` if ``tmpl_string`` contains any Jinja2
    expressions or statements.
    """
    from jinja2 import nodes

    ast = default_env.parse(tmpl_string)
    assert isinstance(ast, nodes.Template)
    if len(ast.body) != 1 or not isinstance(ast.body[0], nodes.Output):
        return False
    output = ast.body[0]
    return (len(output.nodes) == 1
            and isinstance(output.nodes[0], nodes.TemplateData))
