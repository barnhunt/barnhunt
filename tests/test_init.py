import pytest

import click

from barnhunt import (
    default_2up_output_file,
    pdf_2up,
)


class Test_default_2up_output_file:
    @pytest.fixture
    def ctx(self):
        with click.Context(pdf_2up) as ctx:
            yield ctx

    @pytest.fixture
    def add_input_file(self, ctx, tmp_path):
        def add_input_file(filename):
            params = ctx.params
            param_name = 'pdffiles'
            dummy_path = tmp_path / filename
            dummy_path.touch()
            fp = click.File('rb').convert(str(dummy_path), param_name, ctx)
            params[param_name] = params.get(param_name, ()) + (fp,)
            return dummy_path
        return add_input_file

    def test_default_output_filename(self, ctx, add_input_file, capsys):
        input_pdf = add_input_file('input.pdf')
        output_filename = default_2up_output_file()
        assert output_filename == input_pdf.with_name('input-2up.pdf')
        assert "Writing output to " in capsys.readouterr().out

    def test_raises_error_when_multiple_inputs(self, ctx, add_input_file):
        add_input_file('input1.pdf')
        add_input_file('input2.pdf')
        with pytest.raises(click.UsageError, match="multiple input files"):
            default_2up_output_file()
