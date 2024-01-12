#!/usr/bin/env python

"""The setup script."""

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(

    author="redis3",
    author_email='jacopo.tagliabue@bauplanlabs.com',
    python_requires='>=3.9',
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    description="redis3",
    install_requires=requirements,
    license="MIT license",
    long_description=readme,
    long_description_content_type="text/x-rst",
    include_package_data=True,
    keywords="reclist",
    name="reclist",
    packages=find_packages(include=["redis3", "redis3.*"]),

    url='https://github.com/BauplanLabs/redis3',
    version='0.0.2',
    zip_safe=False,
    extras_require={},
)