# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import time
import hmac
import hashlib
import subprocess
import os
import re
import logging
import json

# this is the local pout that is going to be tested
import pout
from pout.compat import *
from pout.interface import V

from . import testdata, TestCase


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


class CTest(TestCase):
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

    def test_variables(self):
        v = "foo bar"
        with testdata.capture() as c:
            pout.c(v)
        #self.assertTrue("v (7) = " in c)
        self.assertRegex(str(c), r"^\s+v\s+=\s+")


class JTest(TestCase):
    def test_j(self):
        with testdata.capture() as c:
            pout.j('["foo", {"bar":["baz", null, 1.0, 2]}]')
        self.assertTrue("list (2)" in c)

        with testdata.capture() as c:
            s = json.dumps({"foo": 1, "bar": 2})
            pout.j(s)
        self.assertTrue("dict (2)" in c)


class BTest(TestCase):
    def test_variable_1(self):
        s = "foo"
        with testdata.capture() as c:
            pout.b(s)
        self.assertTrue("foo" in c)

        s = b"foo"
        with testdata.capture() as c:
            pout.b(s)
        self.assertTrue("foo" in c)

    def test_variable_2(self):
        """https://github.com/Jaymon/pout/issues/40"""
        i = 5
        with testdata.capture() as c:
            pout.b(i)
            self.assertTrue(" 5 " in c)

        with testdata.capture() as c:
            pout.b(5)
        self.assertEqual(8, len(c.splitlines()))

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


class PTest(TestCase):
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


class XTest(TestCase):
    def test_x(self):
        path = testdata.create_file([
            "import pout",
            "",
            "v = 'xx'",
            "pout.x(v)"
        ])
        #raise unittest.SkipTest("we skip the pout.x tests unless we are working on them")
        #pout.x()
        r = path.run(code=1)
        self.assertTrue("xx" in r)

        path = testdata.create_file([
            "import pout",
            "",
            "pout.x()"
        ])
        r = path.run(code=1)
        self.assertTrue("exit at line " in r)


class SleepTest(TestCase):
    def test_run(self):
        with testdata.capture() as c:
            pout.sleep(0.25)

        self.assertTrue("Done Sleeping" in c)
        self.assertTrue("Sleeping 0.25 seconds" in c)

    def test_sleep(self):
        start = time.time()
        pout.sleep(1.1)
        stop = time.time()
        self.assertLess(1.0, stop - start)


class TTest(TestCase):
    """test the pout.t() method"""
    def get_trace(self):
        pout.t()

    def test_t_1(self):
        with testdata.capture() as c:
            pout.t()
        self.assertTrue("pout.t()" in c)

    def test_t_2_space(self):
        with testdata.capture() as c:
            pout.t ()
        self.assertTrue("pout.t ()" in c)

    def test_t_3_newline(self):
        raise ValueError("I need to make this work")

        pout.t(
            inspect_packages=False,
            depth=0,
        )

        return


        (
            pout.t
            ()
        )

        return


        with testdata.capture() as c:
            pout.t
            ()
        pout.v(str(c))
        self.assertTrue("pout.t\n()" in c)

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


class HTest(TestCase):
    """
    test the pout.h() method
    """
    def test_h(self):
        with testdata.capture() as c:
            pout.h(1)

            pout.h()
        self.assertTrue("here 1" in c)


class STest(TestCase):
    def test_s_return(self):
        v = "foo"
        r = pout.s(v)
        self.assertTrue('v = ' in r)
        self.assertTrue('str (3) instance' in r)
        self.assertTrue('foo' in r)

    def test_ss_return(self):
        v = "foo"
        r = pout.ss(v)
        self.assertTrue('foo' in r)


class RTest(TestCase):
    def test_run(self):
        path = testdata.create_file([
            "# -*- coding: utf-8 -*-",
            "from __future__ import unicode_literals, division, print_function, absolute_import",
            "import pout",
            "",
            "for x in range(10):",
            "    pout.r(x)",
            "",
            "for y in range(5):",
            "    pout.r(y)",
        ])
        c = path.run()
        self.assertTrue("pout.r(x) called 10 times" in c)
        self.assertTrue("pout.r(y) called 5 times" in c)


class VTest(TestCase):
    def test_issue42(self):
        class Foo(object):
            def __init__(self, a, b):
                self.a = a
                self.b = b
                pout.v(self)

        f = Foo(1, 2) # success if no error raised

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
        self.assertTrue('ret = ' in c)
        self.assertTrue('default_val =' in c)
        self.assertTrue('getattr(self.issue_module, k, None) = None' in c)
        self.assertTrue('self.issue_fields.get(k, None) = None')

        del self.issue_module
        del self.issue_fields

    def test_function(self):
        b = Bam()

        with testdata.capture() as c:
            pout.v(b.get_bar)
            self.assertTrue("method" in c)

        with testdata.capture() as c:
            pout.v(b.get_foo)
            self.assertTrue("method" in c)

        with testdata.capture() as c:
            pout.v(baz)
            self.assertTrue("function" in c)

    def test_get_name(self):
        """makes sure if __getattr__ raises other errors than AttributeError
        then pout will still print correctly"""
        class FooGetName(object):
            def __init__(self):
                self.fields = {}
            def __getattr__(self, key):
                # This will raise a KeyError when key doesn't exist
                return self.fields[key]

        with testdata.capture() as c:
            fgn = FooGetName()
            pout.v(fgn)

        for s in ["FooGetName (", "at 0x", "__str__ (", "fields = "]:
            self.assertTrue(s in c, s)

    def test_vs(self):
        with testdata.capture() as c:
            d = {'foo': 1, 'bar': 2}
            pout.vv(d)
        self.assertFalse("d (" in c)
        self.assertTrue("'foo':" in c)
        self.assertTrue("'bar':" in c)

    def test_overriding(self):
        """This verifies that child classes still can find the correct stack
        traces

        https://github.com/Jaymon/pout/issues/8
        """
        original_function = pout.v

        class Child(V):
            @classmethod
            def function_name(cls):
                return "v"

            def name_value(self, name, body, **kwargs):
                return "foo custom"

        Child.inject()

        try:
            with testdata.capture() as c:
                v = "foo"
                pout.v(v)
            self.assertTrue("foo custom" in c)

            with testdata.capture() as c:
                v = "bar"
                pout.v(v)
            self.assertTrue("bar" in c)

        finally:
            pout.v = original_function

    def test_issue_31(self):
        """https://github.com/Jaymon/pout/issues/31"""
        class Issue31String(String):
            def bar(self):
                pout.v("")
                return ""

        with testdata.capture() as c:
            s = Issue31String("foo")
            pout.v(s.bar())

        lines = re.findall(r"\([^:)]+:\d+\)", str(c))
        self.assertEqual(2, len(lines))
        self.assertNotEqual(lines[0], lines[1])

    def test_issue_34(self):
        """https://github.com/Jaymon/pout/issues/34"""
        class FooIssue34(object):
            bar_che = ["one", "two", "three"]

        left = "left"
        right = "right"

        with testdata.capture() as c:
            pout.v(left, " ".join(FooIssue34.bar_che), right)
        self.assertTrue("right" in c)
        self.assertTrue("left" in c)
        self.assertTrue("one two three" in c)

    def test_keys(self):
        d = {'\xef\xbb\xbffoo': ''} 
        d = {'\xef\xbb\xbffo_timestamp': ''}
        pout.v(d)

        d = {0: "foo", 1: "bar"}
        pout.v(d)

    def test_compiled_regex(self):
        regex = re.compile(r"foo", re.I | re.MULTILINE)
        pout.v(regex)

    def test_cursor(self):
        import sqlite3
        path = ":memory:"
        con = sqlite3.connect(path)
        cur = con.cursor()
        pout.v(cur)

    def test_encoding_in_src_file(self):
        path = testdata.create_file([
            "# -*- coding: iso-8859-1 -*-",
            "from __future__ import unicode_literals, division, print_function, absolute_import",
            "import pout",
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
        contents = path.read_text()
        path.write_text(contents, encoding="iso-8859-1")
        #path.encoding = "iso-8859-1"
        #path.replace(contents)

        environ = {
            "PYTHONPATH": os.path.abspath(os.path.expanduser("."))
        }
        output = subprocess.check_output(
            [sys.executable, path],
            env=environ,
            stderr=subprocess.STDOUT,
        )
        self.assertTrue("foo bar" in output.decode("utf-8"))

    def test_unicode_in_src_file(self):
        path = testdata.create_file([
            "# -*- coding: utf-8 -*-",
            "from __future__ import unicode_literals, division, print_function, absolute_import",
            "import pout",
            "",
            "# {}".format(testdata.get_unicode_words()),
            "",
            "pout.v('foo bar')"
        ])

        environ = {
            "PYTHONPATH": os.path.abspath(os.path.expanduser("."))
        }
        output = subprocess.check_output(
            [sys.executable, path],
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

    def test_binary_bytes(self):
        """https://github.com/Jaymon/pout/issues/30"""
        with testdata.capture() as c:
            s = b"foo"
            pout.v(bytes(s))
        self.assertTrue("foo" in c)
        self.assertTrue("b\"" in c)

    def test_binary_1(self):
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

        for s in ["b\"", "abcefg", "foobar", ".\\xf0\\xf1\\xf2"]:
            self.assertTrue(s in c, s)

    def test_binary_unicode_error(self):
        d = hmac.new(b"this is the key", b"this is the message", hashlib.md5)
        with testdata.capture() as c:
            pout.v(d.digest())
        self.assertTrue("d.digest()" in c)
        self.assertTrue(" b\"" in c)
        self.assertFalse("<bytes" in c)

    def test_set(self):
        s = set(["foo", "bar", "che"])
        with testdata.capture() as c:
            pout.v(s)

        for s in ["foo", "che", "bar", "set (3) ", "{", "}"]:
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
        for s in ['__init__', 'args = tuple', 'kwargs = <dict (0) instance']:
            self.assertTrue(s in c, s)

        for s in ['__get__', 'DescExample instance', 'DescExample class']:
            self.assertTrue(s in c, s)

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
        self.assertTrue("1 instance" in c)
        self.assertTrue("m = " in c)

    def test_proxy_dict(self):
        with testdata.capture() as c:
            pout.v(FooBar.__dict__)
        for s in ["FooBar.__dict__", " (2) ", "{"]:
            self.assertTrue(s in c)
        #self.assertTrue("FooBar.__dict__ (2) = dict_proxy({" in c)

    def test_multiline_comma(self):
        # https://github.com/Jaymon/pout/issues/12
        with testdata.capture() as c:
            pout.v(
                "foo",
                "bar",
                "che",
            )
        #self.assertRegex(String(c), re.compile(r'"foo"\s+"bar"\s+"che"', re.M))
        #self.assertTrue('"foo"\n\n"bar"\n\n"che"' in c)
        self.assertTrue("foo" in c)
        self.assertTrue("bar" in c)
        self.assertTrue("che" in c)

    def test_type(self):
        with testdata.capture() as c:
            pout.v(type(100))

        pout.v(str(c))
        self.assertTrue("type(100) =" in c)
        self.assertTrue("int class" in c)

        with testdata.capture() as c:
            pout.v(type([]))
        self.assertTrue("type([]) =" in c)
        self.assertTrue("<list class" in c)

    def test_str(self):
        '''
        since -- 3-28-2013
        '''
        s_unicode = "this is a unicode string"
        s_byte = b"this is a byte string"
        with testdata.capture() as c:
            pout.v(s_unicode)
            pout.v(s_byte)
        self.assertTrue("this is a byte string" in c.stderr)
        self.assertTrue("this is a unicode string" in c.stderr)

        s_unicode = ""
        s_byte = b""
        with testdata.capture() as c:
            pout.v(s_unicode)
            pout.v(s_byte)
        self.assertTrue("bytes (0)" in c.stderr)
        self.assertTrue('str (0)' in c.stderr)

        #print(c.stderr.read())

#         d = {
#             'foo': "foo is a unicode str",
#             'bar': b"bar is a byte string"
#         }
#         with testdata.capture() as c:
#             pout.v(d)
#         self.assertTrue('\'foo\': "foo is a unicode str"' in c.stderr)
#         self.assertTrue("'bar': b'bar is a byte string'" in c.stderr)

    def test_sys_module(self):
        '''
        built-in modules fail, which they shouldn't

        since -- 7-19-12
        '''
        with testdata.capture() as c:
            pout.v(sys)

        for s in ["sys = sys module", "Functions:", "Classes:"]:
            self.assertTrue(s in c, "[{}] is not present".format(s))

    def test_multiline_call(self):

        foo = 1
        bar = 2

        from pout import v as voom

        with testdata.capture() as c:
            voom(
                foo,bar
            )
        self.assertRegex(String(c), re.compile(r"foo\s+=\s+", re.M))
        self.assertRegex(String(c), re.compile(r"bar\s+=\s+", re.M))

        with testdata.capture() as c:
            pout.v(
                foo,
                bar,
                "this is a string"
            )
        self.assertTrue("foo = " in c)
        self.assertTrue("bar = " in c)
        self.assertTrue("str (16) instance" in c)

        from pout import v

        with testdata.capture() as c:
            v(
                foo,
                bar)
        self.assertRegex(String(c), re.compile(r"foo\s+=\s+", re.M))
        self.assertRegex(String(c), re.compile(r"bar\s+=\s+", re.M))

        with testdata.capture() as c:
            v(
                foo, bar)
        self.assertRegex(String(c), re.compile(r"foo\s+=\s+", re.M))
        self.assertRegex(String(c), re.compile(r"bar\s+=\s+", re.M))

        with testdata.capture() as c:
            v(
                foo,

                bar

            )
        self.assertRegex(String(c), re.compile(r"foo\s+=\s+", re.M))
        self.assertRegex(String(c), re.compile(r"bar\s+=\s+", re.M))

        def func(a, b):
            return a + b

        with testdata.capture() as c:
            v(
                func(1, 4)
            )
        self.assertTrue("func(1, 4) = " in c)

        with testdata.capture() as c:
            v(
                func(
                    5,
                    5
                )
            )
        self.assertRegex(String(c), "\s10\s")

        import pout as poom
        with testdata.capture() as c:
            poom.v(foo)
        self.assertTrue("foo = " in c)

    def test_object_1(self):
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

    def test_object___pout___method(self):
        class PoutFoo(object):
            bar = "bar"
            def __pout__(self):
                return {
                    "bar": "pout bar"
                }

        instance = PoutFoo()
        with testdata.capture() as c:
            pout.v(instance)
            self.assertTrue("pout bar" in c)

    def test_exception(self):
        try:
            f = Foo()
            f.raise_error()

        except Exception as e:
            pout.v(e)

    def test_object_instance_str_method(self):
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

    def test_range_iterator(self):
        #p = pout.Pout()
        #print(p._get_type(range(5)))
        with testdata.capture() as c:
            pout.v(range(5))
        for s in ["range(5)", "range (5)"]:
            self.assertTrue(s in c, s)

    def test_not_in_val(self):
        with testdata.capture() as c:
            sentinal = "foo"
            val = "foobar"
            pout.v(sentinal not in val)
        self.assertTrue("sentinal not in val" in c)

    def test_really_long_list(self):
        raise self.skip_test("This takes about 14 seconds to run")

        v = [testdata.get_words(1) for x in range(260818)]
        pout.v(v)


class MTest(TestCase):
    def test_m(self):
        pout.m() # around 11
        l = list(range(1, 1000000))
        pout.m("after big list creation") # around 43


class ITest(TestCase):
    def test_class_info(self):
        """I noticed when passing classes into pout.i() they identified as
        instances in the output, this makes sense now that I've looked into it,
        but I went ahead and fixed it"""
        class Foo(object): pass

        with testdata.capture() as c:
            pout.i(Foo)
        self.assertTrue("Foo class at" in c)

        with testdata.capture() as c:
            pout.i(dict)
        self.assertTrue("dict class at" in c)

        d = {}
        with testdata.capture() as c:
            pout.i(d)
        self.assertTrue("dict (0) instance at" in c)

        f = Foo()
        with testdata.capture() as c:
            pout.i(f)
        self.assertTrue("Foo instance at" in c)

    def test_map(self):
        with testdata.capture() as c:
            v = map(str, range(5))
            pout.i(v)

        for s in ["Methods (", "Instance Properties ("]:
            self.assertTrue(s in c, s)

    def test_object(self):
        bar = 1
        with testdata.capture() as c:
            pout.i(bar)
        for s in ["<method"]:
            self.assertTrue(s in c, s)

        class Foo(object):
            p = 1
            o = 2
            n = 3
            m = 4
            def z(self): pass
            def y(self): pass
            def x(self): pass
            def c(self): pass
            def b(self): pass
            def a(self): pass

        instance = Foo()
        instance.k = 5
        instance.j = 6

        with testdata.capture() as c:
            pout.i(instance)
            self.assertRegex(
                str(c),
                re.compile(r"a\(.*b\(.*c\(.*x\(.*y\(", re.S)
            )


class LTest(TestCase):
    def test_l(self):
        tl = logging.getLogger("LTest")
        tl.setLevel(logging.ERROR)

        tl.debug("This should not print 1")

        with pout.l():
            tl.debug("This should print 1/3")

        tl.debug("This should not print 2")

        with pout.l("LTest"):
            tl.debug("This should print 2/3")

        tl.debug("This should not print 3")

        with pout.l("LTest", logging.INFO):
            tl.debug("This should not print 4")

        tl.debug("This should not print 5")

        with pout.l("LTest", "debug"):
            tl.debug("This should print 3/3")

        tl.debug("This should not print 6")



class ETest(TestCase):
    def test_e(self):
        with self.assertRaises(ValueError):
            with pout.e():
                raise ValueError("foo")


class ToFileTest(TestCase):
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

