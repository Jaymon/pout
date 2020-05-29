# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

# this is the local pout that is going to be tested
from pout.compat import *
from pout.utils import String, Bytes
from pout import environ

from . import testdata, TestCase


class StringTest(TestCase):
    def test___format__(self):
        """Make sure the String and Bytes classes can be formatted back and forth"""
        # if no exceptions are raised then the test passes
        #s = String("poche, ça !")
        s = String("poche, \u00E7a !")
        b = Bytes(s)

        "{}".format(s)
        "{}".format(b)

        if is_py2:
            b"{}".format(s)
            b"{}".format(b)

    def test_indent(self):
        chars = environ.INDENT_STRING
        environ.INDENT_STRING = "."
        s = String("foo")
        self.assertTrue(s.indent(3).startswith("..."))
        self.assertFalse(s.indent(2).startswith("..."))
        environ.INDENT_STRING = chars

