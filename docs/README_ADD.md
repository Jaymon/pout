# Add a function

1. Add an interface class in `pout/interface.py`
2. Import the interface class into `pout/__init__.py`
3. Set a class constant so it can be overridden (eg, `ValueInterface` is set to `V_CLASS` in `pout/__init__.py`)
4. Add your new function using the existing functions as a template (eg, `pout.v`).
5. Add appropriate tests to make sure everything is working as expected


# Add a new value

1. Modify `pout.value.Inspect` to know about your new value.

    Basically, `Inspect.typename` should return the name you want to give to this value, and you usually add an `Inspect.is_NAME` method and then modify `Inspect.typename` to check that `is_NAME` method and return the type name.

2. Add `TypenameValue` class.

    If you're typename is `FOO` then you would add `value.FooValue`. Whatever value you choose for the type name, it will be normalized to find the `*Value` class, so if `FOO_BAR` would become `FooBar`.

3. The `Value` method you will usually override is `Value.string_value`

    You might also need to override `Value.__iter__`.

4. Add tests to make sure your new value is printing correctly
