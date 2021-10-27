# Customizing Pout

## How Pout decides what to print

Pout uses `pout.value.Value` to decide how to print out any values passed to `pout.v()`. The `Value` class uses the `pout.value.Values` class to actually find the `Value` subclasses and decide which is the correct `Value` subclass for the given value (see the `pout.value.Values.find_class` method).

You can completely replace the `Values` class with your own by doing something like:

```python
import pout.value

class MyValues(pout.value.Values):
    @classmethod
    def find_class(cls, val):
        # customize this to decide how to handle val
        pass
    
pout.value.Value.values_class = MyValues
```

Pout will now use your `MyValues` class to find the correct `Value` subclass.


## Add a function

This section is intended for people wanting to add core functionality to Pout itself.

Add an `Interface` subclass to `pout.interface` and implement the required methods

```python
class Foo(Interface):
    def __call__(self, *args, **kwargs):
        # the args and kwargs are what's passed to pout.foo()
        pass
    
    def value(self):
        # return the value you want Foo to return
        pass
```

If your class is not in the `pout.interface` module you will need to manually inject your new class into pout:

```python
Foo.inject()
```

After `.inject()` is called then `pout.<FUNCTION_NAME>` should work and use your custom interface subclass.


## Add a new value

This section is intended for people wanting to add core functionality to Pout itself.

Add a `Value` subclass to `pout.value`:

```python
class CustomValue(Value):
    @classmethod
    def is_valid(cls, val):
        # return True if val is the right type
    
    def string_value(self):
        # return string representation of val
```

You can use the class hierarchy to decide when your `CustomValue` class should be checked. For example, if you want your class to be checked before `ListValue` because your custom value is a derivative of a `list` then you would just have `CustomValue` extend `ListValue` and it will be checked before `ListValue` in `Values.find_class()`.
