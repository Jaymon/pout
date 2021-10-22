# Customizing Pout

## How Pout decides what to print

Pout uses `pout.value.Value` to decide how to print out any values passed to `pout.v()`. The `Value` class uses the `pout.value.Values` class to actually find the `Value` subclasses and decide which is the correct `Value` subclass for the given value (see the `pout.value.Values.find_class` method).

You can completely replace the `Values` class with your own by doing something like:

```python
import pout.value

class MyValues(pout.value.Values):
    pass
    
pout.value.Value.values_class = MyValues
```

Pout will now use your `MyValues` clas to find the correct `Value` subclass.


## Add a function

1. Add an interface class in `pout/interface.py`
2. Import the interface class into `pout/__init__.py`
3. Set a class constant so it can be overridden (eg, `ValueInterface` is set to `V_CLASS` in `pout/__init__.py`)
4. Add your new function using the existing functions as a template (eg, `pout.v`).
5. Add appropriate tests to make sure everything is working as expected


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
