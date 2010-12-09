#!/usr/bin/env python

from distutils.core import setup

setup(name = 'filesdir-check',
      version = '1.0',
      description = 'filesdir-check helps locate unused FILESDIR files',
      author = 'Jason Palmer',
      author_email = 'jalanpalmer@gmail.com',
      url = 'http://github.com/jalan/filesdir-check',
      license = 'GPLv2',
      py_modules = ['filesdir_check'],
      scripts = ['filesdir-check']
     )
