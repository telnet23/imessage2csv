#!/usr/bin/env python

import os
import setuptools

path = os.path.dirname(os.path.abspath(__file__))

setuptools.setup(
    name='imessage2csv',
    description='Export contacts and chat messages from iOS or macOS for easy viewing and searching',
    long_description=os.path.join(path, 'README.md').read_file(),
    long_description_content_type='text/markdown',
    url='https://github.com/telnet23/imessage2csv',
#    author_email='',
#    author='',
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
