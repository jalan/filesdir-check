#!/usr/bin/env python

from distutils.core import setup

setup(
	name='filesdir-check',
	version='1.1',
	description='filesdir-check helps locate unused FILESDIR files',
	author='Jason Alan Palmer',
	author_email='jalanpalmer@gmail.com',
	url='http://github.com/jalan/filesdir-check',
	py_modules=['filesdir_check'],
	scripts=['filesdir-check'],
	classifiers=[
		"License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
		"License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
		]
     )
