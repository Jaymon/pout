# -*- coding: utf-8 -*-
"""
test pout

right now this doesn't do much more than just print out pout statements, but someday I will
go through and add assert statements

link -- http://docs.python.org/library/unittest.html

to run on the command line:
python -m unittest test_pout[.ClassTest[.test_method]]
"""
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import time
import unittest
from unittest import TestCase
import hmac
import hashlib
import subprocess
import os

import testdata

# remove any global pout (this is to overcome me putting pout in sites.py
if 'pout' in sys.modules:
    sys.modules['pout2'] = sys.modules['pout']
    del sys.modules['pout']

    # allow the global pout to be used as pout2 without importing
    try:
        if sys.version_info[0] < 3:
            import __builtin__ as builtins
        else:
            import builtins

        if hasattr(builtins, "pout"):
            del builtins.pout
        builtins.pout2 = sys.modules['pout2']

    except ImportError as e:
        pass

# this is the local pout that is going to be tested
import pout
from pout.compat import queue, range, is_py2
from pout import Inspect


class Foo(object):
    bax=4
    def __init__(self):
        self.bar = 1
        self.che = 2
        self.baz = 3

    def raise_error(self):
        e = IndexError("foo")
        raise e


class Bar(object):

    f = Foo()

    def __init__(self):
        self.foo = 1
        self.che = 2
        self.baz = 3

    def __str__(self):
        return u"Bar"


class FooBar(Foo, Bar):
    pass


class Foo2(Foo):
    pass


class Foo3(Foo2):
    pass


class Che(object):

    f = Foo()
    b = Bar()

    def __getattr__(self, key):
        return super(Che, self).__getattr__(key)

    def __str__(self):
        return u"Che"


class Bax():
    '''
    old school defined class that doesn't inherit from object
    '''
    pass


def baz():
    pass


class Bam(object):
    baz = "baz class property"
    che = "che class property"

    @property
    def bax(self):
        return "bax property"

    @classmethod
    def get_foo(cls):
        return "get_foo instance method"

    def __init__(self):
        self.baz = "baz instance property"

    def get_bar(self):
        return "get_bar instance method"


class PoutTest(unittest.TestCase):
    """any non-specific function testing should go here"""
    def test_overriding(self):
        """This verifies that child classes still can find the correct stack traces

        https://github.com/Jaymon/pout/issues/8
        """
        original_class = pout.pout_class
        class Child(pout.Pout):
            def v(self, *args, **kwargs):
                if args[0] == "foo":
                    call_info = self._get_arg_info(args)
                    self._print(["foo custom "], call_info)

                else:
                    return super(Child, self).v(*args, **kwargs)

        pout.pout_class = Child

        with testdata.capture() as c:
            v = "foo"
            pout.v(v)
        self.assertTrue("foo custom" in c)

        with testdata.capture() as c:
            v = "bar"
            pout.v(v)
        self.assertTrue('"bar"' in c)

        pout.pout_class = original_class

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

    def test__get_name(self):
        """makes sure if __getattr__ raises other errors than AttributeError then
        pout will still print correctly"""
        class FooGetName(object):
            def __init__(self):
                self.fields = {}
            def __getattr__(self, key):
                # This will raise a KeyError when key doesn't exist
                return self.fields[key]

        with testdata.capture() as c:
            fgn = FooGetName()
            pout.v(fgn)
        for s in ["pout_test.FooGetName", "id:", "path:", "Ancestry:", "__str__:", "fields = "]:
            self.assertTrue(s in c, s)

    def test__get_arg_names(self):
        """see also VTest.test_multi_args() and VTest.test_multiline_comma()"""

        p = pout.Pout()

        r = p._get_arg_names("\n".join([
            "        pout.v(",
            '            "foo",',
            '            "bar",',
            '            "che",',
            '        )'
        ]))
        self.assertEqual(3, len(r[0]))
        for x in range(3):
            self.assertEqual("", r[0][x])
        self.assertEqual(True, r[1])

        r = p._get_arg_names("\n".join([
            "        pout.v(",
            '"foo",',
            '"bar",',
            '"che"'
        ]))
        self.assertEqual(3, len(r[0]))
        for x in range(3):
            self.assertEqual("", r[0][x])
        self.assertEqual(False, r[1])

        r = p._get_arg_names("        pout.v(\"this string has 'mixed quotes\\\"\")")
        self.assertEqual(1, len(r[0]))
        self.assertEqual("", r[0][0])

        r = p._get_arg_names(" pout.v(name); hasattr(self, name)")
        self.assertEqual("name", r[0][0])
        self.assertEqual(1, len(r[0]))

        r = p._get_arg_names("\n".join([
            "        pout.v(",
            '"foo",',
            '"bar",',
            '"che",'
        ]))
        for x in range(3):
            self.assertEqual("", r[0][x])
        self.assertEqual(False, r[1])

        r = p._get_arg_names("pout.v(foo, [bar, che])")
        self.assertEqual("foo", r[0][0])
        self.assertEqual("[bar, che]", r[0][1])

        r = p._get_arg_names("pout.v(foo, bar)")
        self.assertEqual("foo", r[0][0])
        self.assertEqual("bar", r[0][1])

        r = p._get_arg_names("pout.v(foo)")
        self.assertEqual("foo", r[0][0])

        r = p._get_arg_names("pout.v('foo')")
        self.assertEqual("", r[0][0])

        r = p._get_arg_names('pout.v("foo")')
        self.assertEqual("", r[0][0])

        r = p._get_arg_names("pout.v('foo\'bar')")
        self.assertEqual("", r[0][0])

        r = p._get_arg_names("pout.v('foo, bar, che')")
        self.assertEqual("", r[0][0])

        r = p._get_arg_names("pout.v((foo, bar, che))")
        self.assertEqual("(foo, bar, che)", r[0][0])

        r = p._get_arg_names("pout.v((foo, (bar, che)))")
        self.assertEqual("(foo, (bar, che))", r[0][0])

        r = p._get_arg_names("pout.v([foo, bar, che])")
        self.assertEqual("[foo, bar, che]", r[0][0])

        r = p._get_arg_names("pout.v([foo, [bar, che]])")
        self.assertEqual("[foo, [bar, che]]", r[0][0])

        r = p._get_arg_names("pout.v([[foo], [bar, che]])")
        self.assertEqual("[[foo], [bar, che]]", r[0][0])

    def test_find_call_depth(self):
        s = "foo"
        class PoutChild(pout.Pout):
            def v(self, *args):
                self._printstr("PoutChild")
                super(PoutChild, self).v(*args)

        pout.pout_class = PoutChild
        with testdata.capture() as c:
            pout.v(s)
        self.assertTrue('s (3) = "foo"' in c)
        pout.pout_class = pout.Pout

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

    def test_unicode_error(self):
        d = hmac.new(b"this is the key", b"this is the message", hashlib.md5)
        with testdata.capture() as c:
            pout.v(d.digest())
        self.assertTrue("d.digest()" in c)
        self.assertTrue(" b'" in c)

    def test_ipython_fail(self):
        '''
        ipython would fail because the source file couldn't be read

        since -- 7-19-12
        '''
        mp_orig = pout.Pout._get_call_info

        def _get_call_info_fake(self, frame_tuple, called_module='', called_func=''):
            call_info = {}
            call_info['frame'] = frame_tuple
            call_info['line'] = frame_tuple[2]
            call_info['file'] = '/fake/file/path'
            call_info['call'] = ''
            call_info['arg_names'] = []
            return call_info

        # monkey patch to do get what would be returned in an iPython shell
        pout.Pout._get_call_info = _get_call_info_fake

        # this should print out
        with testdata.capture() as c:
            pout.v(list(range(5)))
        self.assertTrue("Unknown 0 (5)" in c)
        self.assertTrue("0: 0," in c)
        self.assertTrue("4: 4" in c)

        pout.Pout._get_call_info = mp_orig

    def test_get_type(self):

        p = pout.Pout()

        v = 'foo'
        self.assertEqual('STRING', p._get_type(v))

        v = 123
        self.assertEqual('DEFAULT', p._get_type(v))

        v = True
        self.assertEqual('DEFAULT', p._get_type(v))

        v = Foo()
        self.assertEqual('OBJECT', p._get_type(v))
        #import types
        #print dir(Foo.__init__)
        #print "{}".format(isinstance(Foo.__init__, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)))
        self.assertEqual('FUNCTION', p._get_type(Foo.__init__))

        self.assertEqual('FUNCTION', p._get_type(baz))

        v = TypeError()
        self.assertEqual('EXCEPTION', p._get_type(v))

        v = {}
        self.assertEqual('DICT', p._get_type(v))

        v = []
        self.assertEqual('LIST', p._get_type(v))

        v = ()
        self.assertEqual('TUPLE', p._get_type(v))

        self.assertEqual('MODULE', p._get_type(pout))

        import ast
        self.assertEqual('MODULE', p._get_type(ast))

        #self.assertEqual('CLASS', pout._get_type(self.__class__))

class CTest(unittest.TestCase):
    def test_c(self):
        with testdata.capture() as c:
            pout.c('this is the input')
        self.assertTrue("Total Characters: 17" in c)

        with testdata.capture() as c:
            pout.c('\u304f')
        self.assertTrue("Total Characters: 1" in c)

        with testdata.capture() as c:
            pout.c('just\r\ntesting')
        self.assertTrue("Total Characters: 13" in c)

        with testdata.capture() as c:
            pout.c('just', u'testing')
        self.assertTrue("Total Characters: 4" in c)
        self.assertTrue("Total Characters: 7" in c)

        # !!! py2 thinks it is 2 chars
        with testdata.capture() as c:
            pout.c('\U00020731')
        self.assertTrue("Total Characters:" in c)

class BTest(unittest.TestCase):
    def test_b(self):
        with testdata.capture() as c:
            pout.b()
        self.assertTrue("*" in c)

        with testdata.capture() as c:
            pout.b(5)
        self.assertTrue("*" in c)

        with testdata.capture() as c:
            pout.b('this is the title')
        self.assertTrue("* this is the title *" in c)

        with testdata.capture() as c:
            pout.b('this is the title 2', 5)
        self.assertTrue("* this is the title 2 *" in c)

        with testdata.capture() as c:
            pout.b('this is the title 3', 3, '=')
        self.assertTrue("= this is the title 3 =" in c)


class PTest(unittest.TestCase):
    def test_p_one_level(self):
        with testdata.capture() as c:
            pout.p('foo')
            time.sleep(.25)
            pout.p()
        self.assertTrue("foo - " in c)

    def test_p_multi_levels(self):
        with testdata.capture() as c:
            pout.p('multi foo')
            pout.p(u'multi bar')
            time.sleep(0.25)
            pout.p()
            time.sleep(0.25)
            pout.p()
        self.assertTrue("multi foo > multi bar" in c)
        self.assertTrue("multi foo -" in c)

    def test_p_with(self):
        with testdata.capture() as c:
            with pout.p("with foo"):
                time.sleep(0.25)
        self.assertTrue("with foo -" in c)


class XTest(unittest.TestCase):
    def test_x(self):
        raise unittest.SkipTest("we skip the pout.x tests unless we are working on them")
        pout.x()

class TTest(unittest.TestCase):
    """test the pout.t() method"""
    def get_trace(self):
        pout.t()

    def test_t(self):
        with testdata.capture() as c:
            pout.t()
        self.assertTrue("pout.t()" in c)

    def test_t_with_assign(self):
        '''
        there was a problem where the functions to parse the call would fail
        when one of the inputs was a dict key assignment, this test makes sure that
        is fixed

        since -- 10-8-12 -- Jay
        '''
        with testdata.capture() as c:
            r = {}
            r['foo'] = self.get_trace()
        self.assertTrue("get_trace()" in c)
        self.assertTrue("pout.t()" in c)


class HTest(unittest.TestCase):
    """
    test the pout.h() method
    """
    def test_h(self):
        with testdata.capture() as c:
            pout.h(1)

            pout.h()
        self.assertTrue("here 1" in c)


class VVTest(unittest.TestCase):
    def test_vv(self):
        with testdata.capture() as c:
            d = {'foo': 1, 'bar': 2}
            pout.vv(d)
        self.assertFalse("d (" in c)
        self.assertTrue("'foo':" in c)
        self.assertTrue("'bar':" in c)


class VTest(unittest.TestCase):
    def test_cursor(self):
        import sqlite3
        path = ":memory:"
        con = sqlite3.connect(path)
        cur = con.cursor()
        pout.v(cur)

    def test_encoding_in_src_file(self):
        path = testdata.create_file("foobar.py", [
            "# -*- coding: iso-8859-1 -*-",
            "from __future__ import unicode_literals, division, print_function, absolute_import",
            "",
            "# \u0087\u00EB",
            "# Här",
            "",
            "try:",
            "    pout.v('foo bar')",
            "except Exception as e:",
            "    print(e)",
        ])

        # convert encoding to ISO-8859-1 from UTF-8, this is convoluted because
        # I usually never have to do this
        contents = path.contents()
        path.encoding = "iso-8859-1"
        path.write(contents)

        environ = {
            "PYTHONPATH": os.path.abspath(os.path.expanduser("."))
        }
        output = subprocess.check_output(
            ["python", path],
            env=environ,
            stderr=subprocess.STDOUT,
        )
        self.assertTrue("foo bar" in output.decode("utf-8"))

    def test_unicode_in_src_file(self):
        path = testdata.create_file("foobar.py", [
            "# -*- coding: utf-8 -*-",
            "from __future__ import unicode_literals, division, print_function, absolute_import",
            "",
            "# {}".format(testdata.get_unicode_words()),
            "",
            "pout.v('foo bar')"
        ])

        environ = {
            "PYTHONPATH": os.path.abspath(os.path.expanduser("."))
        }
        output = subprocess.check_output(
            ["python", path],
            env=environ,
            stderr=subprocess.STDOUT,
        )
        self.assertTrue("foo bar" in output.decode("utf-8"))

    def test_depth(self):
        t = ()
        for x in [8, 7, 6, 5, 4, 3, 2, 1]:
            t = (x, t)

        pout.v(t)

    def test_map(self):
        v = map(str, range(5))
        pout.v(v)

    def test_binary(self):
        with testdata.capture() as c:
            v = memoryview(b'abcefg')
            pout.v(v)

            v = bytearray.fromhex('2Ef0 F1f2  ')
            pout.v(v)

            if is_py2:
                v = bytes("foobar")
            else:
                v = bytes("foobar", "utf-8")
            pout.v(v)

        if is_py2:
            # memoryview just gives a reference in py2
            # bytearray is also different but I don't care enough to fix it
            for s in ["b'foobar'", "b'....'"]:
                self.assertTrue(s in c, s)
        else:
            for s in ["b'abcefg'", "b'foobar'", "b'.\\xf0\\xf1\\xf2'"]:
                self.assertTrue(s in c, s)

    def test_set(self):
        s = set(["foo", "bar", "che"])
        with testdata.capture() as c:
            pout.v(s)

        for s in ['"foo"', '"che"', '"bar"', "s (3) =", "{", "}"]:
            self.assertTrue(s in c, s)

    def test_descriptor_error(self):
        """ https://github.com/Jaymon/pout/issues/18 """
        class Desc(object):
            def __init__(self, *args, **kwargs):
                pout.v("__init__", args, kwargs)
                self.func = args[0]

            def __get__(self, instance, klass):
                pout.v("__get__", instance, klass)
                def wrapped(*args, **kwargs):
                    return self.func(instance, *args, **kwargs)
                return wrapped

        with testdata.capture() as c:
            class DescExample(object):
                @Desc
                def foo(self): pass

            e = DescExample()
            e.foo()
        for s in ['"__init__"', 'args (1) =', 'kwargs (0) = ']:
            self.assertTrue(s in c, s)
        for s in ['"__get__"', 'instance = pout_test.DescExample instance', 'klass = <']:
            self.assertTrue(s in c, s)

    def test_class_vars(self):

        class VarParent(object):
            foo = 1

        class VarChild(VarParent):
            foo = 2
            def __init__(self):
                pout.v(self)

        with testdata.capture() as c:
            vc = VarChild()
        self.assertTrue("foo = 2" in c)

    def test_misclassified_instance(self):
        """objects that have a __getattr__ method that always return something get
        misclassified as dict proxies, this makes sure that is fixed"""

        def misclass_func():
            return 2

        class Misclass(object):
            def __getattr__(self, k):
                return 1

        with testdata.capture() as c:
            m = Misclass()
            pout.v(m)
        self.assertTrue("m = pout_test.1 instance" in c)

    def test_proxy_dict(self):
        with testdata.capture() as c:
            pout.v(FooBar.__dict__)
        self.assertTrue("FooBar.__dict__ (2) = dict_proxy({" in c)

    def test_multiline_comma(self):
        # https://github.com/Jaymon/pout/issues/12
        with testdata.capture() as c:
            pout.v(
                "foo",
                "bar",
                "che",
            )
        self.assertTrue('"foo"\n\n"bar"\n\n"che"' in c)

    def test_type(self):
        with testdata.capture() as c:
            pout.v(type(100))
        self.assertTrue("type(100) =" in c)
        self.assertTrue("'int'" in c)

        with testdata.capture() as c:
            pout.v(type([]))
        self.assertTrue("type([]) =" in c)
        self.assertTrue("'list'" in c)

    def test_str(self):
        '''
        since -- 3-28-2013
        '''
        s_unicode = "this is a unicode string"
        s_byte = b"this is a byte string"
        with testdata.capture() as c:
            pout.v(s_unicode)
            pout.v(s_byte)
        self.assertTrue("b'this is a byte string'" in c.stderr)
        self.assertTrue('"this is a unicode string"' in c.stderr)

        s_unicode = ""
        s_byte = b""
        with testdata.capture() as c:
            pout.v(s_unicode)
            pout.v(s_byte)
        self.assertTrue("b''" in c.stderr)
        self.assertTrue('""' in c.stderr)

        #print(c.stderr.read())

        d = {
            'foo': "foo is a unicode str",
            'bar': b"bar is a byte string"
        }
        with testdata.capture() as c:
            pout.v(d)
        self.assertTrue('\'foo\': "foo is a unicode str"' in c.stderr)
        self.assertTrue("'bar': b'bar is a byte string'" in c.stderr)

    def test_sys_module(self):
        '''
        built-in modules fail, which they shouldn't

        since -- 7-19-12
        '''
        with testdata.capture() as c:
            pout.v(sys)
        for s in ["sys = sys module", "Functions:", "Classes:"]:
            self.assertTrue(s in c)

    def test_multiline_call(self):

        foo = 1
        bar = 2

        from pout import v as voom

        with testdata.capture() as c:
            voom(
                foo,bar
            )
        self.assertTrue("foo = 1\n\nbar = 2" in c)

        with testdata.capture() as c:
            pout.v(
                foo,
                bar,
                "this is a string"
            )
        self.assertTrue("foo = 1\n\nbar = 2\n\n\"this is a string\"" in c)

        from pout import v

        with testdata.capture() as c:
            v(
                foo,
                bar)
        self.assertTrue("foo = 1\n\nbar = 2" in c)

        with testdata.capture() as c:
            v(
                foo, bar)
        self.assertTrue("foo = 1\n\nbar = 2" in c)

        with testdata.capture() as c:
            v(
                foo,

                bar

            )
        self.assertTrue("foo = 1\n\nbar = 2" in c)

        def func(a, b):
            return a + b

        with testdata.capture() as c:
            v(
                func(1, 4)
            )
        self.assertTrue("func(1, 4) = 5" in c)

        with testdata.capture() as c:
            v(
                func(
                    5,
                    5
                )
            )
        self.assertTrue("= 10" in c)

        import pout as poom
        with testdata.capture() as c:
            poom.v(foo)
        self.assertTrue("foo = 1" in c)

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


        pout.v("this string has 'mixed quotes\"")
        pout.v('this string has \'mixed quotes"')
        pout.v('this string has \'single quotes\' and "double quotes"')
        pout.v(foo, 'this isn\'t a string, just kidding')
        pout.v('this string is formatted {} {}'.format(foo, bar))
        pout.v('this string' + " is added together")
        pout.v(func('this string', " has 'single quotes'"))
        pout.v('this string has \'single quotes\'')
        pout.v("this string has \"quotes\"")
        pout.v(che['foo'], che['bar'])
        pout.v(foo, "this isn't a string, just kidding")
        pout.v(foo, "(a) this is a string")

        pout.v(foo, "(a this is a string")
        pout.v(foo, "a) this is a string")  
        pout.v(foo, "this is a, string")
        pout.v(foo, "this is a simple string")

        pout.v(foo, bar, func(1, 2))

    def test_module(self):
        pout.v(pout)
        pout.v(sys.modules[__name__])

    def test_object(self):
        f = Foo()
        pout.v(f)

        c = Che()
        pout.v(c)

    def test_object_2(self):
        b = Bam()
        pout.v(b)

    def test_object_ancestry(self):
        f = Foo3()
        pout.v(f)


    def test_object_pout_method(self):
        class PoutFoo(object):
            bar = "bar"
            def __pout__(self):
                return {
                    "bar": "pout bar"
                }

        instance = PoutFoo()
        pout.v(instance)

    def test_exception(self):
        try:
            f = Foo()
            f.raise_error()

        except Exception as e:
            pout.v(e)

    def test_instance_str_method(self):

        b = Bar()
        pout.v(b)

    def test_one_arg(self):

        foo = [
            [
                [1, 2, 3],
            ],
            [
                [5, 6, 7],
            ],
        ]

        #foo = [range(1, 3) for x in (range(1, 2) for x in range(1))]
        pout.v(foo)


        foo = 1
        bar = 2
        pout.v(foo)

        pout.v(foo, bar)

        foo = "this is a string"
        pout.v(foo)

        foo = True
        pout.v(foo)

        foo = []
        pout.v(foo)

        foo = list(range(1, 10))
        pout.v(foo)

        foo = [list(range(1, 10)) for x in list(range(2))]
        pout.v(foo)

        foo = {}
        pout.v(foo)

        foo = {'foo': 1}
        pout.v(foo)

        #pout._get_arg_info([foo])

    def test_queue(self):
        """Queue.Queue was failing, let's fix that"""
        pout.v(queue.Queue)

    def test_precision(self):
        """float precision was cutting off at 2 decimal places"""

        with testdata.capture() as c:
            f = 1380142261.454746
            pout.v(f)
        self.assertTrue(str(f) in c)

        with testdata.capture() as c:
            i = 1232432435
            pout.v(i)
        self.assertTrue(str(i) in c)

        with testdata.capture() as c:
            b = True
            pout.v(b)
        self.assertTrue("b = True" in c)

    def test_range_iterator(self):
        #p = pout.Pout()
        #print(p._get_type(range(5)))
        with testdata.capture() as c:
            pout.v(range(5))
        self.assertTrue("range(5) (5) = " in c)

    def test_not_in_val(self):
        with testdata.capture() as c:
            sentinal = "foo"
            val = "foobar"
            pout.v(sentinal not in val)
        self.assertTrue("sentinal not in val" in c)

    def test_really_long_list(self):
        raise unittest.SkipTest("This takes about 14 seconds to run")

        v = [testdata.get_words(1) for x in range(260818)]
        pout.v(v)

    def test_sleep(self):
        start = time.time()
        pout.sleep(1.1)
        stop = time.time()
        self.assertLess(1.0, stop - start)

class MTest(TestCase):
    def test_m(self):
        pout.m() # around 11
        l = list(range(1, 1000000))
        pout.m("after big list creation") # around 43


class ITest(TestCase):
    def test_i(self):
        with testdata.capture() as c:
            v = map(str, range(5))
            pout.i(v)

        for s in ["MEMBERS:", "Methods:", "Params:"]:
            self.assertTrue(s in c, s)


class InspectTest(TestCase):
    def test_is_set(self):
        v = set(["foo", "bar", "che"])
        t = Inspect(v)
        self.assertTrue(t.is_set())
        self.assertEqual("SET", t.typename)

    def test_is_generator(self):
        v = (x for x in range(100))
        t = Inspect(v)
        self.assertEqual("GENERATOR", t.typename)

        v = map(str, range(5))
        t = Inspect(v)
        if is_py2:
            self.assertEqual("LIST", t.typename)
        else:
            self.assertEqual("GENERATOR", t.typename)

    def test_is_binary(self):
        v = memoryview(b'abcefg')
        t = Inspect(v)
        self.assertEqual("BINARY", t.typename)

        v = bytearray.fromhex('2Ef0 F1f2  ')
        t = Inspect(v)
        self.assertEqual("BINARY", t.typename)

        if is_py2:
            v = bytes("foobar")
        else:
            v = bytes("foobar", "utf-8")
        t = Inspect(v)
        self.assertEqual("BINARY", t.typename)


if __name__ == '__main__':
    unittest.main()

