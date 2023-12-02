#!/usr/bin/env python3

# import os
from setuptools import setup, find_packages
from sonagent.version import __version__

# load the README file and use it as the long_description for PyPI
with open('README.md', 'r', encoding="utf8") as f:
    readme = f.read()

install_requires =[
    'pandas',
    'ipython',
    'pylint',
    'sphinx-material',
    'numpydoc',
    'nbsphinx',
    'recommonmark',
    'sphinx-markdown-tables',
    'sphinx_copybutton',
    'readthedocs-sphinx-search'
]

# package configuration - for reference see:
# https://setuptools.readthedocs.io/en/latest/setuptools.html#id9
setup(
    name="sonagent",
    description="Autonomous Agent for Digital Consciousness Backup Using Large Language Models (LLM).",
    long_description=readme,
    long_description_content_type='text/markdown',
    version=__version__,
    author="Son Nguyen Huu",
    author_email="sonnhfit@gmail.com",
    url="https://github.com/sonnhfit/sonagent",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.9.0",
    install_requires=install_requires,
    license="MIT",
    zip_safe=False,
    entry_points={
        'console_scripts': ['py-package-template=py_pkg.entry_points:main'],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.12",
    ],
    keywords='agent ai ml language-model autonomus-robots large-language-models llm chatgpt llama2'
)
