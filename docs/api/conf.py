# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# Add the source directory to the path
sys.path.insert(0, os.path.abspath('../../src/'))

# -- Project information -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Configurable Agents'
copyright = '2026, Configurable Agents Contributors'
author = 'Configurable Agents Contributors'
release = '0.1.0'
version = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',        # Auto-generate from docstrings
    'sphinx.ext.napoleon',       # Google/NumPy style docstrings
    'sphinx.ext.viewcode',       # View source code links
    'sphinx.ext.intersphinx',    # Link to other projects' docs
    'myst_parser',               # Markdown support
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix(es) of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.md': 'markdown',
}

# The master toctree document.
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'collapse_navigation': False,
    'sticky_navigation': True,
    'includehidden': True,
    'titles_only': False,
}

# -- Options for autodoc -----------------------------------------------------

autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Show inherited members
autodoc_inherit_docstrings = True

# Type hints formatting
autodoc_typehints = 'signature'
autodoc_typehints_description_target = 'documented'

# -- Options for napoleon -----------------------------------------------------

napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_preprocess_types = False
napoleon_type_aliases = None
napoleon_attr_annotations = True

# -- Options for intersphinx -------------------------------------------------

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pydantic': ('https://docs.pydantic.dev/latest/', None),
    'langchain': ('https://python.langchain.com/', None),
}

# -- Options for MyST parser -------------------------------------------------

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]

# -- HTML context -------------------------------------------------------------

html_context = {
    'display_github': True,
    'github_user': 'yourusername',
    'github_repo': 'configurable-agents',
    'github_version': 'main/docs/api',
}

# -- Options for HTML help output -------------------------------------------

htmlhelp_basename = 'ConfigurableAgentsdoc'
