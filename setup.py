#!/usr/bin/env python

import setuptools
import sys

if {'bdist_wheel', 'sdist'}.intersection(sys.argv):
    long_description = open('README.rst').read()

setuptools.setup(
    name='glamkit-feincmstools',
    use_scm_version={'version_scheme': 'post-release'},  # Get version from git tags.
    description='Some neat and useful bits on top of FeinCMS',
    author='Interaction Consortium',
    author_email='studio@interaction.net.au',
    url='https://github.com/ixc/glamkit-feincmstools',
    long_description=locals().get('long_description', ''),
    license='BSD',
    packages=setuptools.find_packages(),
    include_package_data=True,
    setup_requires=['setuptools_scm'],
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
