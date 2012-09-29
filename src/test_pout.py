"""
test pout

right now this doesn't do much more than just print out pout statements, but someday I will
go through and add assert statements

link -- http://docs.python.org/library/unittest.html

to run on the command line:
python -m unittest test_pout[.ClassTest[.test_method]]
"""

import sys
import unittest

import pout

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

class Che(object):

    f = Foo()
    b = Bar()

    def __getattr__(self, key):
        return self.__getattr(key)

    def __str__(self):
        return u"Che"

class Bax():
    '''
    old school defined class that doesn't inherit from object
    '''
    pass

def baz():
    pass

class PoutTest(unittest.TestCase):
    '''
    any non specific function testing should go here
    '''
    
    def test_ipython_fail(self):
        '''
        ipython would fail because the source file couldn't be read
        
        since -- 7-19-12
        '''
        mp_orig = pout._get_call_info
        
        def _get_call_info_fake(frame_tuple, called_module='', called_func=''):
            call_info = {}
            call_info['frame'] = frame_tuple
            call_info['line'] = frame_tuple[2]
            call_info['file'] = '/fake/file/path'
            call_info['call'] = u''
            call_info['arg_names'] = []
            return call_info
            
        # monkey patch to do get what would be returned in an iPython shell
        pout._get_call_info = _get_call_info_fake
        
        # this should print out
        pout.v(range(5))
        
        mp_orig = pout._get_call_info = mp_orig
    
    def test_get_type(self):
    
        v = 'foo'
        self.assertEqual('STRING', pout._get_type(v))
        
        v = 123
        self.assertEqual('DEFAULT', pout._get_type(v))
        
        v = True
        self.assertEqual('DEFAULT', pout._get_type(v))
        
        v = Foo()
        self.assertEqual('OBJECT', pout._get_type(v))
        self.assertEqual('FUNCTION', pout._get_type(Foo.__init__))

        self.assertEqual('FUNCTION', pout._get_type(baz))
        
        v = TypeError()
        self.assertEqual('EXCEPTION', pout._get_type(v))
        
        v = {}
        self.assertEqual('DICT', pout._get_type(v))
        
        v = []
        self.assertEqual('LIST', pout._get_type(v))
        
        v = ()
        self.assertEqual('TUPLE', pout._get_type(v))
        
        self.assertEqual('MODULE', pout._get_type(pout))
        
        import ast
        self.assertEqual('MODULE', pout._get_type(ast))
        
        #self.assertEqual('CLASS', pout._get_type(self.__class__))

class TTest(unittest.TestCase):
    """
    test the pout.t() method
    """

    def test_t(self):
        pout.t()

class HTest(unittest.TestCase):
    """
    test the pout.h() method
    """
    def test_h(self):
        
        pout.h(1)
        
        pout.h()

class VTest(unittest.TestCase):

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

    def test_exception(self):
    
        e = IndexError("foo")
        #pout.v(e)
        
        try:
        
            f = Foo()
            f.raise_error()
            
            raise e
            
        except Exception, e:
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

if __name__ == '__main__':
    unittest.main()
