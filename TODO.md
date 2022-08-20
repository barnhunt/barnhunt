# To-Dos and Ideas

## Test and fix for modern Inkscapes

- Add support for specifying Inkscape binary via $INKSCAPE_COMMAND.  (Default to `inkscape.exe` on Windows.  [Here's what `inkex` does][1])

[1]: <https://gitlab.com/inkscape/extensions/-/blob/cb74374e46894030775cf947e97ca341b6ed85d8/inkex/command.py#L45>


## Templating

- Add a `metadata` jinja global (or some such) to provide access to document metadata.
  This could be used to template _judge name_, _trial date_, etc.
