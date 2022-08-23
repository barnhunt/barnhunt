from __future__ import annotations

from typing import Collection
from typing import Sequence

import pytest

from barnhunt import layerinfo
from barnhunt.inkscape import svg
from barnhunt.layerinfo import dwim_layer_info
from barnhunt.layerinfo import LayerFlags
from barnhunt.layerinfo import parse_flagged_layer_info
from barnhunt.layerinfo import parse_obs_layer_info
from testlib import svg_maker


@pytest.mark.parametrize(
    "s, flags",
    [
        ("", LayerFlags(0)),
        ("h", LayerFlags.HIDDEN),
        ("o", LayerFlags.OVERLAY),
        ("ho", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
        ("hoo", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
        ("oh", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ],
)
def test_layerflags_parse(s: str, flags: LayerFlags) -> None:
    assert LayerFlags.parse(s) == flags


def test_layerflags_parse_warns(caplog: pytest.LogCaptureFixture) -> None:
    assert LayerFlags.parse("hx") == LayerFlags.HIDDEN
    assert "unknown character" in caplog.text


@pytest.mark.parametrize(
    "s, flags",
    [
        ("", LayerFlags(0)),
        ("h", LayerFlags.HIDDEN),
        ("o", LayerFlags.OVERLAY),
        ("ho", LayerFlags.OVERLAY | LayerFlags.HIDDEN),
    ],
)
def test_layerflags_str(s: str, flags: LayerFlags) -> None:
    assert set(str(flags)) == set(s)


@pytest.fixture
def tree1() -> svg.ElementTree:
    layer = svg_maker.layer
    return svg_maker.tree(
        layer("Cruft"),
        layer("Ring", visible=False),
        layer(
            "T1 Master",
            children=[
                layer(
                    "Overlays",
                    children=[
                        layer("Blind 1"),
                        layer("Build Notes"),
                    ],
                )
            ],
        ),
        layer("T1 Novice"),
    )


@pytest.mark.parametrize(
    "predicate_name, expected_ids",
    [
        (
            "obs_is_ring",
            [
                "ring",
            ],
        ),
        (
            "obs_is_course",
            [
                "t1novice",
                "t1master",
            ],
        ),
        (
            "obs_is_cruft",
            [
                "cruft",
            ],
        ),
        (
            "obs_is_overlay",
            [
                "blind1",
                "buildnotes",
            ],
        ),
    ],
)
def test_predicate(
    predicate_name: str, tree1: svg.ElementTree, expected_ids: Collection[str]
) -> None:
    predicate = getattr(layerinfo, predicate_name)

    def match(elem: svg.Element) -> bool:
        return svg.is_layer(elem) and predicate(elem)

    print(list(elem.get("id") for elem in svg.walk_layers(tree1.getroot())))
    matches = {elem.get("id") for elem in tree1.iter() if match(elem)}
    assert matches == set(expected_ids)


@pytest.mark.parametrize(
    "layer_label, label, flags, output_basenames, exclude_from, include_in",
    [
        ("[h] Hidden", "Hidden", LayerFlags.HIDDEN, [], set(), set()),
        ("[o] An Overlay", "An Overlay", LayerFlags.OVERLAY, [], set(), set()),
        ("Plain Jane", "Plain Jane", LayerFlags(0), [], set(), set()),
        (
            "[o|foo] Another Overlay",
            "Another Overlay",
            LayerFlags.OVERLAY,
            ["foo"],
            set(),
            set(),
        ),
        ("[!base]Second Layer", "Second Layer", LayerFlags(0), [], {"base"}, set()),
        ("[=base]Base desc", "Base desc", LayerFlags(0), [], set(), {"base"}),
    ],
)
def test_FlaggedLayerInfo(
    layer_label: str,
    label: str,
    flags: LayerFlags,
    output_basenames: Sequence[str],
    exclude_from: Collection[str],
    include_in: Collection[str],
) -> None:
    info = parse_flagged_layer_info(svg_maker.layer(layer_label))
    # FIXME: assert info.elem is elem
    assert info.label == label
    assert info.flags is flags
    assert info.output_basenames == output_basenames
    assert info.exclude_from == exclude_from
    assert info.include_in == include_in


class Test_obs_layer_info:
    @pytest.mark.parametrize(
        "label, flags",
        [
            ("Prototypes", LayerFlags.HIDDEN),
            ("Master 1", LayerFlags.OVERLAY),
            ("Test Ring", LayerFlags(0)),
        ],
    )
    def test_init(self, label: str, flags: LayerFlags) -> None:
        info = parse_obs_layer_info(svg_maker.layer(label))
        assert info.label == label
        assert info.flags is flags
        assert len(info.output_basenames) == 0
        assert len(info.exclude_from) == 0
        assert len(info.include_in) == 0

    def test_overlay(self) -> None:
        layer = svg_maker.layer
        overlay = layer("Test ovl")
        not_overlay = layer("Test not ovl")
        svg_maker.tree(
            layer(
                "Master 2",
                children=[
                    layer("Overlays", children=[overlay]),
                    layer("Stuff", children=[not_overlay]),
                ],
            )
        )

        info = parse_obs_layer_info(overlay)
        assert info.flags is LayerFlags.OVERLAY

        info = parse_obs_layer_info(not_overlay)
        assert info.flags is LayerFlags(0)


class Test_dwim_layer_info:
    @pytest.fixture
    def dummy_tree(self, leaf_label_1: str) -> svg.ElementTree:
        layer = svg_maker.layer
        return svg_maker.tree(
            layer("Layer", children=[layer(leaf_label_1)]),
        )

    @pytest.mark.parametrize("leaf_label_1", ["[h] Hidden"])
    def test_flagged_info(self, dummy_tree: svg.ElementTree) -> None:
        assert dwim_layer_info(dummy_tree) is parse_flagged_layer_info

    @pytest.mark.parametrize("leaf_label_1", ["Not Flagged"])
    def test_obs_info(self, dummy_tree: svg.ElementTree) -> None:
        assert dwim_layer_info(dummy_tree) is parse_obs_layer_info
