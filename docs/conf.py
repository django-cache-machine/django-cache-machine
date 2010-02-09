import os
import sys

sys.path.append(os.path.abspath('..'))

import caching

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

extensions = ['sphinx.ext.autodoc']

# General information about the project.
project = u'Cache Machine'
copyright = u'2010, The Zamboni Collective'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# version: The short X.Y version.
# release: The full version, including alpha/beta/rc tags.
version = release = caching.__version__

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']
