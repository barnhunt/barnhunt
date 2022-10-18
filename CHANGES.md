## Changes

### Release 1.2.0rc2 (2022-10-17)

### Extension and Symbol Set Installation

- This release add a `barnhunt install` (and `uninstall`) sub-command
  to simplify installation of the
  [inkex-bh](https://github.com/barnhunt/inkex-bh) Inkscape extensions
  and [bh-symbols](https://github.com/barnhunt/bh-symbols) symbol
  sets.

#### Testing

- Update to `mypy==0.982` for testing. Fix spurious mypy errors.

### Release 1.2.0rc1 (2022-08-31)

First public release to PyPI. Moved project to
[GitHub](https://github.com/barnhunt/barnhunt).

- Dropped support for python 3.6
- Changed license to GPL version 3
- We now do rudimentary testing under Windows and macOS.

#### Dependencies

- Use [pikepdf](https://pypi.org/project/pikepdf/) instead of
  [pdfrw](https://pypi.org/project/pdfrw/) to manipulate PDFs.  (Pdfrw
  seems not to be very actively maintained.) The only possible
  downside of this is that `pikepdf` is not pure-python. It claims to
  be easily installable on Windows and _x86_64_ Macs, but is not
  (easily) installable on Macs with Apple silicon.

- Generated PDFs are now [linearized][qpdf-linearize] and
  [compressed][qpdf-object-streams].

- Add test dependency on
  [pdfminer.six](https://pypi.org/project/pdfminer.six/) (but drop
  dependency on [PyPDF2](https://pypi.org/project/PyPDF2/)).


#### Compatibility

- Refactor `barnhunt.inkscape.runner` to support running
  Inkscape >= 1.0 (as well as continuing to support Inkscape 0.9x).

- Add `--inkscape-command` parameter to the `barnhunt pdfs` command
  to specify the name/path of the Inkscape binary to run to export PDFs.
  This also supports setting the Inkscape executable via the `$INKSCAPE_COMMAND`
  environment variable.  Default executable is not `inkscape.exe` on Windows
  (and `inkscape` everywhere else).

- Use `pexpect.popen_spawn.PopenSpawn` instead of `pexpect.spawn` to
  run Inkscape in shell-mode. Due to `pexpect.spawn`'s use of ptys, it
  [will not work][pexpect-windows] on Windows.

- **MacOS**: our code for running Inkscape in shell-mode appears to be broken.
  For now, on _macOS_ we default to not using shell-mode.

#### Packaging

- Added a stub `barnhunt.__main__` module to allow running via `python
  -m barnhunt`.

#### Testing

- Add type annotations.

#### Bit Rot

- Fix up tests to address deprecations in PyPDF2.

[qpdf-linearize]: https://qpdf.readthedocs.io/en/latest/cli.html?highlight=linearize#option-linearize
[qpdf-object-streams]: https://qpdf.readthedocs.io/en/latest/cli.html?highlight=object-streams#option-object-streams
[pexpect-windows]: https://pexpect.readthedocs.io/en/stable/overview.html#windows

### Release 1.1.0a1 (2022-03-08)

#### "Base Map" support

Add ability to mark layers for exclusion from particular output files.

This adds the ability to list multiple comma-separated output base
filenames for a given overlay.
E.g. A layer with label `"[o|build_notes,base] Build Notes"`
will define an overlay which will generate maps in two separate
output files.

Tagging a layer with `[!`_output-basename_`]` will exclude that
layer from any maps which are directed to the specified output
filename.

Tagging a layer with `[=`_output-basename_`]` will include that layer
from any maps which are directed to the specified output filename, while
excluding all other sibling layers not explicitly tagged to be included
in that output file.


### Release 1.0.1 (2021-11-10)

#### Diagnostics

`Barnhunt pdfs` now issues a warning when generating PDFs from an SVG
file which does not have an explicit random-seed set.

#### Bugs Fixed

Open SVG files in binary mode in order to let the XML parser figure
out the encoding from the XML declaration.

### Release 1.0 (2021-11-10)

Support python 3.10.

#### Random Seed

The way the random seed (used for generating random rat numbers) for
each SVG layer is computed has been changed in a
**backward-incompatible** way.  This was done so that rat numbers can
be kept from changing when an SVG source file is copied or edited in
such a way that the device and/or inode of the file changes.

Now, the file-level random seed (an integer) is read from the
`bh:random-seed` attribute of the root `svg` element of the SVG
file. If no `bh:random-seed` attribute is set, the file-level seed is
computed by hashing the device and inode numbers of the SVG file.

The layer-level seed is formed by hashing the file-level random seed
with the XML *id* of the layer.

(Formerly, the layer-level seed was form by hashing a triple of the
file-level seed (which was always zero), the hash of the SVG files
device and inode, and the id of the layer.)

A new `barnhunt random-seed` sub-command has been implemented to help
with setting the random seed for SVG source files.

#### Bit-rot

Address `DeprecationWarning: 'contextfunction' is renamed to
'pass_context'` from Jinja2. Require `Jinja2>3`.

#### OCDisms

Run `pyupgrade --py36-plus` on source.


### Release 0.5 (2021-05-04)

Make `-o` option to `2up` sub-command optional.

Remove support for python < 3.6.

### Release 0.4 (2019-02-25)

#### New Sub-Command: 2up

New `2up` sub-command to format PDFs for 2-up printing.  Pages are
pre-shuffled so that the 2-up pages do not need to be shuffled after
cutting.


### Release 0.3 (2019-02-20)

#### `barnhunt pdfs`

- Multi-page output support.

  There is a new syntax to specify the output file basename for an overlay.
  Multiple overlays which specify the same output file will all be saved to
  the same file.

- It is now possible to render course maps from multiple SVG files in a
  single invocation.  (Just list all the files to be rendered on the
  command line.)

#### Tests

- `test_layerinfo.test_layerflags_str`: Fix test to deal with
  arbitrary ordering of `enum.Flag` flags.

### Release 0.2 (2018-11-07)

#### Templating

- Do not expand text within hidden layers.  This avoids generating
  error messages (e.g. "'overlay' is undefined") due to template
  expansion of unused text.

- Add optional `skip` argument to the `random_rats` function.
  This allows the generation of more than one set of stable random rat
  numbers per layer.  E.g. `random_rats(skip=5)` will generate a set
  of random number totally uncorrelated to that generated by
  `random_rats()`.  Using `skip` has the advantage over using
  `seed=None` that the results are stable and do not vary from
  render to render.

### Release 0.1 (2018-11-07)

- Python 3.7 is now supported.

- The template for the output filename has been generalized to work
  sensibly in the case where overlays are nested more than two deep.

#### Templating

- Added new attributes to layers:

  `layer.is_overlay`
      Boolean.  True if layer is an overlay.

  `layer.lineage`
      Sequence starting with layer and including each parent layer in
      turn.

  `layer.overlay`
      Returns the nearest overlay layer.  If the layer is an overlay,
      `layer.overlay` returns `layer`, otherwise it returns the
      nearest parent layer which is an overlay.  If the layer is not
      contained within an overlay, returns `None`.

- Added new values to context when expanding text in SVG:

  `overlays`
      A list of all overlay layers in the lineage of the text
      element, in order from outermost to innermost.

  `course`
      The outermost overlay layer.  (Equivalent to `overlays[0]`.)
      This value already existed in the context used for filename expansion.

  `overlay`
      If the element is at least two overlays deep, this is the
      innermost overlay.  Otherwise it is unset.  This value already
      existed in the context used for filename expansion.

- Added new values to context when expanding output filenames:

  `overlays`
      A list of all overlay layers in the lineage of the overlay
      being expanded.

#### Bugs

- Templating: the `safepath` filter would fail with a `TypeError`
  if applied to anything but a string.  Now it coerces its argument to
  text.

- Templating: (New style) layer flags in parent layers were not being
  removed from the layer labels.  (E.g. `"{{ layer.parent.label }}"`
  was expanding to `"[o] Some Overlay"`, when it should expand to
  `"Some Overlay"`.)

- Pexpect==4.4.0 appears to have a subtle brokenness when
  `searchwindowsize` is set to something other than `None`.  The
  problem seems to be in [pexpect.expect.py][], and is triggered when
  multiple chunks of output are read before a match is found.

[pexpect.expect.py]: <https://github.com/pexpect/pexpect/blob/606f368b4a0dc442e2523d439d722a389b6e54c6/pexpect/expect.py#L22>

#### Bit-Rot

- Use `log.warning`, rather than the deprecated `log.warn`.

### Release 0.1a12 (2017-02-09)

- Remove tags from layer.label when expanding templated text in SVG file.

### Release 0.1a11 (2017-02-01)

- Add `--version` command line option

#### Pager for `coords`

- A fancy pager (poor man's `less`) has been added for viewing the
  output of the `barnhunt coords` sub-command.  If any of `sys.stdin`
  or `sys.stdout` is not a tty, then the pager will be disabled.

- Since there is now a fancy pager, the default for `--number-of-rows`
  has been increased to 1000.

### Release 0.1a10 (2017-01-30)

#### Things still to be fixed

Things still to be fixed: I'm pretty sure things are direly broken if
a drawing contains no overlays, and somewhat broken if a drawing
contains more than two layers of overlays.  The problems have to do
with how the output PDF filenames are determined...

#### New layer flag scheme

New scheme for marking overlay and hidden layers.  One can now set
bit-flags on layers by including the flags in square brackets at the
beginning of the layer label.  I.e. a label like `"[o] Master Trial
1"` marks the layer as an overlay layer, while `"[h] Prototypes"`
marks a hidden layer.

If no layers have any flags, `barnhunt pdfs` will fall back to the
old name-based heuristics for determining hidden and overlay layers.


### Release 0.1a9 (2017-01-03)

* When exporting PDFs, run `inkscape` with `--export-area-page`.

#### Packaging

* Fix MANIFEST.in. Tests were not being included in sdist.

* Add `url` to package metadata.

### Release 0.1a8 (2018-01-03)

* Ignore *ring* layers when identifying *course* layers.  (Now a layer
  labeled “C8 Ring” will not be treated as a course layer.)

* `pdfs`: default `--output-directory` to `.` (avoiding exception when no
  explicit output directory is specified.)

### Release 0.1a7 (2017-11-18)

* Change `barnhunt coords` so that it omits duplicate coordinates in its output.
  Also increase the default for `--number-of-rows` to 50 and
  add the `--group-size` parameter to separate output into groups.

### Release 0.1a6 (2017-11-15)

* Templating: `LabelAdapter` now stringifies to the layer label, and
  `FileAdapter` now stringifies to the file name.
* More refactoring, more tests
* Run several inkscapes in parallel.  This results in a major speedup.

### Release 0.1a5 (2017-11-13)

* Expand text in SVG file.
* Add tests.
* Major code refactor.

### Release 0.1a4 (2017-11-10)

#### PDFS

* Log unexpected output from inkscape.

* Add `--no-shell-mode-inkscape` option to control whether shell-mode inkscape
  optimization is used.

### Release 0.1a3.post1 (2017-11-10)

#### PDFS

* Reverse order that layers are considered.  (Layers are listed from
  bottom to top in the SVG file.)

### Release 0.1a3 (2017-11-10)

#### PDFS

Replace spaces and other shell-unfriendly characters with underscores
in output file names.

### Release 0.1a2 (2017-11-09)

Add sub-commands for generating random numbers.

### Release 0.1a1 (2017-11-07)

Initial release.
