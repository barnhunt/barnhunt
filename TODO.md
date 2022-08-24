# To-Dos and Ideas

## Templating

- Add a `metadata` jinja global (or some such) to provide access to document metadata.
  This could be used to template _judge name_, _trial date_, etc.

## PDF Manipulation

- Should look into whether our PDFs are PDF/A compliant.  And, if not, what
  we can do to make them so.

- _Optimization_: Use `qpdf`'s [`--object-streams=generate`][object-streams]?
  Currently we do this. It makes the PDFs a bit smaller.

- _Optimization_: Use `qpdf`'s [`--recompress-flate`][recompress-flate] (or equivalent)?
  Currently we do this. It makes the PDFs a bit smaller.

- _Optimization_: Does [linearization][] help us?  Currently we are
  doing this.  Does it hurt us?  Does it help us?

  From what I can glean via google it helps when streaming PDFs over
  the web.  I'm not sure it helps with local viewing (it may hurt,
  CPU-wise?) or with printing. (Though if the printer deals with PDF
  directly — does it?  — I guess that streaming optimizations would
  help.)

- _Optimization:_ In generated 2-up documents, perhaps we can
  move common resources (e.g. fonts) from individual _Form
  XObjects_ to the containing page's resources?

  It appears that Inkscape embeds "partial fonts" in each page,
  so it's not clear how straightforward it would be to merge them.
  It's probably not worth the effort.

### Compatibility

- Should a pure-python PDF manipulation library be needed in the
  future, look into using [PyPDF2](https://pypi.org/project/PyPDF2/) —
  it appears to be much more actively maintained than
  [pdfrw](https://pypi.org/project/pdfrw/) (which we used to use.)

[object-streams]: https://qpdf.readthedocs.io/en/latest/cli.html?highlight=object-streams#option-object-streams
[recompress-flate]: https://qpdf.readthedocs.io/en/latest/cli.html?highlight=object-streams#option-recompress-flate
[linearization]: https://qpdf.readthedocs.io/en/latest/cli.html?highlight=linearize#option-linearize

## Bugs in Other Packages

Should report/fix these?

### types-lxml

- `lxml.etree.register_namespace` (and `register_namespaces`?) is missing.
- `lxml.etree.QName` is not equality-comparable to str | bytes.
