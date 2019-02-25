# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import hmac
import hashlib
import array

from . import testdata, TestCase

import pout
from pout import environ
from pout.compat import range, is_py2
from pout.value import Inspect, Value
from pout.value import (
    DefaultValue,
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
    RegexValue
)


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

    def test_typename(self):
        class FooTypename(object): pass
        v = FooTypename()
        self.assertEqual('OBJECT', Inspect(v).typename)
        #import types
        #print dir(Foo.__init__)
        #print "{}".format(isinstance(Foo.__init__, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)))
        self.assertEqual('FUNCTION', Inspect(FooTypename.__init__).typename)

        v = 'foo'
        self.assertEqual('STRING', Inspect(v).typename)

        v = 123
        self.assertEqual('DEFAULT', Inspect(v).typename)

        v = True
        self.assertEqual('DEFAULT', Inspect(v).typename)

        def baz(): pass
        self.assertEqual('FUNCTION', Inspect(baz).typename)

        v = TypeError()
        self.assertEqual('EXCEPTION', Inspect(v).typename)

        v = {}
        self.assertEqual('DICT', Inspect(v).typename)

        v = []
        self.assertEqual('LIST', Inspect(v).typename)

        v = ()
        self.assertEqual('TUPLE', Inspect(v).typename)

        self.assertEqual('MODULE', Inspect(pout).typename)

        import ast
        self.assertEqual('MODULE', Inspect(ast).typename)

        #self.assertEqual('CLASS', pout._get_type(self.__class__))

    def test_instance_callable(self):
        class InsCall(object):
            def __call__(self): pass
            @classmethod
            def cmeth(cls): pass

        instance = InsCall()

        v = Inspect(instance)
#         import sys
#         pout2.v(dir(instance))
#         pout2.v(dir(instance.__call__))
#         pout2.v(dir(sys.exit))
        self.assertEqual('OBJECT', v.typename)

        v = Inspect(instance.__call__)
        self.assertEqual('FUNCTION', v.typename)

        v = Inspect(InsCall.cmeth)
        self.assertEqual('FUNCTION', v.typename)

#     def test_bs4(self):
#         from bs4 import BeautifulSoup
#         soup = BeautifulSoup("<p>blah</p>", "html.parser")
#         pout2.v(soup)
#         #pout.v(soup)

class ValueTest(TestCase):
    def test___format__(self):
        """Make sure Value instances handle string format correctly"""
        #s = "C'est <b>full</b> poche, ça !"
        s = "poche, \u00E7a !"
        v = Value(s)
        # if there are no exceptions the test passes
        "{}".format(v)
        if is_py2:
            b"{}".format(v)

    def test_default(self):
        v = Value(5)
        self.assertTrue(isinstance(v, DefaultValue))

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

    def test_array(self):
        a = array.array("i", range(0, 100))
        v = Value(a)
        s = v.string_value()
        self.assertTrue("array.array('i'" in s)

    def test_list(self):
        v = Value([])
        self.assertTrue(isinstance(v, ListValue))
        self.assertEqual("[]", repr(v))

    def test_set(self):
        v = Value(set())
        self.assertTrue(isinstance(v, SetValue))

    def test_tuple(self):
        v = Value(tuple())
        self.assertTrue(isinstance(v, TupleValue))

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
        repr(v)

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


    def test_exception(self):
        v = Value(ValueError("foo bar"))
        self.assertTrue(isinstance(v, ExceptionValue))
        repr(v)

    def test_module(self):
        v = Value(testdata)
        self.assertTrue(isinstance(v, ModuleValue))
        repr(v)

    def test_dict_keys(self):
        d = {"foo": 1, "bar": 2}
        v = Value(d.keys())
        self.assertEqual("LIST", v.typename)


