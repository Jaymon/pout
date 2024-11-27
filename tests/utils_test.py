# -*- coding: utf-8 -*-

import pout
from pout.compat import *
from pout.utils import String, Color
from pout import environ

from . import TestCase, SkipTest


class StringTest(TestCase):
    def test___format__(self):
        """Make sure the String class can be formatted back and forth"""
        # if no exceptions are raised then the test passes
        s = String("poche, \u00E7a !")
        "{}".format(s)

    def test_indent(self):
        s = String("foo")
        self.assertTrue(s.indent(".", 3).startswith("..."))
        self.assertFalse(s.indent(".", 2).startswith("..."))

    def test_camelcase(self):
        s = String("foo_bar").camelcase()
        self.assertEqual("FooBar", s)

    def test_snakecase(self):
        s = String("FooBar").snakecase()
        self.assertEqual("foo_bar", s)


class ColorTest(TestCase):
    @classmethod
    def setUpClass(cls):
        environ.SHOW_COLOR = True

    def test_has_color_support(self):
        self.assertTrue(environ.has_color_support())
        environ.SHOW_COLOR = False
        self.assertFalse(environ.has_color_support())
        environ.SHOW_COLOR = True

    def test_color(self):
        if environ.has_color_support():
            text = Color.color("foo bar", "red")
            self.assertTrue("31m" in text)

        else:
            raise SkipTest("Color is not supported")

    def test_pout(self):
        """This doesn't test anything, it's just here for me to check colors"""
        def bar(one, two, three):
            pass

        class Foo(object):
            prop_str = "string value"
            prop_int = 123456
            prop_dict = {
                "key-1": "string dict value 1",
                "key-2": "string dict value 2"
            }

        d = {
            "bool-true": True,
            "bool-false": False,
            "float": 123456.789,
            "int": 1234456789,
            "none": None,
            "list": list(range(5)),
            "string": "foo bar che",
            "instance": Foo(),
            "class": Foo,
            "function": bar,
        }

        pout.v(d)

