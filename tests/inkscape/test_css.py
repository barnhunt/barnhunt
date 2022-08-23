import logging

import pytest

from barnhunt.inkscape.css import InlineCSS


class TestInlineCSS:
    def test_setitem(self) -> None:
        css = InlineCSS()
        css["display"] = "none"
        assert css.serialize() == "display:none;"

        css = InlineCSS("display: inline; Display: block")
        css["display"] = "none"
        assert css.serialize() == "display:none;"

        css = InlineCSS("text-align:center")
        css["display"] = "none"
        assert css.serialize() == "text-align:center;display:none;"

    def test_getitem(self) -> None:
        css = InlineCSS("display: inline; text-align:center; Display:block")
        assert css["display"] == "block"
        with pytest.raises(KeyError):
            css["missing"]

    def test_delitem(self) -> None:
        css = InlineCSS("display: inline; text-align:center; Display: block")
        del css["display"]
        assert css.serialize() == "text-align:center;"

    def test_iter(self) -> None:
        css = InlineCSS("DISPLAY: inline; text-align:center; Display:block")
        assert list(css) == ["DISPLAY", "text-align"]

    def test_len(self) -> None:
        css = InlineCSS("DISPLAY: inline; text-align:center; Display:block")
        assert len(css) == 2

    def test_repr(self) -> None:
        css = InlineCSS()
        assert repr(css) == "<InlineCSS []>"

    def test_parse_error(self, caplog: pytest.LogCaptureFixture) -> None:
        css = InlineCSS("display:inline; mistake;text-align:center")
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "mistake" in warnings[0].getMessage()
        assert css.serialize() == "display:inline;text-align:center;"

    def test_warns_on_at_rule(self, caplog: pytest.LogCaptureFixture) -> None:
        style = "display:inline;@display print {display:block}"
        css = InlineCSS(style)
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 1
        assert "@ rules" in warnings[0].getMessage()
        assert css.serialize() == style

    def test_str(self) -> None:
        css = InlineCSS("x: fü")
        assert str(css) == "x: fü;"
