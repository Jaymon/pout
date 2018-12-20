# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os

from .compat import String


class Path(String):
    """Returns a path string relative to the current working directory (if applicable)"""
    def __new__(cls, path):
        cwd = os.getcwd()
        if path.startswith(cwd):
            path = path.replace(cwd, "", 1).lstrip(os.sep)
        return super(Path, cls).__new__(cls, path)

