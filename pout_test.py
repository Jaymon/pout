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
import hmac

import testdata

# remove any global pout (this is to overcome me putting pout in sites.py
if 'pout' in sys.modules:
    sys.modules['pout2'] = sys.modules['pout']
    del sys.modules['pout']

    # allow the global pout to be used as pout2 without importing
    try:
        import __builtin__
        if hasattr(__builtin__, "pout"):
            del __builtin__.pout
        __builtin__.pout2 = sys.modules['pout2']

    except ImportError:
        pass

# this is the local pout that is going to be tested
import pout
import Queue


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
        v = "foo"
        pout.v(v)
        v = "bar"
        pout.v(v)
        pout.pout_class = original_class

    def test_issue16(self):
        """ https://github.com/Jaymon/pout/issues/16 """
        class Module(object): pass
        ret = "foo"
        default_val = "bar"
        self.issue_module = Module()
        self.issue_fields = {}
        k = "che"

        pout.v(ret, default_val, getattr(self.issue_module, k, None), self.issue_fields.get(k, None))

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

        fgn = FooGetName()
        pout.v(fgn)

    def test__get_arg_names(self):
        """see also VTest.test_multi_args() and VTest.test_multiline_comma()"""

        p = pout.Pout()

        r = p._get_arg_names("\n".join([
            u"        pout.v(",
            u'            "foo",',
            u'            "bar",',
            u'            "che",',
            u'        )'
        ]))
        self.assertEqual(3, len(r[0]))
        for x in range(3):
            self.assertEqual(u"", r[0][x])
        self.assertEqual(True, r[1])

        r = p._get_arg_names("\n".join([
            u"        pout.v(",
            u'"foo",',
            u'"bar",',
            u'"che"'
        ]))
        self.assertEqual(3, len(r[0]))
        for x in range(3):
            self.assertEqual(u"", r[0][x])
        self.assertEqual(False, r[1])

        r = p._get_arg_names(u"        pout.v(\"this string has 'mixed quotes\\\"\")")
        self.assertEqual(1, len(r[0]))
        self.assertEqual(u"", r[0][0])

        r = p._get_arg_names(u" pout.v(name); hasattr(self, name)")
        self.assertEqual(u"name", r[0][0])
        self.assertEqual(1, len(r[0]))

        r = p._get_arg_names("\n".join([
            u"        pout.v(",
            u'"foo",',
            u'"bar",',
            u'"che",'
        ]))
        for x in range(3):
            self.assertEqual(u"", r[0][x])
        self.assertEqual(False, r[1])

        r = p._get_arg_names(u"pout.v(foo, [bar, che])")
        self.assertEqual(u"foo", r[0][0])
        self.assertEqual(u"[bar, che]", r[0][1])

        r = p._get_arg_names(u"pout.v(foo, bar)")
        self.assertEqual(u"foo", r[0][0])
        self.assertEqual(u"bar", r[0][1])

        r = p._get_arg_names(u"pout.v(foo)")
        self.assertEqual(u"foo", r[0][0])

        r = p._get_arg_names(u"pout.v('foo')")
        self.assertEqual(u"", r[0][0])

        r = p._get_arg_names(u'pout.v("foo")')
        self.assertEqual(u"", r[0][0])

        r = p._get_arg_names(u"pout.v('foo\'bar')")
        self.assertEqual(u"", r[0][0])

        r = p._get_arg_names(u"pout.v('foo, bar, che')")
        self.assertEqual(u"", r[0][0])

        r = p._get_arg_names(u"pout.v((foo, bar, che))")
        self.assertEqual(u"(foo, bar, che)", r[0][0])

        r = p._get_arg_names(u"pout.v((foo, (bar, che)))")
        self.assertEqual(u"(foo, (bar, che))", r[0][0])

        r = p._get_arg_names(u"pout.v([foo, bar, che])")
        self.assertEqual(u"[foo, bar, che]", r[0][0])

        r = p._get_arg_names(u"pout.v([foo, [bar, che]])")
        self.assertEqual(u"[foo, [bar, che]]", r[0][0])

        r = p._get_arg_names(u"pout.v([[foo], [bar, che]])")
        self.assertEqual(u"[[foo], [bar, che]]", r[0][0])


    def test_find_call_depth(self):
        s = "foo"
        class PoutChild(pout.Pout):
            def v(self, *args):
                self._printstr("PoutChild")
                super(PoutChild, self).v(*args)

        pout.pout_class = PoutChild
        pout.v(s)
        pout.pout_class = pout.Pout

    def test__get_arg_info(self):
        foo = 1
        pout.v(foo)

    def test_multi_command_on_one_line(self):
        """make sure we are finding the correct call on a multi command line"""
        name = "foo"
        val = 1
        if not hasattr(self, name): pout.v(name); hasattr(self, name)

    def test_unicode_error(self):
        d = hmac.new(b"this is the key", "this is the message")
        pout.v(d.digest())

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
            call_info['call'] = u''
            call_info['arg_names'] = []
            return call_info

        # monkey patch to do get what would be returned in an iPython shell
        pout.Pout._get_call_info = _get_call_info_fake

        # this should print out
        pout.v(range(5))

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
        pout.c('this is the input')
        pout.c(u'\u304f')
        pout.c(u'just\r\ntesting')
        pout.c(u'just', u'testing')
        pout.c(u'\U00020731')

class BTest(unittest.TestCase):
    def test_b(self):
        pout.b()
        pout.b(5)
        pout.b('this is the title')
        pout.b('this is the title 2', 5)
        pout.b('this is the title 3', 3, '=')


class PTest(unittest.TestCase):
    def test_p_one_level(self):
        pout.p('foo')
        time.sleep(.25)
        pout.p()

    def test_p_multi_levels(self):
        pout.p('multi foo')
        pout.p(u'multi bar')
        time.sleep(0.25)
        pout.p()
        time.sleep(0.25)
        pout.p()

    def test_p_with(self):
        with pout.p("with foo"):
            time.sleep(0.25)



class XTest(unittest.TestCase):
    def test_x(self):
        # pout.x()
        pass

class TTest(unittest.TestCase):
    """
    test the pout.t() method
    """

    def test_t(self):
        pout.t()

    def test_t_with_assign(self):
        '''
        there was a problem where the functions to get parse the call would fail
        when one of the inputs was a dict key assignment, this test makes sure that
        is fixed

        since -- 10-8-12 -- Jay
        '''
        r = {}
        r['foo'] = self.get_trace()

    def get_trace(self):
        pout.t()

class HTest(unittest.TestCase):
    """
    test the pout.h() method
    """
    def test_h(self):

        pout.h(1)

        pout.h()


class VVTest(unittest.TestCase):
    def test_vv(self):
        d = {'foo': 1, 'bar': 2}
        pout.vv(d)


class VTest(unittest.TestCase):
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

        class DescExample(object):
            @Desc
            def foo(self): pass

        e = DescExample()
        e.foo()

    def test_class_vars(self):

        class VarParent(object):
            foo = 1

        class VarChild(VarParent):
            foo = 2
            def __init__(self):
                pout.v(self)

        vc = VarChild()

    def test_misclassified_instance(self):
        """objects that have a __getattr__ method that always return something get
        misclassified as dict proxies, this makes sure that is fixed"""

        def misclass_func():
            return 2

        class Misclass(object):
            def __getattr__(self, k):
                return 1

        m = Misclass()
        pout.v(m)

    def test_proxy_dict(self):
        pout.v(FooBar.__dict__)

    def test_multiline_comma(self):
        # https://github.com/Jaymon/pout/issues/12
        pout.v(
            "foo",
            "bar",
            "che",
        )

    def test_type(self):

        pout.v(type(100))
        pout.v(type([]))

    def test_str(self):
        '''
        since -- 3-28-2013
        '''
        s_unicode = "this is a unicode string"
        s_byte = b"this is a byte string"
        pout.v(s_unicode)
        pout.v(s_byte)

        s_unicode = ""
        s_byte = b""
        pout.v(s_unicode)
        pout.v(s_byte)

        d = {
            'foo': "foo is a unicode str",
            'bar': b"bar is a byte string"
        }
        pout.v(d)

    def test_sys_module(self):
        '''
        built-in modules fail, which they shouldn't

        since -- 7-19-12
        '''
        pout.v(sys)


    def test_multiline_call(self):

        foo = 1
        bar = 2
        def func(a, b):
            return a + b

        from pout import v as voom

        voom(
            foo,bar
        )

        pout.v(
            foo,
            bar,
            "this is a string"
        )

        from pout import v

        v(
            foo,
            bar)

        v(
            foo, bar)

        v(
            foo,

            bar

        )

        v(
            func(1, 4)
        )

        v(
            func(
                5,
                5
            )
        )

        import pout as poom

        poom.v(foo)


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

        foo = range(1, 10)
        pout.v(foo)

        foo = [range(1, 10) for x in range(2)]
        pout.v(foo)

        foo = {}
        pout.v(foo)

        foo = {'foo': 1}
        pout.v(foo)

        #pout._get_arg_info([foo])

    def test_queue(self):
        """Queue.Queue was failing, let's fix that"""
        pout.v(Queue.Queue)

    def test_precision(self):
        """float precision was cutting off at 2 decimal places"""

        f = 1380142261.454746
        pout.v(f)

        i = 1232432435
        pout.v(i)

        b = True
        pout.v(b)


class MTest(unittest.TestCase):
    def test_m(self):
        pout.m() # around 11
        l = range(1, 1000000)
        pout.m("after big list creation") # around 43


if __name__ == '__main__':
    unittest.main()

