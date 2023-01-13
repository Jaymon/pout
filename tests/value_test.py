# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import hmac
import hashlib
import array
import re
from pathlib import Path

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
    GeneratorValue,
    Values,
    Value,
)


class ValuesTest(TestCase):
    def test___init__(self):
        vs = Values()
        self.assertEqual(Value, vs[-1])


class ValueTest(TestCase):
    def test_iterator_object_depth(self):
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

    def test_descriptor(self):
        class Foo(object):
            @property
            def bar(self):
                return 1

        f = Foo()
        v = Value(f)
        s = v.string_value()
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

    def test_dict(self):
        v = Value({})
        self.assertTrue(isinstance(v, DictValue))

    def test_dict_unicode_keys(self):
        """Make sure unicode keys don't mess up dictionaries"""
        d = {"\u00E7": "foo", b'\xc3\xa7 b': "bar"}
        v = Value(d)
        # if no exceptions then test passes
        s = v.string_value()
        sb = v.bytes_value()

    def test_dictproxy(self):
        class FooDictProxy(object): pass
        v = Value(FooDictProxy.__dict__)
        self.assertTrue(isinstance(v, DictProxyValue))
        #s = v.string_value()

    def test_array(self):
        a = array.array("i", range(0, 100))
        v = Value(a)
        s = v.string_value()
        self.assertTrue("array.array('i'" in s)

    def test_list_1(self):
        v = Value([])
        self.assertTrue(isinstance(v, ListValue))
        self.assertEqual("[]", repr(v))

    def test_list_2(self):
        v = Value([
            testdata.get_unicode(),
            testdata.get_unicode(),
        ])

        # if no UnicodeError is raised then this was a success
        repr(v)

    def test_set(self):
        v = Value(set())
        self.assertTrue(isinstance(v, SetValue))

    def test_tuple(self):
        v = Value(tuple([1, 2, 3, 4]))
        self.assertTrue(isinstance(v, TupleValue))
        #s = v.string_value()

    def test_binary(self):
        v = Value(b"")
        self.assertTrue(isinstance(v, BinaryValue))

    def test_binary_2(self):
        d = hmac.new(b"this is the key", b"this is the message", hashlib.md5)
        v = Value(d.digest())
        repr(v)

    def test_string(self):
        v = Value("")
        self.assertTrue(isinstance(v, StringValue))

    def test_object_1(self):
        class FooObject(object):
            bar = 1
            che = "2"

        o = FooObject()
        o.baz = [3]

        v = Value(o)
        s = repr(v)
        self.assertTrue("\n<\n" in s)

        d = {
            "che": o,
            "baz": {"foo": 1, "bar": 2}
        }
        v = Value(d)
        s = repr(v)
        self.assertTrue(f"\n{environ.INDENT_STRING}{environ.INDENT_STRING}<\n" in s)

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
        """in python2 there was an issue with printing lists with unicode, this was
        traced to using Value.__repr__ which was returning a byte string in python2
        which was then being cast to unicode and failing the conversion to ascii"""
        class To3(object):
            pass

        t = To3()
        t.foo = [
            testdata.get_unicode(),
            testdata.get_unicode(),
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

    def test_object_regex_match(self):
        m = re.match(r"(\d)(\d)(\d+)", "0213434")

        with self.assertLogs(logger=pout.stream.logger, level="DEBUG") as c:
            pout.v(m)
        logs = "\n".join(c[1])
        self.assertFalse("READ ERRORS" in logs)

    def test_exception(self):
        v = Value(ValueError("foo bar"))
        self.assertTrue(isinstance(v, ExceptionValue))
        repr(v)

    def test_module(self):
        v = Value(testdata)
        self.assertTrue(isinstance(v, ModuleValue))
        repr(v)

    def test_dict_keys_1(self):
        d = {"foo": 1, "bar": 2}
        v = Value(d.keys())
        self.assertEqual("MAPPING_VIEW", v.typename)
        s = v.string_value()
        self.assertTrue("dict_keys" in s)

    def test_std_collections__pout__(self):
        """https://github.com/Jaymon/pout/issues/61"""
        class PoutDict(dict):
            def __pout__(self):
                return "custom dict"

        d = PoutDict(foo=1, bar=2)
        v = Value(d)
        s = v.string_value()
        self.assertTrue("custom dict" in s)

    def test_dict_keys_bytes(self):
        d = {
            b'foo': b'bar'
        }
        v = Value(d)
        s = v.string_value()
        self.assertTrue("b'foo'" in s)

    def test_object___pout__1(self):
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

    def test_path(self):
        p = Path("/foo/bar/che")
        v = Value(p)
        s = v.string_value()
        self.assertEqual(4, len(s.splitlines(False)))

    def test_callable(self):

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

