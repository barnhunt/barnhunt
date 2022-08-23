from __future__ import annotations

import os
import stat
from typing import Callable
from typing import Sequence

import jinja2
import pytest

from barnhunt.inkscape import svg
from barnhunt.templating import _hash_string
from barnhunt.templating import FileAdapter
from barnhunt.templating import get_element_context
from barnhunt.templating import is_string_literal
from barnhunt.templating import LayerAdapter
from barnhunt.templating import random_rats
from barnhunt.templating import render_template
from barnhunt.templating import safepath
from barnhunt.templating import TemplateContext
from testlib import svg_maker


class TestLayerAdapter:
    @pytest.fixture(scope="session")
    def top_layer(self) -> svg.LayerElement:
        layer = svg_maker.layer
        return layer(
            "Parent",
            id="toplevel",
            children=[
                layer(
                    "[o|somefile] Overlay",
                    id="overlay",
                    children=[layer("Sublayer", id="sublayer")],
                )
            ],
        )

    @pytest.fixture
    def toplevel(self, top_layer: svg.LayerElement) -> LayerAdapter:
        return LayerAdapter(top_layer)

    @pytest.fixture
    def overlay(self, top_layer: svg.LayerElement) -> LayerAdapter:
        assert svg.is_layer(top_layer[0])
        return LayerAdapter(top_layer[0])

    @pytest.fixture
    def sublayer(self, top_layer: svg.LayerElement) -> LayerAdapter:
        assert svg.is_layer(top_layer[0][0])
        return LayerAdapter(top_layer[0][0])

    def test_id(self, sublayer: LayerAdapter) -> None:
        assert sublayer.id == "sublayer"

    def test_label(self, sublayer: LayerAdapter) -> None:
        assert sublayer.label == "Sublayer"

    def test_output_basenames(
        self, overlay: LayerAdapter, sublayer: LayerAdapter
    ) -> None:
        assert overlay.output_basenames == ["somefile"]
        assert sublayer.output_basenames is None

    def test_flagged_label(self, overlay: LayerAdapter) -> None:
        assert overlay.label == "Overlay"

    def test_is_overlay(self, overlay: LayerAdapter, sublayer: LayerAdapter) -> None:
        assert overlay.is_overlay
        assert not sublayer.is_overlay

    def test_lineage(
        self, toplevel: LayerAdapter, overlay: LayerAdapter, sublayer: LayerAdapter
    ) -> None:
        assert list(sublayer.lineage) == [sublayer, overlay, toplevel]

    def test_overlay(
        self, toplevel: LayerAdapter, overlay: LayerAdapter, sublayer: LayerAdapter
    ) -> None:
        assert overlay.overlay == overlay
        assert sublayer.overlay == overlay
        assert toplevel.overlay is None

    def test_parent(self, sublayer: LayerAdapter) -> None:
        assert sublayer.parent is not None
        assert sublayer.parent.id == "overlay"
        assert sublayer.parent.parent is not None
        assert sublayer.parent.parent.id == "toplevel"
        assert sublayer.parent.parent.parent is None

    def test_hash(self, sublayer: LayerAdapter) -> None:
        assert hash(sublayer) == _hash_string("sublayer")

    def test_eq(self, toplevel: LayerAdapter, sublayer: LayerAdapter) -> None:
        assert sublayer != toplevel
        assert sublayer == LayerAdapter(sublayer.elem)

    def test_repr(self, sublayer: LayerAdapter) -> None:
        assert repr(sublayer) == "<LayerAdapter id=sublayer>"

    def test_str(self, sublayer: LayerAdapter) -> None:
        assert str(sublayer) == "Sublayer"


@pytest.mark.parametrize(
    "s, h",
    [
        ("", 628939552449298973),
        ("Fü", 1702320224449935351),
    ],
)
def test_hash_string(s: str, h: int) -> None:
    assert _hash_string(s) == h


class Test_get_element_context:
    @pytest.fixture(scope="session")
    def tree(self) -> svg.ElementTree:
        layer = svg_maker.layer
        text = svg_maker.text
        return svg_maker.tree(
            layer("[h] Junk", id="cruft"),
            layer("Outline", id="ring"),
            layer(
                "[o] T1 Master",
                id="t1master",
                children=[
                    layer(
                        "[o|blinds] Blind 1",
                        id="blind1",
                        children=[
                            text(
                                "{{ course.label }} - {{ overlay.label }}",
                                id="blind1_title",
                            )
                        ],
                    ),
                    layer("[o|build_notes] Build Notes", id="build"),
                ],
            ),
            layer(
                "[o] T1 Novice",
                id="t1novice",
                children=[text("{{ course.label }}", id="novice_title")],
            ),
        )

    GetContext = Callable[[str], TemplateContext]

    @pytest.fixture
    def get_context(self, tree: svg.ElementTree) -> GetContext:
        def get_context(id: str) -> TemplateContext:
            (elem,) = tree.xpath("//*[@id=$id]", namespaces=svg.NSMAP, id=id)
            return get_element_context(elem)

        return get_context

    def test_one_overlay(self, get_context: GetContext) -> None:
        novice = get_context("novice_title")
        assert novice["course"].label == "T1 Novice"
        assert novice.get("overlay") is None

    def test_two_overlays(self, get_context: GetContext) -> None:
        master = get_context("blind1_title")
        assert master["course"].label == "T1 Master"
        assert master["overlay"].label == "Blind 1"

    def test_no_layers(self, get_context: GetContext) -> None:
        context = get_context("root")
        assert context == {}

    @pytest.mark.parametrize("id_", ["blind1_title", "novice_title"])
    def test_output_basename(self, id_: str, get_context: GetContext) -> None:
        context = get_context(id_)
        assert "output_basenames" not in context


class TestFileAdapter:
    @pytest.fixture
    def srcfile(self) -> FileAdapter:
        return FileAdapter(open(__file__, "rb"))

    def test_name(self, srcfile: FileAdapter) -> None:
        assert srcfile.name == __file__

    def test_basename(self, srcfile: FileAdapter) -> None:
        assert srcfile.basename == os.path.basename(__file__)

    def test_stat(self, srcfile: FileAdapter) -> None:
        assert srcfile.stat == os.stat(__file__)
        assert stat.S_ISREG(srcfile.stat.st_mode)

    def test_hash(self, srcfile: FileAdapter) -> None:
        dev_ino = srcfile.stat.st_dev, srcfile.stat.st_ino
        assert hash(srcfile) == hash(dev_ino)

    def test_repr(self, srcfile: FileAdapter) -> None:
        assert repr(srcfile) == f"<FileAdapter {__file__!r}>"

    def test_str(self, srcfile: FileAdapter) -> None:
        assert str(srcfile) == __file__


def make_context(template_context: TemplateContext) -> jinja2.runtime.Context:
    return jinja2.runtime.Context(
        jinja2.Environment(),
        template_context,
        name=None,
        blocks={},
    )


class Test_random_rats:
    def check_plausibility(self, results: Sequence[int]) -> None:
        assert len(results) == 5
        assert all(1 <= r <= 5 for r in results)

    def test_basic(self) -> None:
        for n in range(20):
            rats = random_rats(make_context({"random_seed": n}))
            self.check_plausibility(rats)

    @pytest.mark.parametrize("varname", ["random_seed", "layer"])
    def test_results_change_if_seed_changes(self, varname: str) -> None:
        noseed = random_rats(make_context({}))
        assert any(noseed != random_rats(make_context({varname: n})) for n in range(20))
        assert noseed == random_rats(make_context({}))

    def test_skip(self) -> None:
        noskip = random_rats(make_context({}))
        rats = random_rats(make_context({}), skip=2)
        assert rats != noskip
        assert rats[:3] == noskip[2:]


@pytest.mark.parametrize(
    "pathcomp, expected",
    [
        ("a b", "a_b"),
        ("a/b", "a_b"),
    ],
)
def test_safepath(pathcomp: str, expected: str) -> None:
    assert safepath(pathcomp) == expected


def test_safepath_coerces_to_text() -> None:
    assert safepath(42) == "42"


class Test_render_template:
    @pytest.mark.parametrize(
        "tmpl, output",
        [
            ("foo", "foo"),
            ("{{ 'a b'|safepath }}", "a_b"),
            ("{{ rats(seed=0)|join(',') }}", "4,4,1,3,5"),
        ],
    )
    def test_render(self, tmpl: str, output: str) -> None:
        context: TemplateContext = {}
        assert render_template(tmpl, context) == output

    def test_strict_undefined(self) -> None:
        context: TemplateContext = {}
        with pytest.raises(jinja2.UndefinedError):
            assert render_template("{{x}}", context, strict_undefined=True)


def test_is_string_literal_true() -> None:
    assert is_string_literal("Some String")


@pytest.mark.parametrize(
    "tmpl",
    [
        "{{ somvar }}",
        "{% for x in [1] %}x{% endfor %}",
        "{% set x = 42 %}",
        "{# comment #}",
    ],
)
def test_is_string_literal_false(tmpl: str) -> None:
    assert not is_string_literal(tmpl)
