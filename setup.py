#!/usr/bin/env python

from setuptools import setup
from os.path import dirname, abspath, join

long_description_path = join(dirname(abspath(__file__)), 'README.md')
long_description = open(long_description_path, encoding='utf-8').read()

setup(
    name='imessage2csv',
    description='Export contacts and chat messages from iOS or macOS for easy viewing and searching',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/telnet23/imessage2csv',
    license='Apache License 2.0',
    use_scm_version=True,
    setup_requires=[
        'setuptools_scm',
    ],
    packages=[
        'imessage2csv',
    ],
    entry_points={
        'console_scripts': [
            'imessage2csv = imessage2csv.__main__:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: Apache Software License',
    ],
)
