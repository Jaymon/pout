"""
test pout

right now this doesn't do much more than just print out pout statements, but someday I will
go through and add assert statements

link -- http://docs.python.org/library/unittest.html

to run on the command line:
python -m unittest test_pout.PoutTest.test_method
"""

import pout
import unittest

class Foo(object):
    bax=4
    def __init__(self):
        self.bar = 1
        self.che = 2
        self.baz = 3

class Bar(object):
    def __init__(self):
        self.foo = 1
        self.che = 2
        self.baz = 3

    def __str__(self):
        return u"Bar"

class Che(object):

    def __getattr__(self, key):
        return self.__getattr(key)

    def __str__(self):
        return u"Che"

class PoutTest(unittest.TestCase):

    def test_multiline_call(self):
        
        foo = 1
        bar = 2
        
        from pout import v as voom
        
        voom(
            foo,bar
        )
        
        pout.v(
            foo,
            bar,
            "this is a string"
        )

    def test_multi(self):
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

    def test_object(self):
    
        f = Foo()
        
        print vars(f.__class__)
        
        pout.v(f)
        
        return 
    
        c = Che()
        pout.v(c)

    def test_exception(self):
    
        e = IndexError("foo")
        pout.v(e)
        
        try:
            
            raise e
            
        except Exception, e:
            pout.v(e)

    def test_h(self):
        
        pout.h(1)
        
        pout.h()

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
