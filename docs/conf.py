# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "regfile_generics"
copyright = "2023, Felix Neumärker"
author = "Felix Neumärker"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.duration",
    "sphinx.ext.githubpages",
    "autoapi.extension",
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

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_baseurl = "https://regfile-generics.icglue.org"
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_show_sourcelink = False
html_css_files = ["custom.css"]
