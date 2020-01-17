# Customizing Pout

## Overriding Values

You can actually completely replace the current Value system with your own by doing something like:

```python
import pout
from pout.value import Inspect, Value

class MyInspect(Inspect):
    @property
    def classtype(self):
        return MyValue
        
class MyValue(Value):
    def string_value(self):
        return repr(self.val)

pout.Value.inspect_class = MyInspect

class Foo(object):
    bar = {"che": 1, "baz": 2}
        
f = Foo()
pout.v(f)
```

Which would result in:

```
f = <__main__.Foo object at 0x10d025310>

(FILENAME.py:N)
```

Likewise, you can selectively override just certain types if you want by doing something like:

```python
# override just dictionary values
class MyInspect(Inspect):
    @property
    def classtype(self):
        if self.is_dict():
            return MyValue
        else:
            return super(MyInspect, self).classtype
```


## Add a function

1. Add an interface class in `pout/interface.py`
2. Import the interface class into `pout/__init__.py`
3. Set a class constant so it can be overridden (eg, `ValueInterface` is set to `V_CLASS` in `pout/__init__.py`)
4. Add your new function using the existing functions as a template (eg, `pout.v`).
5. Add appropriate tests to make sure everything is working as expected


## Add a new value

1. Modify `pout.value.Inspect` to know about your new value.

    Basically, `Inspect.typename` should return the name you want to give to this value, and you usually add an `Inspect.is_NAME` method and then modify `Inspect.typename` to check that `is_NAME` method and return the type name.

2. Add `TypenameValue` class in `pout/value.py`.

    If your typename is `FOO` then you would add `value.FooValue`. Whatever value you choose for the type name, it will be normalized to find the `*Value` class, so `FOO_BAR` would become `FooBar`.

3. The `Value` method you will usually override is `Value.string_value()`

    You might also need to override `Value.__iter__()`.

4. Add tests to make sure your new value is printing correctly
