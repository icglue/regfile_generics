# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "regfile_generics"
copyright = "2023, ICGlue.org"
author = "Felix Neumärker"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.duration",
    "autoapi.extension",
    "sphinx_multiversion",
]

autoapi_dirs = ["../src/regfile_generics"]
autodoc_typehints = "description"
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
    "imported-members",
]
# autoapi_keep_files = True

# def skip_member(app, what, name, obj, skip, options):
#    # skip submodules
#    if (obj.is_private_member):
#        #print(f"Skipping {obj.short_name}")
#        skip = True
#    return skip
#
# def setup(sphinx):
#    sphinx.connect("autoapi-skip-member", skip_member)

# Whitelist pattern for tags (set to None to ignore all tags)
smv_tag_whitelist = r"^.*$"

# Whitelist pattern for branches (set to None to ignore all branches)
smv_branch_whitelist = r"^master$"

# Whitelist pattern for remotes (set to None to use local branches only)
smv_remote_whitelist = None

# Pattern for released versions
smv_released_pattern = r"^tags/.*$"

# Format for versioned output directories inside the build directory
smv_outputdir_format = "{ref.name}"

# Determines whether remote or local git branches/tags are preferred if their output dirs conflict
smv_prefer_remote_refs = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# html_baseurl = "https://regfile-generics.icglue.org"
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_show_sourcelink = False
html_css_files = ["custom.css"]
