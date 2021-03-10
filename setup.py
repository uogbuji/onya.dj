#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Highly recommend installing using `pip install -U .` not `python setup.py install`

Uses pkgutil-style namespace package (Working on figuring out PEP 420)

Note: careful not to conflate install_requires with requirements.txt

https://packaging.python.org/discussions/install-requires-vs-requirements/

Reluctantly use setuptools for now to get install_requires & long_description_content_type

$ python -c "import onya.dj.version; print(onya.dj.version.version_info)"
('0', '0', '1')
'''

import sys
from setuptools import setup, Extension
#from distutils.core import setup, Extension

PROJECT_NAME = 'onya.dj'
PROJECT_DESCRIPTION = "DJ tools with data managed in a property graph"
PROJECT_LICENSE = 'License :: OSI Approved :: Apache Software License'
PROJECT_AUTHOR = 'Uche Ogbuji'
PROJECT_AUTHOR_EMAIL = 'uche@ogbuji.net'
PROJECT_URL = 'https://github.com/uogbuji/onya.dj'
PACKAGE_DIR = {'onya': 'pylib'}
PACKAGES = ['onya.dj', 'onya.dj.serial']
SCRIPTS = [
        'exec/onya.dj',
]

CORE_REQUIREMENTS = [
    #'click',
    'click',
    'pytest',
]

EXTRA_REQUIREMENTS = [
    'pytest-mock', # For testing
]

# From http://pypi.python.org/pypi?%3Aaction=list_classifiers
CLASSIFIERS = [
    "Programming Language :: Python",
    "Programming Language :: Python :: 3",
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: Apache Software License",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Internet :: WWW/HTTP",
]

KEYWORDS=['music', 'data']

versionfile = 'pylib/dj/version.py'
exec(compile(open(versionfile, "rb").read(), versionfile, 'exec'), globals(), locals())
__version__ = '.'.join(version_info)

LONGDESC = '''# Onya/DJ

DJ tools with data managed in a property graph.
'''

LONGDESC_CTYPE = 'text/markdown'

setup(
    name=PROJECT_NAME,
    version=__version__,
    description=PROJECT_DESCRIPTION,
    license=PROJECT_LICENSE,
    author=PROJECT_AUTHOR,
    author_email=PROJECT_AUTHOR_EMAIL,
    #maintainer=PROJECT_MAINTAINER,
    #maintainer_email=PROJECT_MAINTAINER_EMAIL,
    url=PROJECT_URL,
    package_dir=PACKAGE_DIR,
    packages=PACKAGES,
    scripts=SCRIPTS,
    install_requires=CORE_REQUIREMENTS,
    classifiers=CLASSIFIERS,
    long_description=LONGDESC,
    long_description_content_type=LONGDESC_CTYPE,
    keywords=KEYWORDS,
)
