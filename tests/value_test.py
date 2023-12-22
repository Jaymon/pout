# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import hmac
import hashlib
import array
import re
from pathlib import Path
import datetime

from . import testdata, TestCase

import pout
from pout import environ
from pout.compat import *
from pout.value import (
    PrimitiveValue,
    DictValue,
    DictProxyValue,
    ListValue,
    SetValue,
    TupleValue,
    BinaryValue,
    StringValue,
    ObjectValue,
    ExceptionValue,
    ModuleValue,
    TypeValue,
    RegexValue,
    RegexMatchValue,
    GeneratorValue,
    CallableValue,
    Values,
    Value,
)


class ValuesTest(TestCase):
    def test___init__(self):
        vs = Values()
        self.assertEqual(Value, vs[-1])


class ValueTest(TestCase):
    def test_primitive_int(self):
        v = Value(100)
        r = v.string_value()
        self.assertTrue("int instance" in r)
        self.assertTrue("100" in r)
        self.assertTrue("<" in r)

    def test_primitive_bool(self):
        v = Value(True)
        r = v.string_value()
        self.assertTrue("bool instance" in r)
        self.assertTrue("True" in r)
        self.assertTrue("<" in r)

    def test_primitive_float(self):
        v = Value(123456.789)
        r = v.string_value()
        self.assertTrue("float instance" in r)
        self.assertTrue("123456.789" in r)
        self.assertTrue("<" in r)

    def test_primitive_none(self):
        v = Value(None)
        r = v.string_value()
        self.assertTrue("NoneType instance" in r)
        self.assertTrue("<" in r)

    def test_object_nested(self):
        class Foo(object):
            pass

        f = Foo()
        f.bar = 1
        f.foo = f

        v = Value(f)
        r = v.string_value()
        self.assertTrue("foo = <" in r, r)
        self.assertTrue("bar = int instance" in r, r)

    def test_object_repeated(self):
        class Foo(object):
            pass

        f = Foo()
        f.bar = 1

        v = Value([f for _ in range(5)])

        r = v.string_value()
        self.assertTrue("0: ValueTest" in r, r)
        self.assertTrue("1: <ValueTest" in r, r)

    def test_iterate_object_depth(self):
        """dicts, lists, etc. should also be subject to OBJECT_DEPTH limits"""
        t = {
            "foo": 1,
            "bar": {
                "che": 2,
                "boo": {
                    "baz": 3,
                    "moo": {
                        "maz": 4,
                    }
                }
            }
        }
        with testdata.modify(environ, OBJECT_DEPTH=1):
            with testdata.capture() as c2:
                pout.v(t)
            self.assertTrue("'bar': <dict" in c2)

    def test_iterate_limit(self):
        """make sure iterators are cutoff when they reach the set limit"""
        with testdata.modify(environ, ITERATE_LIMIT=10):
            t = list(range(0, 100))
            with testdata.capture() as c:
                pout.v(t)
            self.assertTrue("..." in c)

            t = {f"{v}": v for v in range(0, 100)}
            with testdata.capture() as c:
                pout.v(t)
            self.assertTrue("..." in c)

    def test_info(self):
        class Foo(object):
            one = "one"

        class Bar(Foo):
            two = "two"

        v = Value(Bar)
        info_dict = v.info()
        self.assertTrue("one" in info_dict["class_properties"])
        self.assertTrue("two" in info_dict["class_properties"])

        v = Value(Bar())
        info_dict = v.info()
        self.assertTrue("one" in info_dict["class_properties"])
        self.assertTrue("two" in info_dict["class_properties"])

        b = Bar()
        b.two = "three"
        v = Value(b)
        info_dict = v.info()
        r = info_dict["instance_properties"]["two"].body_value()
        self.assertEqual("three", r)

    def test__get_name(self):
        class Foo(object):
            pass

        r = Value(Foo.__new__)._get_name(Foo.__new__)
        self.assertTrue("object.__new__" in r)

        r = Value(Foo)._get_name(Foo)
        self.assertTrue("<locals>.Foo" in r)

        def bar(one, two):
            pass

        r = Value(bar)._get_name(bar)
        self.assertTrue("<locals>.bar" in r)

    def test_descriptor(self):
        class Foo(object):
            @property
            def bar(self):
                return 1

        f = Foo()
        v = Value(f)
        s = v.string_value()
        print(s)
        self.assertTrue("<property instance" in s)

    def test_is_set(self):
        v = set(["foo", "bar", "che"])
        t = Value(v)
        self.assertTrue(SetValue.is_valid(v))
        self.assertEqual("SET", t.typename)

    def test_is_generator(self):
        v = (x for x in range(100))
        t = Value(v)
        self.assertTrue(GeneratorValue.is_valid(v))
        self.assertEqual("GENERATOR", t.typename)

        v = map(str, range(5))
        t = Value(v)
        self.assertTrue(GeneratorValue.is_valid(v))
        self.assertEqual("GENERATOR", t.typename)

    def test_is_binary(self):
        v = memoryview(b'abcefg')
        t = Value(v)
        self.assertTrue(BinaryValue.is_valid(v))
        self.assertEqual("BINARY", t.typename)

        v = bytearray.fromhex('2Ef0 F1f2  ')
        t = Value(v)
        self.assertTrue(BinaryValue.is_valid(v))
        self.assertEqual("BINARY", t.typename)

        v = bytes("foobar", "utf-8")
        t = Value(v)
        self.assertTrue(BinaryValue.is_valid(v))
        self.assertEqual("BINARY", t.typename)

    def test_typename(self):
        class FooTypename(object): pass
        v = FooTypename()
        self.assertEqual('OBJECT', Value(v).typename)
        self.assertEqual('CALLABLE', Value(FooTypename.__init__).typename)

        v = 'foo'
        self.assertEqual('STRING', Value(v).typename)

        v = 123
        self.assertEqual('PRIMITIVE', Value(v).typename)

        v = True
        self.assertEqual('PRIMITIVE', Value(v).typename)

        def baz(): pass
        self.assertEqual('CALLABLE', Value(baz).typename)

        v = TypeError()
        self.assertEqual('EXCEPTION', Value(v).typename)

        v = {}
        self.assertEqual('DICT', Value(v).typename)

        v = []
        self.assertEqual('LIST', Value(v).typename)

        v = ()
        self.assertEqual('TUPLE', Value(v).typename)

        self.assertEqual('MODULE', Value(pout).typename)

        import ast
        self.assertEqual('MODULE', Value(ast).typename)

    def test_instance_callable(self):
        class InsCall(object):
            def __call__(self): pass
            @classmethod
            def cmeth(cls): pass

        instance = InsCall()

        v = Value(instance)
        self.assertEqual('OBJECT', v.typename)

        v = Value(instance.__call__)
        self.assertEqual('CALLABLE', v.typename)

        v = Value(InsCall.cmeth)
        self.assertEqual('CALLABLE', v.typename)

    def test___format__(self):
        """Make sure Value instances handle string format correctly"""
        #s = "C'est <b>full</b> poche, ça !"
        s = "poche, \u00E7a !"
        v = Value(s)
        # if there are no exceptions the test passes
        "{}".format(v)

    def test_primitive(self):
        v = Value(5)
        self.assertTrue(isinstance(v, PrimitiveValue))

    def test_dict_empty(self):
        v = Value({})
        self.assertTrue(isinstance(v, DictValue))

        r = v.string_value()
        self.assertTrue("dict (0) instance at" in r)

    def test_dict_simple(self):
        v = Value({"foo": 1, "bar": 2})
        self.assertTrue(isinstance(v, DictValue))

        r = v.string_value()
        self.assertTrue("dict (2)" in r, r)
        self.assertTrue("'foo': int instance" in r, r)

    def test_dict_unicode_keys(self):
        """Make sure unicode keys don't mess up dictionaries"""
        d = {"\u00E7": "foo", b'\xc3\xa7 b': "bar"}
        v = Value(d)
        # if no exceptions then test passes
        s = v.string_value()

    def test_dict_keys_1(self):
        d = {"foo": 1, "bar": 2}
        v = Value(d.keys())
        self.assertEqual("MAPPING_VIEW", v.typename)
        s = v.string_value()
        self.assertTrue("dict_keys" in s)

    def test_dict_keys_bytes(self):
        d = {
            b'foo': b'bar'
        }
        v = Value(d)
        s = v.string_value()
        self.assertTrue("b'foo'" in s)

    def test_dictproxy(self):
        class FooDictProxy(object): pass
        v = Value(FooDictProxy.__dict__)
        self.assertTrue(isinstance(v, DictProxyValue))

    def test_list_empty(self):
        v = Value([])
        self.assertTrue(isinstance(v, ListValue))

        r = v.string_value()
        self.assertTrue("<list (0) instance at" in r)

    def test_list_2(self):
        v = Value([
            testdata.get_unicode_words(),
            testdata.get_unicode_words(),
        ])

        r = v.string_value()
        self.assertTrue("list (2) instance" in r)

    def test_array(self):
        a = array.array("i", range(0, 10))
        v = Value(a)
        s = v.string_value()
        self.assertTrue("array.array ('i')" in s)

    def test_set(self):
        v = Value(set())
        self.assertTrue(isinstance(v, SetValue))

        s = set(["foo", "bar"])
        v = Value(s)
        r = v.string_value()
        self.assertTrue("set (2) instance" in r)
        self.assertTrue("bar" in r)

    def test_generator(self):
        v = Value(range(10))

        r = v.string_value()
        self.assertTrue("<range (10) generator")

    def test_tuple(self):
        v = Value(tuple([1, 2, 3, 4]))
        self.assertTrue(isinstance(v, TupleValue))

        r = v.string_value()
        self.assertTrue("tuple (4) instance" in r)

    def test_binary_1(self):
        v = Value(b"")
        self.assertTrue(isinstance(v, BinaryValue))

    def test_binary_2(self):
        d = hmac.new(b"this is the key", b"this is the message", hashlib.md5)
        v = Value(d.digest())

        r = v.string_value()
        self.assertTrue(r.startswith("b"))

    def test_string(self):
        v = Value("")
        self.assertTrue(isinstance(v, StringValue))

        r = v.string_value()
        self.assertTrue("<str (0) instance" in r, r)

        v = Value("foo bar")
        r = v.string_value()
        self.assertTrue("str (7) instance" in r, r)
        self.assertTrue("foo bar" in r, r)

    def test_exception(self):
        v = Value(ValueError("foo bar"))
        self.assertTrue(isinstance(v, ExceptionValue))
        repr(v)

    def test_module(self):
        m = testdata.create_module([
            "bar = 1",
            "def foo(one, two): return 3",
            "class Che(object):",
            "    boo = 1",
            "    def bam(self): pass",
        ]).module()
        v = Value(m)
        self.assertTrue(isinstance(v, ModuleValue))

        r = v.string_value()
        self.assertTrue(r.startswith(f"{m.__name__} module at"))

    def test_std_collections__pout__(self):
        """https://github.com/Jaymon/pout/issues/61"""
        class PoutDict(dict):
            def __pout__(self):
                return "custom dict"

        d = PoutDict(foo=1, bar=2)
        v = Value(d)
        s = v.string_value()
        self.assertTrue("custom dict" in s)

    def test_object_1(self):
        class FooObject(object):
            bar = 1
            che = "2"

        o = FooObject()
        o.baz = [3]

        v = Value(o)
        self.assertTrue(isinstance(v, ObjectValue))

        r = v.string_value()
        self.assertRegex(r, r"\n\s+<\n")

        d = {
            "che": o,
            "baz": {"foo": 1, "bar": 2}
        }
        v = Value(d)
        r = v.string_value()
        indent = environ.INDENT_STRING * 3
        self.assertTrue(f"\n{indent}<\n" in r)

    def test_object_2(self):
        class To26(object):
            value = 1
        class To25(object):
            instances = [To26()]
        class To24(object):
            instances = [To25()]
        class To23(object):
            instances = [To24()]
        class To22(object):
            instances = [To23()]
        class To21(object):
            instances = [To22()]
            instance = To22()

        t = To21()
        with testdata.capture() as c1:
            pout.vs(t)

        with testdata.modify(environ, OBJECT_DEPTH=1):
            with testdata.capture() as c2:
                pout.vs(t)

        self.assertNotEqual(str(c1), str(c2))

    def test_object_3(self):
        """in python2 there was an issue with printing lists with unicode, this
        was traced to using Value.__repr__ which was returning a byte string in
        python2 which was then being cast to unicode and failing the conversion
        to ascii"""
        class To3(object):
            pass

        t = To3()
        t.foo = [
            testdata.get_unicode_words(),
            testdata.get_unicode_words(),
        ]

        # no UnicodeError raised is success
        pout.v(t)

    def test_object_4_recursive(self):
        class To4(object):
            def __str__(self):
                return self.render()

            def render(self):
                pout.v(self)
                return self.__class__.__name__

        t = To4()
        pout.v(t)

    def test_object___pout___1(self):
        class OPU(object):
            def __pout__(self):
                return "foo"

        v = Value(OPU())
        s = v.string_value()
        self.assertEqual(4, len(s.splitlines(False)))
        self.assertTrue("foo" in s)

    def test_object___pout___unicode(self):
        s = testdata.get_unicode_words()
        class OPU(object):
            def __pout__(self):
                return {"foo": s}

        o = OPU()
        with testdata.capture() as c:
            pout.v(o)

        self.assertTrue(String(s) in String(c))

    def test_object_str_limit(self):
        class StrLimit(object):
            def __str__(self):
                return testdata.get_words(100)

        s = StrLimit()
        v = Value(s)
        r = v.string_value()
        self.assertTrue("... Truncated " in r)

    def test_type_1(self):
        class Foo(object):
            bar = 1

        v = Value(Foo)
        s = v.string_value()
        self.assertTrue("bar = int instance" in s, s)
        self.assertRegex(s, r"\s1\s", s)

        v = Value(object)
        self.assertTrue(isinstance(v, TypeValue))

        s = v.string_value()
        self.assertRegex(s, r"^<object\sclass\sat\s\dx[^>]+?>$", s)

    def test_regex_match(self):
        m = re.match(r"(\d)(\d)(\d+)", "0213434")
        v = Value(m)
        self.assertTrue(isinstance(v, RegexMatchValue))

        r = v.string_value()
        self.assertTrue("Pattern:" in r)
        self.assertTrue("Group 3" in r)

    def test_regex_compiled(self):
        regex = re.compile(r"^\s([a-z])", flags=re.I)
        v = Value(regex)
        self.assertTrue(isinstance(v, RegexValue))

        r = v.string_value()
        self.assertTrue("re:Pattern instance" in r)
        self.assertTrue("groups:" in r)
        self.assertTrue("flags:" in r)

    def test_callable_1(self):
        class Klass(object):
            def instancemethod(self, *args, **kwargs): pass
            @classmethod
            def clsmethod(cls, *args, **kwargs): pass

        v = Value(Klass.clsmethod)
        s = v.string_value()
        self.assertTrue("<classmethod tests." in s)

        k = Klass()
        v = Value(k.instancemethod)
        s = v.string_value()
        self.assertTrue("<method tests." in s)

        def func(*args, **kwargs): pass

        v = Value(func)
        s = v.string_value()
        self.assertTrue("<function tests." in s)

    def test_callable_2(self):
        v = Value(object.__new__)
        self.assertTrue(isinstance(v, CallableValue))

        r = v.string_value()
        self.assertTrue("staticmethod" in r)

    def test_classmethod(self):
        """in python 3.10 classmethods were being categorized as properties"""
        def foo(cls):
            pass

        func = classmethod(foo)
        v = Value(func)
        self.assertEqual("CALLABLE", v.typename)

        class ToProp(object):
            @classmethod
            def foo(cls):
                pass

        v = Value(ToProp)
        info = v.info(show_methods=True)
        self.assertEqual({}, info["class_properties"])
        self.assertEqual({}, info["instance_properties"])
        self.assertTrue("foo" in info["methods"])

    def test_datetime(self):
        dt = datetime.datetime.now()
        v = Value(dt)
        r = v.string_value()
        self.assertTrue(str(dt) in r)

    def test_path(self):
        p = Path("/foo/bar/che")
        v = Value(p)
        s = v.string_value()
        self.assertEqual(4, len(s.splitlines(False)))
        self.assertTrue("/foo/bar/che" in s)

