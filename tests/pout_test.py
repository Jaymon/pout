# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import unittest

# this is the local pout that is going to be tested
import pout
from pout.compat import *

from . import testdata, TestCase


class PoutTest(TestCase):
    def test_tofile(self):
        path = testdata.get_file("pout.txt")
        with pout.tofile(path):
            s = "foobar"
            pout.b()
            pout.v(s)
            pout.h()

        r = path.read_text()
        self.assertTrue("foobar" in r)
        self.assertTrue("here" in r)

        with testdata.capture() as c:
            pout.v("after tofile")
        self.assertTrue("after tofile" in c)

    def test_issue16(self):
        """ https://github.com/Jaymon/pout/issues/16 """
        class Module(object): pass
        ret = "foo"
        default_val = "bar"
        self.issue_module = Module()
        self.issue_fields = {}
        k = "che"

        with testdata.capture() as c:
            pout.v(ret, default_val, getattr(self.issue_module, k, None), self.issue_fields.get(k, None))
        self.assertTrue('ret (3) = "foo"' in c)
        self.assertTrue('default_val (3) = "bar"' in c)
        self.assertTrue('getattr(self.issue_module, k, None) = None' in c)
        self.assertTrue('self.issue_fields.get(k, None) = None')

        del self.issue_module
        del self.issue_fields

    def test__get_arg_info(self):
        foo = 1
        with testdata.capture() as c:
            pout.v(foo)
        self.assertTrue('foo = 1' in c)

    def test_multi_command_on_one_line(self):
        """make sure we are finding the correct call on a multi command line"""
        name = "foo"
        val = 1
        with testdata.capture() as c:
            if not hasattr(self, name): pout.v(name); hasattr(self, name)
        self.assertTrue('name (3) = "foo"' in c)


if __name__ == '__main__':
    unittest.main()

