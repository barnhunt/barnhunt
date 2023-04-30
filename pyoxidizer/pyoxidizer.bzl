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

# The version of the barnhunt program.
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


# Any module not listed here gets omitted by the filter_stdlib filter (below)
# This is currently unused.
STDLIB_MODULES = []

# Configuration files consist of functions which define build "targets."
# This function creates a Python executable and installs it in a destination
# directory.
reported_resources = []
report_state = {}


def resource_repr(resource):
    bits = [type(resource)]
    for attr in ("path", "package", "name"):
        if hasattr(resource, attr):
            bits.append(getattr(resource, attr))
    if getattr(resource, "is_stdlib", False):
        bits.append("(stdlib)")
    return " ".join(bits)


def report_resource(policy, resource, prefix="", force=""):
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
    return resource_repr(resource) in reported_resources


def filter_stdlib(policy, resource):
    if not getattr(resource, "is_stdlib", False):
        return
    if not resource.add_include:
        return

    if type(resource) == "PythonPackageResource":
        name = resource.package
        if name.startswith("config-"):
            return
    else:
        name = resource.name
    if name in STDLIB_MODULES:
        return

    resource.add_include = False
    report_resource(policy, resource, "OMIT")


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
    if not force:
        if resource_already_reported(resource) or is_uninteresting(resource):
            return
    report_resource(policy, resource)
    report_state["was_file"] = type(resource) == "File"


def make_exe():

    dist = default_python_distribution(python_version=python_version)

    policy = dist.make_python_packaging_policy()
    # XXX: doesn't work yet
    # policy.register_resource_callback(filter_stdlib)
    policy.register_resource_callback(include_dlls)
    policy.register_resource_callback(include_extmodules)
    policy.register_resource_callback(filter_package_resources)
    # policy.register_resource_callback(report_resource)
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

    # Set initial value for `sys.path`. If the string `$ORIGIN` exists in
    # a value, it will be expanded to the directory of the built executable.

    # FIXME: needed? (neither seem to be?)
    # python_config.module_search_paths = ["$ORIGIN/lib"]
    # python_config.filesystem_importer = True

    # Write files containing loaded modules to the directory specified
    # by the given environment variable.
    # python_config.write_modules_directory_env = "/tmp/oxidized/loaded_modules"

    # Run a Python module as __main__ when the interpreter starts.
    # NB: sys.argv[0] ends up being None, so make sure to ancipate that
    # See https://github.com/indygreg/PyOxidizer/issues/307
    python_config.run_module = "barnhunt"

    # Make the embedded interpreter behave like a `python` process.
    # python_config.config_profile = "python"

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

    # Filter all resources collected so far through a filter of names
    # in a file.
    #exe.filter_resources_from_files(files=["/path/to/filter-file"])

    # Return our `PythonExecutable` instance so it can be built and
    # referenced by other consumers of this target.
    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    # Create an object that represents our installed application file layout.
    files = FileManifest()

    # Add the generated executable to our install layout in the root directory.
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

# Resolve whatever targets the invoker of this configuration file is requesting
# be resolved.
resolve_targets()
