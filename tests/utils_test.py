# -*- coding: utf-8 -*-

# this is the local pout that is going to be tested
from pout.compat import *
from pout.utils import String, Bytes
from pout import environ

from . import TestCase


class StringTest(TestCase):
    def test___format__(self):
        """Make sure the String class can be formatted back and forth"""
        # if no exceptions are raised then the test passes
        s = String("poche, \u00E7a !")
        "{}".format(s)

    def test_indent(self):
        chars = environ.INDENT_STRING
        environ.INDENT_STRING = "."
        s = String("foo")
        self.assertTrue(s.indent(3).startswith("..."))
        self.assertFalse(s.indent(2).startswith("..."))
        environ.INDENT_STRING = chars

    def test_camelcase(self):
        s = String("foo_bar").camelcase()
        self.assertEqual("FooBar", s)

    def test_snakecase(self):
        s = String("FooBar").snakecase()
        self.assertEqual("foo_bar", s)

