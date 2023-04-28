# This file defines how PyOxidizer application building and packaging is
# performed. See PyOxidizer's documentation at
# https://gregoryszorc.com/docs/pyoxidizer/stable/pyoxidizer.html for details
# of this configuration file format.

print("BUILD_TARGET_TRIPLE", BUILD_TARGET_TRIPLE)
print("CONFIG_PATH", CONFIG_PATH)
print("CWD", CWD)
print("VARS", VARS)

# Configurable bits

# Python version to build
python_version = VARS.get("python_version", "3.10")

# The python distribution version of the barnhunt program.
barnhunt_version = VARS.get("barnhunt_version", "<dev>")

# This is for the installers we build.
# For the WiX (windows) installers, it must be in the format of
# 1 to 4 dotted integers.
product_version = VARS.get("product_version", "0.0")

version_module = "barnhunt._version"
project_root = CWD + "/.."

print("python_version", python_version)
print("product_version", product_version)
print("barnhunt_version", barnhunt_version)

# Configuration for WiX MSI installer generator
WIX_CONFIG = {
    "id_prefix": "barnhunt",
    "product_name": "Barnhunt",
    "product_version": product_version,
    "product_manufacturer": "Jeff Dairiki https://github.com/barnhunt",
}

INCLUDE_MODULES = """
#*
#runpy

click._textwrap
click.shell_completion
difflib
#_sysconfigdata__linux_x86_64-linux-gnu
#lxml.*
#PIL.*
#encodings.*
#logging.*
#http.*
#json.*
# Modules loaded by barnhunt <dev>
# 2023-04-27T18:46:36Z
# Command: 2up pdfs/novice.pdf
# Command: install
# Command: pdfs --no-shell-mode-inkscape tests/drawing.svg
# Command: pdfs tests/drawing.svg
# Command: rats
# Command: uninstall
_abc
abc
array
_ast
ast
atexit
atomicwrites
barnhunt
barnhunt.cli
barnhunt._compat
barnhunt.coursemaps
barnhunt.inkscape
barnhunt.inkscape.css
barnhunt.inkscape.runner
barnhunt.inkscape.svg
barnhunt.inkscape.utils
barnhunt.installer
barnhunt.installer.github
barnhunt.installer.metadata
barnhunt.layerinfo
barnhunt.pager
barnhunt.pdfutil
barnhunt.templating
barnhunt._version
base64
binascii
_bisect
bisect
_blake2
builtins
_bz2
bz2
calendar
certifi
certifi.core
cffi
cffi.api
cffi.error
cffi.lock
cffi.model
charset_normalizer
charset_normalizer.api
charset_normalizer.assets
charset_normalizer.cd
charset_normalizer.constant
charset_normalizer.legacy
charset_normalizer.md
charset_normalizer.md__mypyc
charset_normalizer.models
charset_normalizer.utils
charset_normalizer.version
click
click._compat
click.core
click.decorators
click.exceptions
click.formatting
click.globals
click.parser
click.termui
click.types
click.utils
_codecs
codecs
_collections
collections
_collections_abc
collections.abc
_compat_pickle
_compression
contextlib
copy
copyreg
_csv
csv
_cython_0_29_32
cython_runtime
dataclasses
_datetime
datetime
_decimal
decimal
dis
email
email.base64mime
email.charset
email._encoded_words
email.encoders
email.errors
email.feedparser
email.header
email.iterators
email.message
email._parseaddr
email.parser
email._policybase
email.quoprimime
email.utils
encodings
encodings.aliases
encodings.cp437
encodings.idna
encodings.unicode_escape
encodings.utf_16_be
encodings.utf_16_le
encodings.utf_8
enum
errno
fcntl
fnmatch
_frozen_importlib
_frozen_importlib_external
_functools
functools
__future__
genericpath
gettext
gzip
_hashlib
hashlib
_heapq
heapq
hmac
http
http.client
http.cookiejar
http.cookies
idna
idna.core
idna.idnadata
idna.intranges
idna.package_data
_imp
importlib
importlib._abc
importlib.abc
importlib._adapters
importlib._bootstrap
importlib._bootstrap_external
importlib._common
importlib.machinery
importlib.metadata
importlib.metadata._adapters
importlib.metadata._collections
importlib.metadata._functools
importlib.metadata._itertools
importlib.metadata._meta
importlib.metadata._text
importlib.readers
importlib.resources
importlib.util
inspect
_io
io
ipaddress
itertools
jinja2
jinja2.async_utils
jinja2.bccache
jinja2.compiler
jinja2.defaults
jinja2.environment
jinja2.exceptions
jinja2.filters
jinja2._identifier
jinja2.idtracking
jinja2.lexer
jinja2.loaders
jinja2.nodes
jinja2.optimizer
jinja2.parser
jinja2.runtime
jinja2.tests
jinja2.utils
jinja2.visitor
_json
json
json.decoder
json.encoder
json.scanner
keyword
linecache
_locale
locale
logging
lxml
lxml._elementpath
lxml.etree
_lzma
lzma
__main__
markupsafe
markupsafe._speedups
marshal
marshmallow
marshmallow.base
marshmallow.class_registry
marshmallow_dataclass
marshmallow_dataclass.lazy_class_attribute
marshmallow.decorators
marshmallow.error_store
marshmallow.exceptions
marshmallow.fields
marshmallow.orderedset
marshmallow.schema
marshmallow.types
marshmallow.utils
marshmallow.validate
marshmallow.warnings
math
mimetypes
__mp_main__
_multibytecodec
_multiprocessing
multiprocessing
multiprocessing.connection
multiprocessing.context
multiprocessing.dummy
multiprocessing.dummy.connection
multiprocessing.pool
multiprocessing.process
multiprocessing.queues
multiprocessing.reduction
multiprocessing.synchronize
multiprocessing.util
mypy_extensions
netrc
ntpath
numbers
_opcode
opcode
_operator
operator
os
os.path
packaging
packaging._elffile
packaging._manylinux
packaging.markers
packaging._musllinux
packaging._parser
packaging.requirements
packaging.specifiers
packaging._structures
packaging.tags
packaging._tokenizer
packaging.utils
packaging.version
pathlib
pexpect
pexpect.exceptions
pexpect.expect
pexpect.popen_spawn
pexpect.pty_spawn
pexpect.run
pexpect.spawnbase
pexpect.utils
_pickle
pickle
pikepdf
pikepdf._augments
pikepdf.codec
pikepdf._cpphelpers
pikepdf._exceptions
pikepdf.jbig2
pikepdf._methods
pikepdf.models
pikepdf.models._content_stream
pikepdf.models.encryption
pikepdf.models.image
pikepdf.models.matrix
pikepdf.models.metadata
pikepdf.models.outlines
pikepdf.models._transcoding
pikepdf.objects
pikepdf._qpdf
pikepdf.settings
pikepdf._version
pikepdf._xml
PIL
PIL._binary
PIL._deprecate
PIL.ExifTags
PIL.Image
PIL.ImageCms
PIL.ImageMode
PIL._imaging
PIL._imagingcms
PIL.TiffTags
PIL._util
PIL._version
platform
posix
posixpath
_posixsubprocess
pprint
pty
ptyprocess
ptyprocess.ptyprocess
ptyprocess.util
_queue
queue
quopri
_random
random
re
reprlib
requests
requests.adapters
requests.api
requests.auth
requests.certs
requests.compat
requests.cookies
requests.exceptions
requests.hooks
requests._internal_utils
requests.models
requests.packages
requests.packages.chardet
requests.packages.idna
requests.packages.idna.core
requests.packages.idna.idnadata
requests.packages.idna.intranges
requests.packages.idna.package_data
requests.packages.urllib3
requests.packages.urllib3._collections
requests.packages.urllib3.connection
requests.packages.urllib3.connectionpool
requests.packages.urllib3.contrib
requests.packages.urllib3.contrib._appengine_environ
requests.packages.urllib3.exceptions
requests.packages.urllib3.fields
requests.packages.urllib3.filepost
requests.packages.urllib3.packages
requests.packages.urllib3.packages.six
requests.packages.urllib3.packages.six.moves
requests.packages.urllib3.packages.six.moves.http_client
requests.packages.urllib3.packages.six.moves.urllib
requests.packages.urllib3.packages.six.moves.urllib.parse
requests.packages.urllib3.poolmanager
requests.packages.urllib3.request
requests.packages.urllib3.response
requests.packages.urllib3.util
requests.packages.urllib3.util.connection
requests.packages.urllib3.util.proxy
requests.packages.urllib3.util.queue
requests.packages.urllib3.util.request
requests.packages.urllib3.util.response
requests.packages.urllib3.util.retry
requests.packages.urllib3.util.ssl_
requests.packages.urllib3.util.ssl_match_hostname
requests.packages.urllib3.util.ssltransport
requests.packages.urllib3.util.timeout
requests.packages.urllib3.util.url
requests.packages.urllib3.util.wait
requests.packages.urllib3._version
requests.sessions
requests.status_codes
requests.structures
requests.utils
requests.__version__
resource
secrets
select
selectors
_sha512
shlex
shutil
_signal
signal
site
_sitebuiltins
_socket
socket
_sre
sre_compile
sre_constants
sre_parse
_ssl
ssl
_stat
stat
_string
string
stringprep
_strptime
_struct
struct
subprocess
sys
sysconfig
tempfile
termios
textwrap
_thread
threading
time
tinycss2
tinycss2.ast
tinycss2.bytes
tinycss2.parser
tinycss2.serializer
tinycss2.tokenizer
token
tokenize
traceback
tty
types
typing
typing_extensions
typing_inspect
typing.io
typing.re
unicodedata
urllib
urllib3
urllib3._collections
urllib3.connection
urllib3.connectionpool
urllib3.contrib
urllib3.contrib._appengine_environ
urllib3.exceptions
urllib3.fields
urllib3.filepost
urllib3.packages
urllib3.packages.six
urllib3.packages.six.moves
urllib3.packages.six.moves.http_client
urllib3.packages.six.moves.urllib
urllib3.packages.six.moves.urllib.parse
urllib3.poolmanager
urllib3.request
urllib3.response
urllib3.util
urllib3.util.connection
urllib3.util.proxy
urllib3.util.queue
urllib3.util.request
urllib3.util.response
urllib3.util.retry
urllib3.util.ssl_
urllib3.util.ssl_match_hostname
urllib3.util.ssltransport
urllib3.util.timeout
urllib3.util.url
urllib3.util.wait
urllib3._version
urllib.error
urllib.parse
urllib.request
urllib.response
uu
_uuid
uuid
_virtualenv
_warnings
warnings
_weakref
weakref
_weakrefset
webencodings
webencodings.labels
zipfile
zipimport
zlib
""".split()
print("INCLUDE_MODULES", INCLUDE_MODULES)

# Configuration files consist of functions which define build "targets."
# This function creates a Python executable and installs it in a destination
# directory.
reported_resources = []
report_state = {}


def resource_repr(resource):
    """Return __repr__ for resource.
    """
    bits = [type(resource)]
    for attr in ("path", "package", "name"):
        if hasattr(resource, attr):
            bits.append(getattr(resource, attr))
    if getattr(resource, "is_stdlib", False):
        bits.append("(stdlib)")
    return " ".join(bits)


def report_resource(policy, resource, prefix=""):
    """Report resource to stdout.

    Resource is prefix by PREFIX, if given.  If PREFIX is not specified a default
    prefix indicating whether the resource is currently slated to be included
    in the build is used.
    """
    pfx = prefix
    if prefix:
        pfx = prefix
    elif resource.add_include:
        pfx = "+++"
    else:
        pfx = "---      "

    rsrc = resource_repr(resource)
    print(pfx, rsrc)
    reported_resources.append(rsrc)
    report_state.clear()


def resource_already_reported(resource):
    """Has this resource already been reported?
    """
    return resource_repr(resource) in reported_resources


def exclude_unneeded(policy, resource):
    if not resource.add_include:
        return
    if (
        type(resource) == "PythonModuleSource"
        or type(resource) == "PythonExtensionModule"
    ):
        module = resource.name
    elif type(resource) == "PythonPackageResource":
        module = resource.package
    else:
        return

    if module in INCLUDE_MODULES:
        return

    parts = module.split(".")
    for n in range(len(parts) + 1):
        if ".".join(parts[:n] + ["*"]) in INCLUDE_MODULES:
            return

    resource.add_include = False
    report_resource(policy, resource, "UNNEEDED")


def filter_package_resources(policy, resource):
    if type(resource) != "PythonPackageResource" or not resource.add_include:
        return
    package = resource.name
    name = resource.name
    if (
        name == "py.typed" or name.endswith(".pyi")
        or name.endswith(".pxi")  # Pyrex source
        or name.endswith(".pyx")  # Cython source
        or name.endswith(".pxd")  # Cython source
        or name.endswith(".h") or name.endswith(".c")
        or package == "lxml.includes"
        or package == "lxml.isoschematron"
    ):
        resource.add_include = False
        report_resource(policy, resource, "OMIT")


def include_dlls(policy, resource):
    if type(resource) == "File" and (
        resource.path.find(".libs/") > 0      # linux
        or resource.path.find(".dylibs/") > 0  # macos
        or resource.path.lower().endswith(".dll")  # needed on win?
    ):
        resource.add_include = True
        resource.add_location = "filesystem-relative:lib"
        report_resource(policy, resource, "ADD")


def include_extmodules(policy, resource):
    if type(resource) == "PythonExtensionModule" and not resource.add_include:
        # XXX: Despite resource.add_include being False
        #
        #     policy.extension_module_filter = "all"
        #
        # seems to force their inclusion anyway (so, no problem, just confusing)
        #
        # I.e. setting add_include does not seem to be necessary, but improves
        # the reporting.
        resource.add_include = True
        # report_resource(policy, resource, "ADD?")


def is_uninteresting(resource):
    """Uninteresting resources are not reported, by default.
    """
    if type(resource) == "PythonExtensionModule":
        # these always seem to be included, regardless of .add_include
        return True
    if type(resource) == "PythonModuleSource":
        return resource.add_include or "test" in resource.name
    if type(resource) == "PythonPackageResource":
        return "test" in resource.package
    if type(resource) == "PythonPackageDistributionResource":
        return resource.add_include

    if type(resource) == "File":
        path = resource.path
        return (
            path.endswith(".py") or path.endswith(".pyc") or path.endswith(".pyo")
            # These seem always to be classified as
            # PythonPackageDistributionResource as well
            or ".dist-info/" in path
            or ".dist-info\\" in path
            # type stubs, etc.
            or path.endswith("/py.typed")
            or path.endswith("\\py.typed")
            or path.endswith(".pyi")
            # Pyrex
            or path.endswith(".pxi")
            # Cython
            or path.endswith(".pxd") or path.endswith(".pxy")
        )
    return False


def report_interesting(policy, resource):
    force = type(resource) != "File" and report_state.get("was_file", False)
    force = force or VARS.get("verbose")
    if not force:
        if resource_already_reported(resource) or is_uninteresting(resource):
            return
    report_resource(policy, resource)
    report_state["was_file"] = type(resource) == "File"


def make_exe():

    dist = default_python_distribution(python_version=python_version)

    policy = dist.make_python_packaging_policy()

    policy.register_resource_callback(exclude_unneeded)
    policy.register_resource_callback(include_dlls)
    policy.register_resource_callback(include_extmodules)
    policy.register_resource_callback(filter_package_resources)
    policy.register_resource_callback(report_interesting)

    policy.resources_location = "in-memory"
    policy.resources_location_fallback = "filesystem-relative:lib"

    # This appears to be required or the pikepdf._qpdf
    # extension module failsto load
    policy.allow_in_memory_shared_library_loading = False

    policy.extension_module_filter = "all"

    policy.allow_files = True
    policy.file_scanner_classify_files = True
    policy.file_scanner_emit_files = True
    policy.include_classified_resources = True
    policy.include_file_resources = False

    policy.include_non_distribution_sources = True
    policy.include_test = False
    policy.include_distribution_sources = True
    policy.include_distribution_resources = True

    # This variable defines the configuration of the embedded Python
    python_config = dist.make_python_interpreter_config()

    # FIXME: needed? (neither seem to be?)
    # python_config.module_search_paths = ["$ORIGIN/lib"]
    # python_config.filesystem_importer = True

    if not VARS.get("build-python"):
        # Run a Python module as __main__ when the interpreter starts.
        # NB: sys.argv[0] ends up being None, so make sure to ancipate that
        # See https://github.com/indygreg/PyOxidizer/issues/307
        python_config.run_module = "barnhunt"
    else:
        # Make the embedded interpreter behave like a `python` process.
        # python_config.config_profile = "python"
        python_config.config_profile = "python"

    exe = dist.to_python_executable(
        name="barnhunt",
        packaging_policy=policy,
        config=python_config,
    )

    for resource in exe.pip_install(["--only-binary", ":all:", project_root]):
        if type(resource) == "PythonModuleSource" and resource.name == version_module:
            # mangle the the version module
            resource = exe.make_python_module_source(
                version_module,
                '__version__ = "{}"'.format(barnhunt_version),
                resource.is_package,
            )
        exe.add_python_resource(resource)

    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

def make_msi(exe):
    return exe.to_wix_msi_builder(**WIX_CONFIG)

def make_bundle(exe):
    # This builds both a .exe and a .msi installer
    # If you run this, you don't need to run make_msi
    return exe.to_wix_bundle_builder(**WIX_CONFIG)

# Tell PyOxidizer about the build targets defined above.
register_target("exe", make_exe)
register_target("resources", make_embedded_resources,
                depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_msi, depends=["exe"])
register_target("exe_installer", make_bundle, depends=["exe"])

resolve_targets()
