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

    def test_object(self):
    
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
