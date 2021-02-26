#!/usr/bin/env python
"""
Lightweight provenance for LSST DESC
Copyright (c) 2018-2021 LSST DESC
http://opensource.org/licenses/MIT
"""
from setuptools import setup

# read the contents of the README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="desc_provenance",
    description="Lightweight provenance for LSST DESC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/LSSTDESC/provenance",
    maintainer="Joe Zuntz",
    license="BSD",
    classifiers=[
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Development Status :: 3 - Alpha",
    ],
    packages=["desc_provenance"],
    entry_points={"console_scripts": ["ceci=ceci.main:main"]},
    setup_requires=[],
    install_requires=[""],
    extras_require={},
)
