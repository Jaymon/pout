# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

from . import testdata, TestCase

import pout
from pout.compat import *
from pout.reflect import Call, CallString, Reflect


class ReflectTest(TestCase):
    def test_discovery(self):
        foo = 1
        pout.v(foo, "foo bar che")


class CallTest(TestCase):
    def test_trace(self):
        pout.t()

    def test_ipython_fail(self):
        '''
        ipython would fail because the source file couldn't be read

        since -- 7-19-12
        '''
        mp_orig = pout.Pout.call_class.__init__

        def _get_call_info_fake(self, frame_tuple, called_module='', called_func=''):
            call_info = {}
            call_info['frame'] = frame_tuple
            call_info['line'] = frame_tuple[2]
            call_info['file'] = '/fake/file/path'
            call_info['call'] = ''
            call_info['arg_names'] = []
            self.info = call_info
            #return call_info

        # monkey patch to do get what would be returned in an iPython shell
        pout.Pout.call_class.__init__ = _get_call_info_fake

        # this should print out
        with testdata.capture() as c:
            pout.v(list(range(5)))
        self.assertTrue("Unknown 0 (5)" in c)
        self.assertTrue("0: 0," in c)
        self.assertTrue("4: 4" in c)

        pout.Pout.call_class.__init__ = mp_orig


class CallStringTest(TestCase):
    def test_is_complete_1(self):
        c = CallString("foo(bar")
        self.assertFalse(c.is_complete())

        c = CallString("foo())")
        self.assertFalse(c.is_complete())

        c = CallString('foo("".join(bar.che), func())')
        self.assertTrue(c.is_complete())

        c = CallString("\n".join([
            "        pout.v(",
            '            "foo",',
            '            "bar",',
            '            "che",',
            '        )'
        ]))
        self.assertTrue(c.is_complete())

    def test_is_complete_2(self):
        c = CallString('foo(bar, "a) something"')
        self.assertFalse(c.is_complete())

        c = CallString('foo(bar, "a) something")')
        self.assertTrue(c.is_complete())

        c = CallString('foo("a) something"); func()')
        self.assertTrue(c.is_complete())

    def test_arg_names_1(self):
        c = CallString('pout.v(left, " ".join(FooIssue34.bar_che), right)')
        arg_names = c.arg_names()
        self.assertEqual(3, len(arg_names))

    def test_arg_names_2(self):
        """see also VTest.test_multiline_comma()"""

        # NOTE 12-21-2018 this used to pass with the old parsing code (it's
        # invalid) but using the tokenize module means this no longer works
        r = CallString("\n".join([
            "        pout.v(",
            '"foo",',
            '"bar",',
            '"che"'
        ])).arg_names()
        self.assertEqual(0, len(r))
#         for x in range(3):
#             self.assertEqual("", r[x])

        r = CallString("\n".join([
            "        pout.v(",
            '            "foo",',
            '            "bar",',
            '            "che",',
            '        )'
        ])).arg_names()
        self.assertEqual(3, len(r))
        for x in range(3):
            self.assertEqual("", r[x])

        r = CallString("        pout.v(\"this string has 'mixed quotes\\\"\")").arg_names()
        self.assertEqual(1, len(r))
        self.assertEqual("", r[0])

        r = CallString(" pout.v(name); hasattr(self, name)").arg_names()
        self.assertEqual("name", r[0])
        self.assertEqual(1, len(r))

        r = CallString("\n".join([
            "        pout.v(",
            '"foo",',
            '"bar",',
            '"che",',
            ")"
        ])).arg_names()
        for x in range(3):
            self.assertEqual("", r[x])

        tests = {
            "pout.v(foo, [bar, che])": ["foo", "[bar, che]"],
            "pout.v(foo, bar)": ["foo", "bar"],
            "pout.v(foo)": ["foo"],
            "pout.v('foo')": [""],
            'pout.v("foo")': [""],
            "pout.v('foo\'bar')": [""],
            "pout.v('foo, bar, che')": [""],
            "pout.v((foo, bar, che))": ["(foo, bar, che)"],
            "pout.v((foo, (bar, che)))": ["(foo, (bar, che))"],
            "pout.v([foo, bar, che])": ["[foo, bar, che]"],
            "pout.v([foo, [bar, che]])": ["[foo, [bar, che]]"],
            "pout.v([[foo], [bar, che]])": ["[[foo], [bar, che]]"],
        }
        for inp, outp in tests.items():
            r = CallString(inp).arg_names()
            for i, expected in enumerate(r):
                self.assertEqual(expected, r[i])

    def test_multi_args(self):
        '''
        since -- 6-30-12

        this actually tests _get_arg_names
        '''

        foo = 1
        bar = 2
        che = {'foo': 3, 'bar': 4}

        def func(a, b):
            return a + b


        with testdata.capture() as c:
            pout.v("this string has 'mixed quotes\"")
        self.assertTrue("this string has 'mixed quotes\"" in c)

        with testdata.capture() as c:
            pout.v('this string has \'mixed quotes"')
        self.assertTrue('this string has \'mixed quotes"' in c)

        with testdata.capture() as c:
            pout.v('this string has \'single quotes\' and "double quotes"')
        self.assertTrue('this string has \'single quotes\' and "double quotes"' in c)

        with testdata.capture() as c:
            pout.v(foo, 'this isn\'t a string, just kidding')
        self.assertTrue("foo" in c)
        self.assertTrue('this isn\'t a string, just kidding' in c)

        with testdata.capture() as c:
            pout.v('this string is formatted {} {}'.format(foo, bar))
        self.assertTrue('this string is formatted 1 2' in c)

        with testdata.capture() as c:
            pout.v('this string' + " is added together")
        self.assertTrue("this string is added together" in c)

        with testdata.capture() as c:
            pout.v(func('this string', " has 'single quotes'"))
        self.assertTrue("this string has 'single quotes'" in c)

        with testdata.capture() as c:
            pout.v('this string has \'single quotes\'')
        self.assertTrue("this string has 'single quotes'" in c)

        with testdata.capture() as c:
            pout.v("this string has \"quotes\"")
        self.assertTrue("this string has \"quotes\"" in c)

        with testdata.capture() as c:
            pout.v(che['foo'], che['bar'])
        self.assertTrue("che['foo']" in c)
        self.assertTrue("che['bar']" in c)

        with testdata.capture() as c:
            pout.v(foo, "this isn't a string, just kidding")
        self.assertTrue("foo" in c)
        self.assertTrue('this isn\'t a string, just kidding' in c)

        with testdata.capture() as c:
            pout.v(foo, "(a) this is a string")
        self.assertTrue("foo" in c)
        self.assertTrue("(a) this is a string" in c)

        with testdata.capture() as c:
            pout.v(foo, "(a this is a string")
        self.assertTrue("foo" in c)
        self.assertTrue("(a this is a string" in c)

        with testdata.capture() as c:
            pout.v(foo, "a) this is a string")  
        self.assertTrue("foo" in c)
        self.assertTrue("a) this is a string" in c)

        with testdata.capture() as c:
            pout.v(foo, "this is a, string")
        self.assertTrue("foo" in c)
        self.assertTrue("this is a, string" in c)

        with testdata.capture() as c:
            pout.v(foo, "this is a simple string")
        self.assertTrue("foo" in c)
        self.assertTrue("this is a simple string" in c)

        with testdata.capture() as c:
            pout.v(foo, bar, func(1, 2))
        self.assertTrue("foo" in c)
        self.assertTrue("bar" in c)
        self.assertTrue("func(1, 2)" in c)

    def test_string_arg(self):
        #self.skipTest("I was using this to debug a lot of the above tests")
        foo = 1
        bar = 2
        che = {'foo': 3, 'bar': 4}

        def func(a, b):
            return a + b

        pout.v(type([]))
        return

        pout.v(func(1, 2))
        return 

        pout.v(func('this string', " has 'single quotes'"))
        return

        pout.v(foo, 'this isn\'t a string, just kidding')
        return

        pout.v(che['foo'], che['bar'])
        return

        pout.v(che['foo'])
        return

        pout.v('isn\'t, no')
        return

        pout.v(foo, "a) this is a string")
        return

        pout.v("foo bar"); print("foo")
        return


        c = CallString("pout.v('isn\'t, no')")
        pout2.v(c.arg_names())

