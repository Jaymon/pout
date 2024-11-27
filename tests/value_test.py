# -*- coding: utf-8 -*-
import hmac
import hashlib
import array
import re
from pathlib import Path
import datetime
import uuid

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
    StringValue,
    BytesValue,
    InstanceValue,
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
        print(r)
        return

        v = Value(100, show_instance_type=True)
        r = v.string_value()
        self.assertFalse("Instance Properties" in r, r)
        self.assertTrue("int instance" in r)
        self.assertTrue("100" in r)
        self.assertTrue("<" in r)

    def test_primitive_bool(self):
        v = Value(True, show_instance_type=True)
        r = v.string_value()
        self.assertFalse("Instance Properties" in r, r)
        self.assertTrue("bool instance" in r)
        self.assertTrue("True" in r)
        self.assertTrue("<" in r)

    def test_primitive_float(self):
        v = Value(123456.789, show_instance_type=True)
        r = v.string_value()
        self.assertFalse("Instance Properties" in r, r)
        self.assertTrue("float instance" in r)
        self.assertTrue("123456.789" in r)
        self.assertTrue("<" in r)

    def test_primitive_none(self):
        v = Value(None, show_instance_type=True)
        r = v.string_value()
        self.assertFalse("Instance Properties" in r, r)
        self.assertTrue("NoneType instance" in r)
        self.assertTrue("<" in r)

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
        v = Value(t, OBJECT_DEPTH=1)
        c = v.string_value()
        self.assertTrue("'bar': <dict" in c)

    def test_iterate_limit(self):
        """make sure iterators are cutoff when they reach the set limit"""
        t = list(range(0, 100))
        v = Value(t, ITERATE_LIMIT=10)
        c = v.string_value()
        self.assertTrue("..." in c)

        t = {f"{v}": v for v in range(0, 100)}
        v = Value(t, ITERATE_LIMIT=10)
        c = v.string_value()
        self.assertTrue("..." in c)

    def test__get_info_1(self):
        class Foo(object):
            one = "one"

        class Bar(Foo):
            two = "two"

        v = Value(Bar)
        info_dict = v._get_info()
        self.assertTrue("one" in info_dict["class_properties"])
        self.assertTrue("two" in info_dict["class_properties"])

        v = Value(Bar())
        info_dict = v._get_info()
        self.assertTrue("one" in info_dict["class_properties"])
        self.assertTrue("two" in info_dict["class_properties"])

        b = Bar()
        b.two = "three"
        v = Value(b)
        info_dict = v._get_info()
        r = info_dict["instance_properties"]["two"].val_value()
        self.assertEqual("three", r)

    def test__get_info_classmethod(self):
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
        info = v._get_info(show_methods=True)
        self.assertEqual({}, info["class_properties"])
        self.assertEqual({}, info["instance_properties"])
        self.assertTrue("foo" in info["methods"])

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
        self.assertTrue("<property" in s)

    def test_set(self):
        v = set(["foo", "bar", "che"])
        t = Value(v)
        self.assertTrue(SetValue.is_valid(v))
        self.assertEqual("SET", t.typename)

    def test_typename(self):
        class FooTypename(object): pass
        v = FooTypename()
        self.assertEqual('INSTANCE', Value(v).typename)
        self.assertEqual('CALLABLE', Value(FooTypename.__init__).typename)

        v = 'foo'
        self.assertEqual('STRING', Value(v).typename)

        v = 123
        self.assertEqual('INT', Value(v).typename)

        v = True
        self.assertEqual('BOOL', Value(v).typename)

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

    def test_callable(self):
        class InsCall(object):
            def __call__(self): pass
            @classmethod
            def cmeth(cls): pass

        instance = InsCall()

        v = Value(instance)
        self.assertEqual('INSTANCE', v.typename)

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
        self.assertTrue("{}" in r)

    def test_dict_populated(self):
        v = Value({"foo": 1, "bar": 2})
        self.assertTrue(isinstance(v, DictValue))

        r = v.string_value()
        self.assertTrue("dict (2)" in r, r)
        self.assertTrue("'foo': 1" in r, r)

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

        pout.v(d)

    def test_dictproxy(self):
        class FooDictProxy(object): pass
        v = Value(FooDictProxy.__dict__)
        self.assertTrue(isinstance(v, DictProxyValue))

    def test_list_empty(self):
        v = Value(
            [],
            show_simple_empty=False,
            show_instance_type=True,
            show_instance_id=True
        )
        self.assertTrue(isinstance(v, ListValue))

        r = v.string_value()
        self.assertTrue("<list (0) instance at" in r)

    def test_list_2(self):
        v = Value([
            testdata.get_unicode_words(),
            testdata.get_unicode_words(),
        ])

        r = v.string_value()
        self.assertTrue("list (2)" in r)

    def test_array(self):
        a = array.array("i", range(0, 10))
        v = Value(a, show_instance_type=True)
        s = v.string_value()
        self.assertTrue("array.array ('i')" in s)

    def test_set(self):
        v = Value(set())
        self.assertTrue(isinstance(v, SetValue))

        s = set(["foo", "bar"])
        v = Value(s, show_instance_type=True)
        r = v.string_value()
        self.assertTrue("set (2) instance" in r)
        self.assertTrue("bar" in r)

    def test_generator_1(self):
        v = Value(range(10), show_instance_type=True)

        r = v.string_value()
        self.assertTrue("<range (10) generator")

    def test_generator_builtin(self):
        v = (x for x in range(100))
        t = Value(v)

        self.assertTrue(GeneratorValue.is_valid(v))
        self.assertEqual("GENERATOR", t.typename)

        v = map(str, range(5))
        t = Value(v)
        self.assertTrue(GeneratorValue.is_valid(v))
        self.assertEqual("GENERATOR", t.typename)

    def test_generator_yield(self):
        def foo():
            for x in range(10):
                yield x

        t = Value(foo(), show_instance_type=True)
        s = t.string_value()
        self.assertTrue("(10) generator" in s)

    def test_tuple(self):
        v = Value(tuple([1, 2, 3, 4]), show_instance_type=True)
        self.assertTrue(isinstance(v, TupleValue))

        r = v.string_value()
        self.assertTrue("tuple (4) instance" in r)

    def test_string(self):
        v = Value("")
        self.assertTrue(isinstance(v, StringValue))

        r = v.string_value()
        self.assertTrue("\"\"" in r, r)

        v = Value("foo bar")
        r = v.string_value()
        self.assertTrue("str (7)" in r, r)
        self.assertTrue("foo bar" in r, r)

    def test_bytes_1(self):
        v = Value(b"")
        self.assertTrue(isinstance(v, BytesValue))

    def test_bytes_2(self):
        d = hmac.new(b"this is the key", b"this is the message", hashlib.md5)
        v = Value(d.digest())

        r = v.string_value()
        self.assertTrue(r.startswith("b"))

    def test_bytes_3(self):
        v = memoryview(b'abcefg')
        t = Value(v)
        self.assertTrue(BytesValue.is_valid(v))
        self.assertEqual("BYTES", t.typename)

        v = bytearray.fromhex('2Ef0 F1f2  ')
        t = Value(v)
        self.assertTrue(BytesValue.is_valid(v))
        self.assertEqual("BYTES", t.typename)

        v = bytes("foobar", "utf-8")
        t = Value(v)
        self.assertTrue(BytesValue.is_valid(v))
        self.assertEqual("BYTES", t.typename)

    def test_bytes_string(self):
        v = Value(bytearray([65, 66, 67, 68]))
        r = v.string_value()
        self.assertTrue("b\"" in r, r)
        self.assertTrue("ABCD" in r, r)

        v = Value(b"foo bar")
        r = v.string_value()
        self.assertTrue("b\"" in r, r)
        self.assertTrue("foo bar" in r, r)

        v = Value(b"")
        r = v.string_value()
        self.assertTrue("b\"\"" in r, r)

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
        self.assertTrue(r.startswith(f"{m.__name__}"))

    def test_object_nested(self):
        class Foo(object):
            pass

        f = Foo()
        f.bar = 1
        f.foo = f

        v = Value(f)
        r = v.string_value()
        self.assertTrue("foo = <" in r, r)
        self.assertTrue("bar = 1" in r, r)

    def test_object_repeated_1(self):
        class Foo(object):
            pass

        f = Foo()
        f.bar = 1

        v = Value([f for _ in range(5)])

        r = v.string_value()
        self.assertTrue("0: ValueTest" in r, r)
        self.assertTrue("1: <ValueTest" in r, r)

    def test_object_repeated_2(self):
        """This test was created to spot check issue 96 but I can't duplicate
        the problem

        https://github.com/Jaymon/pout/issues/96
        """
        m = testdata.create_module("""
            class Parent(object):
                classes = []
                def __init_subclass__(cls):
                    cls.classes.append(cls)

            class Foo(Parent):
                pass

            class Bar(Parent):
                pass

            class Che(Parent):
                pass
        """).get_module()

        v = Value(m.Bar.classes, OBJECT_DEPTH=10)
        s = v.string_value()

        self.assertEqual(1, s.count("Foo class at"))
        self.assertEqual(1, s.count("Bar class at"))
        self.assertEqual(1, s.count("Che class at"))

    def test_object_1(self):
        class FooObject(object):
            bar = 1
            che = "2"

        o = FooObject()
        o.baz = [3]
        indent = environ.INDENT_STRING

        v = Value(o)
        self.assertTrue(isinstance(v, InstanceValue))

        r = v.string_value()
        self.assertRegex(r, rf"\n[{indent}]+<\n")

        d = {
            "che": o,
            "baz": {"foo": 1, "bar": 2}
        }
        v = Value(d)
        r = v.string_value()
        self.assertTrue(f"\n{indent * 3}<\n" in r)

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
        c1 = Value(t, OBJECT_DEPTH=10).string_value()
        c2 = Value(t, OBJECT_DEPTH=1).string_value()
        self.assertNotEqual(c1, c2)

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
        Value(t).string_value()

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
        c = Value(o).string_value()
        self.assertTrue(s in c)

    def test_object___pout___class(self):
        """The __pout__ method could cause failure when defined on a class
        and the class is being outputted because __pout__ is an instance
        method, this makes sure __pout__ failing doesn't fail the whole thing
        """
        class Foo(object):
            def __pout__(self):
                return 1

        v = Value(Foo)
        s = v.string_value()
        self.assertTrue(".Foo" in s)

    def test_std_collections__pout__(self):
        """https://github.com/Jaymon/pout/issues/61"""
        class PoutDict(dict):
            def __pout__(self):
                return "custom dict"

        d = PoutDict(foo=1, bar=2)
        v = Value(d)
        s = v.string_value()
        self.assertTrue("custom dict" in s)

    def test_object_string_limit(self):
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
        #self.assertTrue("bar = int instance" in s, s)
        self.assertRegex(s, r"bar\s=\s1\s", s)

        v = Value(object, show_instance_id=True, show_instance_type=True)
        self.assertTrue(isinstance(v, TypeValue))

        s = v.string_value()
        self.assertRegex(s, r"object\sclass\sat\s\dx[^>]+?", s)

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
        self.assertTrue("re:Pattern" in r)
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
        self.assertTrue(".clsmethod(" in s, s)

        k = Klass()
        v = Value(k.instancemethod)
        s = v.string_value()
        self.assertTrue("<method tests." in s)
        self.assertTrue(".instancemethod(" in s, s)

        def func(*args, **kwargs): pass
        v = Value(func)
        s = v.string_value()
        self.assertTrue("<function tests." in s)
        self.assertTrue(".func(" in s, s)

    def test_callable_2(self):
        v = Value(object.__new__)
        self.assertTrue(isinstance(v, CallableValue))

        r = v.string_value()
        self.assertTrue("staticmethod" in r, r)
        self.assertTrue(".__new__" in r, r)

    def test_callable_3(self):
        class Foo(object):
            def get_foo(self, **kwargs):
                pass

        v = Value(Foo().get_foo)
        r = v.string_value()
        self.assertTrue(".get_foo" in r)

    def test_datetime(self):
        dt = datetime.datetime.now()

        v = Value(dt)
        r = v.string_value()
        self.assertTrue(str(dt) in r)
        self.assertTrue("<" in r)

        v = Value(dt, show_simple_value=False)
        r = v.string_value()
        self.assertTrue(str(dt) in r)
        self.assertTrue("<" in r)
        self.assertTrue("year:" in r)

        v = Value(dt, show_simple=True)
        r = v.string_value()
        self.assertTrue(r.startswith("\""))
        self.assertFalse("\n" in r)

    def test_pathlib_path(self):
        p = Path("/foo/bar/che")
        v = Value(p)
        s = v.string_value()
        self.assertEqual(4, len(s.splitlines(False)))
        self.assertTrue("/foo/bar/che" in s)

    def test_class_vars_inheritance(self):
        class VarParent(object):
            foo = 1

        class VarChild2(VarParent):
            foo = 2

        class VarChild1(VarParent):
            pass

        v = Value(VarChild2())
        r = v.string_value()
        self.assertRegex(r, r"\s2\s", r)

        v = Value(VarChild1())
        r = v.string_value()
        self.assertRegex(r, r"\s1\s", r)

    def test_show_simple_1(self):
        l = [self.get_dict() for _ in range(5)]

        v = Value(l, show_simple=True)
        r = v.string_value()
        self.assertTrue(r.startswith("["))
        self.assertTrue(r.endswith("]"))

    def test_show_simple_str(self):
        s = self.get_words()
        v = Value(s, show_simple=True)
        r = v.string_value()
        self.assertFalse("\n" in r)
        self.assertTrue(r.startswith("\""))
        self.assertTrue(r.endswith("\""))

    def test_show_simple_empty(self):
        vio = [
            ({}, "{}"),
            ([], "[]"),
            ("", "\"\""),
            ('', "\"\""),
            (set(), "set()"),
            (tuple(), "()"),
        ]

        for vin, vout in vio:
            v = Value(vin, show_simple=True)
            r = v.string_value()
            self.assertEqual(vout, r)

    def test_show_instance_id_1(self):
        d = self.get_dict()
        v = Value(d)
        r = v.string_value()
        self.assertFalse("at 0x" in r)

    def test_show_instance_id_empty(self):
        """
        https://github.com/Jaymon/pout/issues/93
        """
        d = {
            "dict": {},
            "list": [],
            "bool": False,
            "str": "",
            "tuple": tuple(),
            "set": set(),
            "int": 0,
            "float": 0.0,
            "None": None,
        }
        v = Value(d)
        r1 = v.string_value()
        self.assertFalse("<dict" in r1)
        for v in d.values():
            v = str(v)
            self.assertTrue(v in r1, v)

        v = Value(
            d,
            show_simple_empty=False,
            show_instance_id=True,
            show_instance_type=True
        )
        r2 = v.string_value()
        self.assertTrue("<dict" in r2)
        self.assertTrue("bool instance" in r2)
        self.assertNotEqual(r1, r2)

        d2 = {
            "dict": {"foo": 1},
            "list": ["foo", "bar"],
            "bool": True,
            "str": "foo bar",
            "tuple": ("foo", "bar"),
            "set": set(["foo", "bar"]),
            "int": 1000,
            "float": 2000.0,
            "None": None,
        }
        v = Value(d2)
        r3 = v.string_value()
        self.assertNotEqual(r1, r3)

    def test_show_instance_id_object_depth(self):
        """empty values were getting returned when simple prefix was used in
        conjunction with object depth, this means full dictionaries would
        return as {} and it confused me for longer than I care to admit"""
        d = {
            "foo": {
                "one": 1,
                "two": 2
            }
        }

        v = Value(
            d,
            object_depth=1,
            show_instance_type=False,
            show_instance_id=False
        )
        s = v.string_value()
        self.assertTrue(": <dict (2)>" in s)
        self.assertTrue("foo" in s)

    def test_uuid(self):
        v = Value(uuid.uuid4())
        s = v.string_value()
        self.assertTrue("UUID" in s)
        self.assertTrue("<" in s)

        v = Value(uuid.uuid4(), show_simple_value=False)
        s = v.string_value()
        self.assertTrue("UUID" in s)
        self.assertTrue("version:" in s)
        self.assertTrue("<" in s)

        v = Value(uuid.uuid4(), show_simple=True)
        s = v.string_value()
        self.assertTrue(s.startswith("\""))
        self.assertTrue(s.endswith("\""))
        self.assertFalse("\n" in s)

    def test_trailing_whitespace(self):
        v = Value([1, 2])
        s = v.string_value()
        self.assertFalse(s[-1].isspace())

    def test_module_output(self):
        v = Value(testdata)
        s = v.string_value()
        for header in ["Properties", "Classes", "Functions", "Modules"]:
            self.assertTrue(header in s)

