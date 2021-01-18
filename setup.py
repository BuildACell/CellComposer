import os
import glob
import setuptools
from distutils.core import setup

with open("README.md", 'r') as readme:
    long_description = readme.read()

setup(
    name='vivarium-bioscrape',
    version='0.0.0.1',
    packages=[
        'vivarium_bioscrape',
        'vivarium_bioscrape.processes',
        'vivarium_bioscrape.composites',
        'vivarium_bioscrape.experiments',
        'vivarium_bioscrape.library'
    ],
    author='William Poole, Eran Agmon, Ryan Spangler',  # TODO: Put your name here.
    author_email='',
    url='https://github.com/vivarium-collective/vivarium-bioscrape',  # TODO: Put your project URL here.
    license='MIT',
    entry_points={
        'console_scripts': []},
    short_description='',  # TODO: Describe your project briefely.
    long_description=long_description,
    long_description_content_type='text/markdown',
    package_data={},
    include_package_data=True,
    install_requires=[
        'vivarium-core',
        'bioscrape'
    ],
)
