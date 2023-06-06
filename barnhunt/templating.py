from __future__ import annotations

import hashlib
import logging
import os
import random
import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
from operator import itemgetter
from typing import Any
from typing import BinaryIO
from typing import Dict
from typing import Iterator
from typing import Mapping
from typing import overload
from typing import Sequence

import jinja2
import lxml.etree
import rdflib
from rdflib import DC
from rdflib import RDF

from ._compat import Final
from .inkscape import svg
from .layerinfo import LayerFlags
from .layerinfo import LayerInfoParser
from .layerinfo import parse_flagged_layer_info

TemplateContext = Dict[str, Any]


log = logging.getLogger()


class LayerAdapter:
    """Adapt an Inkscape SVG layer element for ease of use in templates"""

    def __init__(
        self,
        elem: svg.LayerElement,
        layer_info_parser: LayerInfoParser = parse_flagged_layer_info,
    ):
        self.elem = elem
        self._parse_layer_info = layer_info_parser
        self._info = layer_info_parser(elem)

    @property
    def id(self) -> str | None:
        return self.elem.get("id")

    @property
    def label(self) -> str:
        return self._info.label

    @property
    def output_basenames(self) -> Sequence[str] | None:
        return self._info.output_basenames or None

    @property
    def is_overlay(self) -> bool:
        return bool(self._info.flags & LayerFlags.OVERLAY)

    @property
    def parent(self) -> LayerAdapter | None:
        parent = svg.parent_layer(self.elem)
        if parent is None:
            return None
        return LayerAdapter(parent, self._parse_layer_info)

    @property
    def lineage(self) -> Iterator[LayerAdapter]:
        ancestor: LayerAdapter | None = self
        while ancestor:
            yield ancestor
            ancestor = ancestor.parent

    @property
    def overlay(self) -> LayerAdapter | None:
        for layer in self.lineage:
            if layer.is_overlay:
                return layer
        return None

    def __hash__(self) -> int:
        assert self.id
        return _hash_string(self.id)

    def __eq__(self, other: Any) -> bool:
        return (
            type(other) is type(self)
            and other.elem == self.elem
            and other._parse_layer_info is self._parse_layer_info
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.id}>"

    def __str__(self) -> str:
        return self.label


def _hash_string(s: str) -> int:
    """A deterministic string hashing function.

    (Python's hash() can depend on the setting of PYTHONHASHSEED.)
    """
    bytes_ = s.encode("utf8")
    return hash(int(hashlib.sha1(bytes_).hexdigest(), 16))


@dataclass
class RdfNodeAdapter:
    """Base for classes that adapt an RDF node for ease of use in templates.

    These adapters represent a particular RDF node within a particular RDF graph.

    """

    _subject: rdflib.IdentifiedNode | rdflib.Literal
    _graph: rdflib.Graph
    _desc: str

    def _adapt(self, node: rdflib.term.Node, desc: str) -> RdfNodeAdapter:
        """Wrap a node from our RDF graph in an appropriate adapter class."""
        if isinstance(node, rdflib.Literal):
            return RdfLiteralAdapter(node, self._graph, desc)
        assert isinstance(node, rdflib.IdentifiedNode)
        node_type = self._graph.value(subject=node, predicate=RDF.type, any=False)
        if node_type in {RDF.Bag, RDF.Seq, RDF.Alt}:
            return RdfCollectionAdapter(node, self._graph, desc)
        return RdfAdapter(node, self._graph, desc)


@dataclass
class RdfLiteralAdapter(RdfNodeAdapter):
    """Adapt an RDF literal node for ease of use in templates.

    Basically, this proxies to the literal value.
    """

    _subject: rdflib.Literal

    def __str__(self) -> str:
        return str(self._subject.value)

    def __getattr__(self, attr: str) -> Any:
        return getattr(self._subject.value, attr)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, RdfNodeAdapter):
            return super().__eq__(other)
        return self._subject.value == other  # type: ignore[no-any-return]


@dataclass
class RdfIdentifiedNodeAdapter(RdfNodeAdapter):
    _subject: rdflib.IdentifiedNode

    def __str__(self) -> str:
        """Stringify to dc:title if there is one."""
        title = self._graph.value(subject=self._subject, predicate=DC.title, any=False)
        if title is not None:
            return str(self._adapt(title, f"{self._desc}['dc:title']"))
        return repr(self)

    def _make_undefined(self, name: str | Any) -> jinja2.Undefined:
        undefined = jinja_undefined.get()
        what = "attribute" if isinstance(name, str) else "element"
        return undefined(f"{self._desc} has no {what} {name}", obj=self, name=name)


class RdfAdapter(RdfIdentifiedNodeAdapter, Mapping[str, RdfNodeAdapter]):
    """Adapt an RDF node for ease of use in templates.

    This is a mapping that maps RDF predicates to RDF objects.
    """

    def __getitem__(  # type: ignore[override]
        self, predicate: str
    ) -> RdfNodeAdapter | jinja2.Undefined:
        # XXX: what if multiple objects?
        object = self._graph.value(
            subject=self._subject, predicate=self._to_uriref(predicate), any=False
        )
        if object is None:
            return self._make_undefined(predicate)
        return self._adapt(object, f"{self._desc}[{predicate!r}]")

    def __iter__(self) -> Iterator[str]:
        graph = self._graph
        for predicate in graph.predicates(subject=self._subject, unique=True):
            assert isinstance(predicate, rdflib.URIRef)
            try:
                yield self._to_qname(predicate)
            except LookupError:
                yield predicate

    def __len__(self) -> int:
        return sum(
            1 for _ in self._graph.predicates(subject=self._subject, unique=True)
        )

    def _to_uriref(self, uri_or_qname: str) -> rdflib.URIRef:
        prefix, sep, suffix = uri_or_qname.partition(":")
        if sep:
            for pfx, base in self._graph.namespace_manager.namespaces():
                if pfx == prefix:
                    return base + suffix
        return rdflib.URIRef(uri_or_qname)

    def _to_qname(self, uriref: rdflib.URIRef) -> str:
        prefix, _uri, name = self._graph.compute_qname(uriref, generate=False)
        if not prefix:
            return name
        return f"{prefix}:{name}"


class RdfCollectionAdapter(RdfIdentifiedNodeAdapter, Sequence[RdfNodeAdapter]):
    """Adapt an RDF collection node for ease of use in templates.

    This presents an RDF collection (rdf:Bag, rdf:Seq, or rdf:Alt) as a sequence.
    """

    @overload  # type: ignore[override]
    def __getitem__(self, n: int) -> RdfNodeAdapter | jinja2.Undefined:
        ...

    @overload
    def __getitem__(self, n: slice) -> Sequence[RdfNodeAdapter]:
        ...

    def __getitem__(
        self, n: int | slice
    ) -> RdfNodeAdapter | Sequence[RdfNodeAdapter] | jinja2.Undefined:
        if isinstance(n, slice):
            return list(self)[n]
        try:
            return list(self)[n]
        except IndexError:
            return self._make_undefined(n)

    _RDF_MEMBER_RE: Final = re.compile(rf"\A{re.escape(str(RDF))}_((?!0)\d+)\Z")

    def __iter__(self) -> Iterator[RdfNodeAdapter]:
        graph = self._graph
        items = []
        for predicate, object_ in graph.predicate_objects(self._subject, unique=True):
            m = self._RDF_MEMBER_RE.match(str(predicate))
            if m is not None:
                items.append((object_, int(m.group(1))))
        return (
            self._adapt(item[0], f"{self._desc}[{n}]")
            for n, item in enumerate(sorted(items, key=itemgetter(1)))
        )

    def __len__(self) -> int:
        return sum(1 for _ in iter(self))


_find_rdf = lxml.etree.ETXPath("//{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF[1]")


def get_rdf_adapter(tree: svg.Element, name: str = "rdf") -> RdfAdapter | None:
    rdf = _find_rdf(tree)
    if len(rdf) > 0:
        base = rdflib.URIRef(uuid.uuid4().urn)
        graph = rdflib.Graph(bind_namespaces="rdflib")
        graph.parse(data=lxml.etree.tostring(rdf[0]), format="xml", publicID=base)
        return RdfAdapter(base, graph, name)
    return None


def get_element_context(
    elem: svg.Element, layer_info_parser: LayerInfoParser = parse_flagged_layer_info
) -> TemplateContext:
    for layer in svg.lineage(elem):
        if svg.is_layer(layer):
            break
    else:
        return {}

    layer_adapter = LayerAdapter(layer, layer_info_parser)
    overlays: list[LayerAdapter] = []
    for ancestor in layer_adapter.lineage:
        if ancestor.is_overlay:
            overlays.insert(0, ancestor)

    context = {
        "layer": layer_adapter,
        "overlays": tuple(overlays),
    }
    if overlays:
        # Course is the outermost containing overlay
        context["course"] = overlays[0]
    if len(overlays) > 1:
        # Overlay is the innermost containing overlay, but only if is
        # distinct from course.
        context["overlay"] = overlays[-1]

    rdf_adapter = get_rdf_adapter(elem, name="rdf")
    if rdf_adapter is not None:
        context["rdf"] = rdf_adapter

    return context


class FileAdapter:
    """Adapt a file object for ease of use in templates"""

    def __init__(self, fp: BinaryIO):
        self._fp = fp

    @property
    def name(self) -> str:
        return self._fp.name

    @property
    def basename(self) -> str:
        return os.path.basename(self.name)

    @property
    def stat(self) -> os.stat_result:
        fd = self._fp.fileno()
        return os.fstat(fd)

    def __hash__(self) -> int:
        st = self.stat
        return hash((st.st_dev, st.st_ino))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name!r}>"

    def __str__(self) -> str:
        return self.name


global_rng = random.Random()


def default_random_seed(context: jinja2.runtime.Context) -> int:
    random_seed = context.get("random_seed")
    layer = context.get("layer")
    return hash((random_seed, layer))


@jinja2.pass_context
def random_rats(
    context: jinja2.runtime.Context,
    n: int = 5,
    min: int = 1,
    max: int = 5,
    seed: int | None = None,
    skip: int = 0,
) -> tuple[int, ...]:
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
    layer)``, where ``random_seed``, and ``layer`` are obtained from
    the current template context (with any missing values replaced
    with ``None``), will be used for the seed.  The ``random_seed``,
    if not specified in the input SVG file is constructed from the
    device and inode number of the input SVG file.  The hash of
    ``layer`` depends on the XML id of the layer.

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


def safepath(path_comp: Any) -> str:
    """A jinja filter to replace shell-unfriendly characters with underscore."""
    return re.sub(r"[\000-\040/\\\177\s]", "_", str(path_comp), flags=re.UNICODE)


GLOBALS = {
    "rats": random_rats,
}

FILTERS = {
    "safepath": safepath,
}


def make_jinja2_environment(
    undefined: type[jinja2.Undefined] = jinja2.Undefined,
) -> jinja2.Environment:
    env = jinja2.Environment(autoescape=False, undefined=undefined)
    env.globals.update(GLOBALS)
    env.filters.update(FILTERS)
    return env


default_env = make_jinja2_environment()
strict_env = make_jinja2_environment(undefined=jinja2.StrictUndefined)


jinja_undefined: ContextVar[type[jinja2.Undefined]] = ContextVar(
    "jinja_undefined", default=jinja2.Undefined
)


def render_template(
    tmpl_string: str, context: TemplateContext, strict_undefined: bool = False
) -> str:
    """Render string template."""
    env = strict_env if strict_undefined else default_env
    tmpl = env.from_string(tmpl_string)
    token = jinja_undefined.set(env.undefined)
    try:
        return tmpl.render(context)
    finally:
        jinja_undefined.reset(token)


def is_string_literal(tmpl_string: str) -> bool:
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
    return len(output.nodes) == 1 and isinstance(output.nodes[0], nodes.TemplateData)
