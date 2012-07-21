#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='glamkit-feincmstools',
    version='0.5.0',
    description='Some neat and useful bits on top of FeinCMS',
    author='Greg Turner',
    author_email='greg@interaction.net.au',
    url='http://glamkit.org/',
    packages=find_packages(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
    ]
)