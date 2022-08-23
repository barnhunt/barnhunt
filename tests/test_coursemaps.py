from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Iterable
from typing import Iterator

import pytest
from lxml import etree

from barnhunt.coursemaps import _hash_dev_ino
from barnhunt.coursemaps import CourseMaps
from barnhunt.coursemaps import iter_coursemaps
from barnhunt.coursemaps import TemplateRenderer
from barnhunt.inkscape import svg
from barnhunt.layerinfo import parse_flagged_layer_info
from testlib import svg_maker


def get_labels(layers: Iterable[svg.LayerElement]) -> Iterator[str]:
    return map(svg.layer_label, layers)


@pytest.fixture
def template_renderer() -> TemplateRenderer:
    return TemplateRenderer(parse_flagged_layer_info)


@pytest.mark.parametrize("hidden", [True, False])
def test_render_templates(template_renderer: TemplateRenderer, hidden: bool) -> None:
    repls = svg.NSMAP.copy()
    repls["flags"] = "[h] " if hidden else ""
    xml = (
        """<g xmlns="%(svg)s" xmlns:inkscape="%(inkscape)s"
                inkscape:groupmode="layer"
                inkscape:label="%(flags)sJunk">
               <tspan>{{ somevar }}</tspan>
              </g>"""
        % repls
    )
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    result = template_renderer(tree, {"somevar": "foo"})
    expected = "{{ somevar }}" if hidden else "foo"
    assert result.getroot()[0].text == expected
    assert tree.getroot()[0].text == "{{ somevar }}"


def test_render_templates_failure(
    template_renderer: TemplateRenderer, caplog: pytest.LogCaptureFixture
) -> None:
    xml = '<tspan xmlns="%(svg)s">{{ foo() }}</tspan>' % svg.NSMAP
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    result = template_renderer(tree, {})
    assert result.getroot().text == "{{ foo() }}"
    assert "'foo' is undefined" in caplog.text


def test_is_hidden(template_renderer: TemplateRenderer) -> None:
    text = svg_maker.text("text")
    tspan = text[0]
    svg_maker.layer("[h] Layer", children=[text])

    assert template_renderer._is_hidden(tspan)
    assert template_renderer._is_hidden(text)


def test_is_hidden_layer(template_renderer: TemplateRenderer) -> None:
    elem = svg_maker.layer("[h] Layer")
    assert template_renderer._is_hidden_layer(elem)


def test_is_hidden_layer_not_hidden(template_renderer: TemplateRenderer) -> None:
    elem = svg_maker.layer("[o] Layer")
    assert not template_renderer._is_hidden_layer(elem)


def test_get_local_context(template_renderer: TemplateRenderer) -> None:
    xml = (
        """<g xmlns="%(svg)s"
                xmlns:inkscape="%(inkscape)s"
                inkscape:groupmode="layer"
                inkscape:label="The Layer">
               <tspan>{{ layer.label }}</tspan>
             </g>"""
        % svg.NSMAP
    )
    tree = etree.parse(BytesIO(xml.encode("utf-8")))
    tspan = tree.getroot()[0]
    context = template_renderer._get_local_context(tspan, dict(foo="bar"))
    assert context["foo"] == "bar"
    assert context["layer"].label == "The Layer"


class TestCourseMaps:
    @pytest.fixture
    def coursemaps(self) -> CourseMaps:
        return CourseMaps(layer_info_parser=parse_flagged_layer_info)

    @pytest.fixture
    def dummy_tree(self) -> svg.ElementTree:
        layer = svg_maker.layer
        return svg_maker.tree(
            layer(
                "Test",
                children=[
                    layer("[!base] Not in base"),
                ],
            ),
            layer(
                "[o] Overlay 2",
                children=[
                    layer("[o] Overlay 2.1"),
                ],
            ),
            layer(
                "Child",
                children=[
                    layer(
                        "[o] Overlay 1",
                        children=[
                            layer("[o] Overlay 1.3"),
                            layer("[h] Hidden 1.2"),
                            layer("[o] Overlay 1.1"),
                        ],
                    ),
                ],
            ),
            layer(
                "[h] Hidden",
                children=[
                    layer("Hidden Child"),
                ],
            ),
        )

    def test_init_with_context(self) -> None:
        coursemaps = CourseMaps(
            layer_info_parser=parse_flagged_layer_info, context={"foo": "bar"}
        )
        assert coursemaps.context["foo"] == "bar"

    def test_call(self, coursemaps: CourseMaps) -> None:
        layer = svg_maker.layer
        tree = svg_maker.tree(
            layer("[h] Hidden", children=[layer("Hidden Child")]),
            layer("Layer", children=[layer("Child")]),
        )

        result = list(coursemaps(tree))
        assert len(result) == 1
        context, pruned = result[0]
        assert context == {"course": None, "overlay": None, "overlays": ()}
        root = pruned.getroot()
        assert len(root) == 1 and svg.is_layer(root[0])
        assert svg.layer_label(root[0]) == "Layer"
        assert len(root[0]) == 1 and svg.is_layer(root[0][0])
        assert svg.layer_label(root[0][0]) == "Child"
        assert len(root[0][0]) == 0

        for layer_ in svg.walk_layers(root):
            # FIXME: assert not is_hidden(layer_)
            assert "display" not in layer_.get("style", "")

    def test_get_context_no_overlays(self, coursemaps: CourseMaps) -> None:
        path: list[svg.LayerElement] = []
        context = coursemaps._get_context(path)
        assert context["course"] is None
        assert context["overlay"] is None

    def test_get_context_one_overlay(self, coursemaps: CourseMaps) -> None:
        path = [svg_maker.layer("[o] Foo")]
        context = coursemaps._get_context(path)
        assert len(context["overlays"]) == 1
        assert context["course"].label == "Foo"
        assert context["overlay"] is None

    def test_iter_overlays(
        self, coursemaps: CourseMaps, dummy_tree: svg.ElementTree
    ) -> None:
        root = dummy_tree.getroot()
        result = list(coursemaps._iter_overlays(root))
        labels = [
            (list(get_labels(path)), set(get_labels(cruft))) for path, cruft in result
        ]
        assert labels == [
            (
                ["[o] Overlay 1", "[o] Overlay 1.1"],
                {"[h] Hidden", "[h] Hidden 1.2", "[o] Overlay 1.3", "[o] Overlay 2"},
            ),
            (
                ["[o] Overlay 1", "[o] Overlay 1.3"],
                {"[h] Hidden", "[o] Overlay 1.1", "[h] Hidden 1.2", "[o] Overlay 2"},
            ),
            (["[o] Overlay 2", "[o] Overlay 2.1"], {"[h] Hidden", "[o] Overlay 1"}),
        ]

    @pytest.mark.parametrize(
        "output_basename, exclusions",
        [
            ("base", {"[!base] Not in base"}),
            ("notbase", set()),
        ],
    )
    def test_find_exclusions(
        self,
        coursemaps: CourseMaps,
        dummy_tree: svg.ElementTree,
        output_basename: str,
        exclusions: set[str],
    ) -> None:
        root = dummy_tree.getroot()
        result = coursemaps._find_exclusions(output_basename, root)
        assert set(get_labels(result)) == exclusions

    def test_find_overlays(
        self, coursemaps: CourseMaps, dummy_tree: svg.ElementTree
    ) -> None:
        root = dummy_tree.getroot()
        overlays, cruft = coursemaps._find_overlays(root)
        assert list(get_labels(overlays)) == ["[o] Overlay 1", "[o] Overlay 2"]
        assert set(get_labels(cruft)) == {"[h] Hidden"}


def test_hash_dev_ino() -> None:
    with open(__file__, "rb") as srcfile:
        st = os.stat(__file__)
        dev_ino = st.st_dev, st.st_ino
        assert _hash_dev_ino(srcfile) == hash(dev_ino)


# XXX: more unit tests for iter_coursemaps are probably in order
def test_iter_coursemaps_warns_if_no_random_seed(
    drawing_svg: Path, caplog: pytest.LogCaptureFixture
) -> None:
    svgfiles = [drawing_svg.open("rb")]
    for _ in iter_coursemaps(svgfiles):
        pass
    assert "no random-seed" in caplog.text
