# -*- coding: utf-8 -*-
"""
The Value classes in this file manage taking any python object and converting
it into a string that can be printed out
"""
import types
import inspect
import sys
import os
import traceback
import logging
import re
import array
from pathlib import PurePath
from types import MappingProxyType
from collections.abc import MappingView
from collections import Counter
import functools
import sqlite3
import datetime
import uuid
import ast

from .compat import *
from . import environ
from .path import Path
from .utils import String, OrderedItems, Color


logger = logging.getLogger(__name__)


class Values(list):
    """We want to keep a particular order of the Value subclasses to make sure
    that certain classes are checked before others, this is because certain
    values might actually resolve into 2 different sub values, so order becomes
    important

    this class maintains that order, basically, it makes sure all subclasses
    get checked before the parent class, so if you want your CustomValue to
    evaluate before DictValue, you would just have CustomValue extend DictValue

    This was the inspiration for datatypes.OrderedSubclasses but since pout
    has no dependencies pout can't use the much more robust datatypes version
    """
    def __init__(self):
        super().__init__()

        self.indexes = {}

    def insert(self, value_class):
        index = len(self)
        for vclass in reversed(inspect.getmro(value_class)):
            if issubclass(vclass, Value):
                index_name = f"{vclass.__module__}.{vclass.__name__}"
                if index_name in self.indexes:
                    index = min(index, self.indexes[index_name])

                else:
                    self.indexes[index_name] = len(self)
                    super().insert(index, vclass)

    def find_class(self, val):
        """Return the *Value class that represents val"""
        for vcls in self:
            try:
                if vcls.is_valid(val):
                    value_cls = vcls
                    break

            except Exception as e:
                # any exception is considered False
                logger.exception(e)

        return value_cls


class Value(object):
    """Pout is mainly used to print values of different objects, and that
    printing of objects happens in subclasses of this parent class. See the
    .interface.V class for how this is hooked into pout.v

    The most important method in this class is .string_value, check out that
    docblock for the order all the other *_value methods are called
    """
    #values_class = Values
    """Holds the class this will use to find the right Value class to return"""

    classes = Values()
    """Holds a cached instance of values_class for faster searches"""

    SHOW_METHODS = False
    """Whether object info includes methods by default"""

    SHOW_MAGIC = False
    """Whether object info includes magic variables/methods by default"""

    SHOW_VAL = True
    """Show the .val_value output"""

    SHOW_OBJECT = False
    """Show the .object_value output

    turns out, it's actually really annoying to me having extended built-in
    classes print their object value, it's 95% noise to the 5% I would find it
    handy"""

    SHOW_OBJECT_STRING = True
    """Whether object info includes __str__ method output by default"""

    SHOW_ALWAYS = False
    """Whether the object should always be expanded, if False then the first
    time an object is seen it will be expanded, if True then everytime the
    object is seen it will be expanded"""

    SHOW_SIMPLE = False
    """Output the value without all the bells and whistles. You would use this
    flag to get a value that is close to actual python code

    NOTE -- while this flips SHOW_SIMPLE_PREFIX and SHOW_SIMPLE_VALUE to True
    if it is True this can be checked separately and so subclasses that want
    to show different values depending on this or SHOW_SIMPLE_VALUE need to
    check this value first
    """

    SHOW_SIMPLE_EMPTY = True
    """See .empty_value"""

    SHOW_INSTANCE_ID = False
    """Output the memory address of the object when printing the prefix"""

    SHOW_INSTANCE_TYPE = False
    """Output the instance type name (see .instance_value)"""

    SHOW_SIMPLE_PREFIX = environ.SHOW_SIMPLE_PREFIX

    SHOW_SIMPLE_VALUE = environ.SHOW_SIMPLE_VALUE

    OBJECT_STRING_LIMIT = environ.OBJECT_STRING_LIMIT

    ITERATE_LIMIT = environ.ITERATE_LIMIT

    INDENT_STRING = environ.INDENT_STRING

    OBJECT_DEPTH = environ.OBJECT_DEPTH

    KEY_QUOTE_CHAR = environ.KEY_QUOTE_CHAR

    @property
    def typename(self):
        s = self.__class__.__name__.replace("Value", "")
        return String(s).snakecase().upper()

    @classmethod
    def is_valid(cls, val):
        return True

    def __new__(cls, val, depth=0, **kwargs):
        """through magic, instantiating an instance will actually create
        subclasses of the different *Value classes, once again, through magic
        """

        # we don't pass in (val, depth) because this just returns the instance
        # and then __init__ is called with those values also
        return super().__new__(cls.classes.find_class(val))

    def __init__(self, val, depth=0, **kwargs):
        self.val = val
        self.depth = depth
        self.instances = kwargs.pop("instances", {})
        self._seen_string_value = False
        self.set_instance_attributes(**kwargs)

    def __init_subclass__(cls):
        """Called when a child class is loaded into memory

        https://peps.python.org/pep-0487/
        """
        cls.classes.insert(cls)

    def set_instance_attributes(self, **kwargs):
        """update the instance attributes to reflect what is set in the
        environment and what was passed into this instance

        :param **kwargs: the passed in keywords
        """
        # we want to be able to update values based on what was passed in, so
        # if show_methods=True was passed in we want to update .SHOW_METHODS
        # for this instance
        for k, v in kwargs.items():
            for ik in [k, k.upper(), f"SHOW_{k.upper()}"]:
                if hasattr(self, ik):
                    setattr(self, ik, v)
                    break

        if self.SHOW_SIMPLE:
            self.SHOW_SIMPLE_PREFIX = True
            self.SHOW_SIMPLE_VALUE = True
            self.SHOW_SIMPLE_EMPTY = True
            self.SHOW_ALWAYS = True
            self.ITERATE_LIMIT = 0
            self.SHOW_OBJECT = False
            self.OBJECT_DEPTH = 0

        if self.SHOW_SIMPLE_PREFIX:
            self.SHOW_SIMPLE_EMPTY = True
            self.SHOW_INSTANCE_ID = False
            self.SHOW_INSTANCE_TYPE = False

        # certain flags only apply to this instance and not sub-instances
        ignore_keys = [
            "SHOW_VAL",
            "SHOW_OBJECT"
        ]
        for k in ignore_keys:
            kwargs.pop(k, None)

        self.kwargs = kwargs

    def get_instance(self, val, **kwargs):
        """Sometimes while generating the .string_value for .val sub Value
        instances need to be created or retrieved, they should be created
        or retrieved only using this method

        :param val: Any, the value to be wrapped in a Value instance
        :returns: Value, the val wrapped in a Value instance
        """
        vid = self._get_id(val)
        if vid in self.instances:
            instance = self.instances[vid]
            instance.depth = self.depth + 1

        else:
            kwargs.setdefault("depth", self.depth + 1)
            kwargs.setdefault("instances", self.instances)
            kwargs = {**self.kwargs, **kwargs}

            instance = Value(val, **kwargs)
            self.instances[vid] = instance

        return instance

    def has_body(self):
        """Returns True if .val has a body, ie, .val_value or .object_value
        will return a value"""
        return True

    def _is_magic(self, name):
        """Return true if the name is __name__

        since -- 7-10-12

        :param name: str, the name to check
        :returns: bool
        """
        return name.startswith('__') and name.endswith('__')

    def _getattr(self, val, key, default_val):
        """wrapper around global getattr(...) method that suppresses any
        exception raised"""
        try:
            ret = getattr(val, key, default_val)

        except Exception as e:
            logger.exception(e)
            ret = default_val

        return ret

    def _get_modpath(self, val):
        """Gets the modulepath where val is defined, used primarily in 
        ._get_name()

        :param val: Any
        :returns: str, the full modulepath where val is defined
        """
        module_name = ""
        if isinstance(val, types.ModuleType):
            module_name = self._getattr(val, "__name__", "")

        else:
            module_name = self._getattr(val, "__module__", "")

        return module_name or ""

    def _get_name(self, val, modpath=True, default='Unknown'):
        """get the full namespaced (module + class) name of the val object

        since -- 6-28-12

        :param val: Any, the value (everything is an object) object
        :param modpath: bool, True if the full module path should be part of
            the name also
        :param default: str, the default name if a decent name can't be found
        programmatically
        :returns: str, the full.module.Name
        """

        if isinstance(val, types.ModuleType):
            full_name = self._get_modpath(val)

        else:
            module_name = ""
            class_name = None
            for k in ["__qualname__", "__name__"]:

                if modpath and not module_name:
                    module_name = self._get_modpath(val)

                class_name = self._getattr(val, k, None)
                if not class_name:
                    cls = self._getattr(val, "__class__", None)
                    if cls:
                        class_name = self._getattr(cls, k, None)

                        if modpath and not module_name:
                            module_name = self._get_modpath(val)

                if class_name:
                    break

            if not class_name:
                class_name = default

            if module_name:
                module_name = f"{module_name}:"

            full_name = "{}{}".format(module_name, class_name)

        return full_name

    def _get_src_file(self, val, default='Unknown'):
        """return the source file path

        since -- 7-19-12

        :param val: Any, the value whose path you want
        :param default: str, what to return if src file can't be found
        :returns: str, the path, or something like 'Unknown' if you can't find
        the path
        """
        path = default

        try:
            # http://stackoverflow.com/questions/6761337/inspect-getfile-vs-inspect-getsourcefile
            # first try and get the actual source file
            source_file = inspect.getsourcefile(val)
            if not source_file:
                # get the raw file since val doesn't have a source file
                # (could be a .pyc or .so file)
                source_file = inspect.getfile(val)

            if source_file:
                path = os.path.realpath(source_file)

        except TypeError as e:
            path = default

        return path

    def getmembers(self, **kwargs):
        """Yields all the members of .val as Value instances

        This is named this way because it's kind of a wrapper around
        `inspect.getmembers`

        :returns: Generator[Value]
        """
        SHOW_MAGIC = kwargs.get("show_magic", self.SHOW_MAGIC)

        def iter_items(items):
            for k, v in items:
                if SHOW_MAGIC or not self._is_magic(k):
                    yield self.get_instance(v)

        try:
            try:
                items = vars(self.val).items()

            except TypeError as e:
                # Since vars() failed we are going to try and make
                # inspect.getmembers act like vars() Also, I could get a
                # recursion error if I tried to just do inspect.getmembers in
                # certain circumstances, I have no idea why
                items = inspect.getmembers(self.val)

        except Exception as e:
            items = [
                (
                    "<GETMEMBERS-ERROR>",
                    e
                )
            ]

        for k, v in items:
            if SHOW_MAGIC or not self._is_magic(k):
                yield k, self.get_instance(v)

    def _get_id(self, v):
        """Returns the Python memory object id as a nicely formatted string

        :param v: Any, the python object we want the id value of
        :returns: str, v's id in hex format
        """
        return "0x{:02x}".format(id(v))

    def _get_info(self, **kwargs):
        """Gathers all the information about this object

        each dict's key is the name of the property and the value is the actual
        property

        :param **kwargs:
            - show_methods: bool, return method information
            - show_magic: bool, don't filter out magic methods and properties,
                magic is determined through ._is_magic() method
        :returns: dict, keys are:
            - val_class: type, the class for .val
            - instance_properties: dict, all the instance properties of .val
            - clas_properties: dict, the class properties of .val
            - methods: dict, all the methods of .val
        """
        val = self.val

        val_class = self._getattr(val, "__class__", None)
        if val_class is type:
            val_class = val

        class_dict = {}
        methods_dict = {}
        instance_dict = {}

        SHOW_METHODS = kwargs.get("show_methods", self.SHOW_METHODS)

        for k, v in self.getmembers(**kwargs):
            if v.typename == "CALLABLE":
                if SHOW_METHODS:
                    methods_dict[k] = v

            else:
                if val is val_class:
                    class_dict[k] = v

                else:
                    instance_dict[k] = v

        if val_class:
            SHOW_MAGIC = kwargs.get("show_magic", self.SHOW_MAGIC)

            # build a full class variables dict with the variables of 
            # the full class hierarchy.
            # The reversing makes us go from parent -> child
            for pcls in reversed(inspect.getmro(val_class)):
                for k, v in vars(pcls).items():
                    # filter out anything that's in the instance dict also
                    # since that takes precedence.
                    if k not in instance_dict:
                        if SHOW_MAGIC or not self._is_magic(k):
                            v = self.get_instance(v)

                            if v.typename == "CALLABLE":
                                if SHOW_METHODS:
                                    methods_dict[k] = v

                            else:
                                class_dict[k] = v

        return {
            "val_class": val_class,
            "instance_properties": instance_dict,
            "class_properties": class_dict,
            "methods": methods_dict,
        }

    def _get_instance_type(self):
        return self.typename.lower()

    def _get_object_method(self):
        """Return self.val.__pout__ if it exists

        This is used in .method_value to generate the val value in
        .string_value

        :returns: callable
        """
        pout_method = self._getattr(self.val, "__pout__", None)
        if pout_method and callable(pout_method):
            return pout_method

    def _is_body_visible(self):
        """Returns True if the body should be visible, see .string_value"""
        ret = False

        if self.SHOW_ALWAYS:
            ret = True

        elif self.OBJECT_DEPTH <= 0:
            ret = True

        elif self.depth < self.OBJECT_DEPTH:
            ret = True

        return ret

    def _is_showing(self):
        """Return True if this instance is NOT considered "seen", which means
        it should generate its full string value

        An instance, by default, is seen when its string value has been
        fully generated once
        """
        return self.SHOW_ALWAYS or not self._seen_string_value

    def string_value(self):
        """This is the main "value" generation method, this is the method that
        should be called from external sources

        If a value has no body, then it returns a value like this:

            <OBJECT_START_VALUE><PREFIX_VALUE><OBJECT_STOP_VALUE>

        If there is a body, then the value will look more or less like this:

            <PREFIX_VALUE>
                <START_OBJECT_VALUE>
                    <OBJECT_VALUE>
                <STOP_OBJECT_VALUE>
                <START_VAL_VALUE>
                    <VAL_VALUE>
                <STOP_VAL_VALUE>

        Most Value subclasses will return either <OBJECT_VALUE> or
        <VAL_VALUE> but not both, though returning both is supported

        If the value doesn't have a <PREFIX_VALUE> (eg, a primitive like int)
        then it will return basically the string version of that primitive
        value

        :returns: str, a string suitable to be printed or whatever
        """
        ret = ""

        if not self._is_body_visible():
            ret = self.summary_value()

        elif not self.has_body():
            ret = self.empty_value()

        elif not self._is_showing():
            ret = self.seen_value()

        else:
            self._seen_string_value = True
            object_body = ""
            value_body = ""

            if self.SHOW_OBJECT:
                object_body = self.object_value()

            if self.SHOW_VAL:
                value_body = self.method_value()

                if not value_body:
                    value_body = self.val_value()

            if value_body or object_body:
                if prefix := self.prefix_value():
                    ret = Color.color_meta(prefix)

                    if object_body:
                        if ret:
                            ret += "\n"

                        ret += self._add_indent(
                            self._wrap_object_value(object_body),
                            1
                        )

                    if value_body:
                        if ret:
                            ret += "\n"

                        ret += self._add_indent(
                            self._wrap_val_value(value_body),
                            1
                        )

                else:
                    if value_body:
                        ret = self._wrap_val_value(value_body)

                    elif object_body:
                        ret = self._wrap_object_value(object_body)

            else:
                ret = self.summary_value()

        return ret

    def method_value(self):
        """Return the __pout__ method output completely ready for
        .string_value use as the val value"""
        ret = ""
        if pout_method := self._get_object_method():
            try:
                v = self.get_instance(pout_method())
                ret = v.val_value()

            except TypeError:
                # ignore instance method __pout__ being called as a
                # classmethod
                pass

        return ret

    def object_value(self):
        """Return information about the object itself

        This generates all the information about the Value as an object, it
        is used in .info_value() and is broken out so it can be more easily
        used in subclasses

        :returns: str, the object information body
        """
        s_body = ""
        src_file = ""

        val = self.val
        depth = self.depth

        SHOW_OBJECT_STRING = self.SHOW_OBJECT_STRING

        info_dict = self._get_info(
            show_methods=self.SHOW_METHODS,
            show_magic=self.SHOW_MAGIC,
        )

        if val_class := info_dict["val_class"]:
            src_file = self._get_src_file(val_class, default="")
            pclses = inspect.getmro(val_class)
            if pclses:
                s_body += "\n"
                for pcls in pclses:
                    psrc_file = self._get_src_file(pcls, default="")
                    if psrc_file:
                        psrc_file = Path(psrc_file)
                    pname = self._get_name(pcls)
                    if psrc_file:
                        pname = "{} ({})".format(pname, psrc_file)

                    if pname:
                        pname = Color.color_meta(pname)

                    s_body += "{}".format(pname)
                    s_body += "\n"

        if SHOW_OBJECT_STRING and hasattr(val, "__str__"):
            try:
                s_str = String(val)

            except Exception as e:
                s_str = f"__str__ failed with: {e}"
                strlen = len(s_str)

            else:
                strlen = len(s_str)
                OBJECT_STRING_LIMIT = self.OBJECT_STRING_LIMIT

                if strlen > OBJECT_STRING_LIMIT:
                    s_str = s_str.truncate(OBJECT_STRING_LIMIT)
                    s_str += "... Truncated {}/{} chars ...".format(
                        strlen - OBJECT_STRING_LIMIT,
                        strlen
                    )

            if s_str:
                s_str = Color.color_string(s_str)

            header = Color.color_header(f"__str__ ({strlen})")
            s_body += f"\n{header}:\n"
            s_body += self._add_indent(s_str, 1)
            s_body += "\n"

        def get_attr_str(k, v, indent_depth):
            s_attr = "{} = {}".format(Color.color_attr(k), v.string_value())
            s_attr = self._add_indent(s_attr, indent_depth)
            return s_attr + "\n"

        if class_dict := info_dict["class_properties"]:
            header = Color.color_header(
                f"Class Properties ({len(class_dict)})"
            )
            s_body += f"\n{header}:\n"

            for k, v in OrderedItems(class_dict):
                s_body += get_attr_str(k, v, 1)

        if instance_dict := info_dict["instance_properties"]:
            header = Color.color_header(
                f"Instance Properties ({len(instance_dict)})"
            )
            s_body += f"\n{header}:\n"

            for k, v in OrderedItems(instance_dict):
                s_body += get_attr_str(k, v, 1)

        if methods_dict := info_dict["methods"]:
            header = Color.color_header(
                f"Methods ({len(methods_dict)})"
            )
            s_body += f"\n{header}:\n"

            for k, v in OrderedItems(methods_dict):
                s_body += get_attr_str(k, v, 1)

        if self.typename == 'EXCEPTION':
            s_body += "\n"
            s_body += "\n".join(
                traceback.format_exception(None, val, val.__traceback__)
            )

        return s_body.strip()

    def val_value(self):
        """This is the method that will be most important to subclasses since
        the meat of generating the value of whatever value being represented
        will be generated

        :returns: str
        """
        return "{}".format(repr(self.val))

    def prefix_value(self):
        """Returns the prefix value

        The prefix value will usually look like this:

            <CLASSPATH> <INSTANCE_VALUE> at <ID_VALUE>

        This is impacted by a few class variables:
            * SHOW_SIMPLE - if True, will set SHOW_SIMPLE_PREFIX to True
            * SHOW_SIMPLE_PREFIX - the simple prefix, by default, is no
                prefix, so if this is True then this returns an empty string
            * SHOW_INSTANCE_ID - if False then don't call .id_value
            * SHOW_INSTANCE_TYPE - if False then don't return
                ._get_instance_type

        :returns: str
        """
        ret = ""

        if not self.SHOW_SIMPLE_PREFIX:
            ret = "{} {}".format(
                self.classpath_value(),
                self.instance_value(),
            )

            # let's strip since instance value can be empty
            ret = ret.rstrip()

            if self.SHOW_INSTANCE_ID:
                ret += " at {}".format(self._get_id(self.val))

        return ret

    def classpath_value(self):
        """The full class name (eg module.submodule.ClassName)

        This is a key component of <PREFIX_VALUE>

        :returns: str
        """
        return self._get_name(self.val, modpath=False) # just the classname

    def count_value(self):
        """Returns the count if it exists, this is handy for subclasses that
        want to show their count, things like dict, list, set, etc.

        :returns: int, the count, if None then it will be assumed the count
            doesn't exist. If int, then it assumes the count does exist and
            that's the count (which could be zero)
        """
        return None

    def instance_value(self):
        """Returns the instance name that's usually used in setting up the 
        prefix value

        :param **kwargs:
            - value: str, the instance value if you want it to be something
                other than the default value
        :returns: str
        """
        if self.SHOW_INSTANCE_TYPE:
            instance_value = self._get_instance_type()

        else:
            instance_value = ""

        count_value = self.count_value()
        if count_value is not None:
            if instance_value:
                instance_value = f"({count_value}) {instance_value}"

            else:
                instance_value = f"({count_value})"

        return instance_value

    def start_object_value(self):
        """this is the start wrapper value for .object_value
        classes that support it

        :returns: str
        """
        return "<"

    def stop_object_value(self):
        """this is the stop wrapper value for .object_value

        :returns: str
        """
        return ">"

    def start_val_value(self):
        """this is the start wrapper value for .val_value

        :returns: str
        """
        return "<"

    def stop_val_value(self):
        """this is the stop wrapper value for .val_value

        :returns: str
        """
        return ">"

    def empty_value(self):
        """If there is no body then this will be called to generate an
        appropriate summary value

        :returns: str
        """
        if self.SHOW_SIMPLE_EMPTY:
            start_wrapper = self.start_val_value()
            stop_wrapper = self.stop_val_value()
            ret = f"{start_wrapper}{stop_wrapper}"

        else:
            start_wrapper = self.start_object_value()
            stop_wrapper = self.stop_object_value()
            prefix = self.prefix_value()
            ret = f"{start_wrapper}{prefix}{stop_wrapper}"
            ret = Color.color_meta(ret)

        return ret

    def summary_value(self):
        """Prints a short summary of the value

        :returns: str
        """
        if self.has_body():
            start_wrapper = self.start_object_value()
            stop_wrapper = self.stop_object_value()
            prefix = self.prefix_value()
            ret = f"{start_wrapper}{prefix}{stop_wrapper}"
            ret = Color.color_meta(ret)

        else:
            ret = self.empty_value()

        return ret

    def seen_value(self):
        """Shown if this instance has generated an actual .string_value at
        some point"""
        prev_simple_prefix = self.SHOW_SIMPLE_PREFIX
        prev_instance_id = self.SHOW_INSTANCE_ID
        self.SHOW_SIMPLE_PREFIX = False
        self.SHOW_INSTANCE_ID = True

        ret = self.summary_value()

        self.SHOW_SIMPLE_PREFIX = prev_simple_prefix
        self.SHOW_INSTANCE_ID = prev_instance_id

        return ret

    def name_value(self, name):
        """wrapper method that the interface can use to customize the name for
        a given Value instance"""
        return name

    def __repr__(self):
        return self.string_value()

    def __format__(self, format_str):
        return self.string_value()

    def _add_indent(self, val, indent_count):
        """add whitespace to the beginning of each line of val

        :param val: Any, will be converted to string
        :param indent_count: int, how many times to apply indent to each line
        :returns: string, string with indent_count indents at the beginning of
            each line
        """
        if isinstance(val, Value):
            val = val.string_value()

        indent = self.INDENT_STRING
        lines = String(val).splitlines(True)

        return "".join(
            Color.color_indent(indent * indent_count) + line for line in lines
        )

    def _wrap_value(self, start_wrapper, stop_wrapper, value):
        return (
            start_wrapper + "\n"
            + self._add_indent(value, 1) + "\n"
            + stop_wrapper
        )

    def _wrap_val_value(self, value):
        return self._wrap_value(
            self.start_val_value(),
            self.stop_val_value(),
            value
        )

    def _wrap_object_value(self, value):
        return self._wrap_value(
            self.start_object_value(),
            self.stop_object_value(),
            value
        )


class InstanceValue(Value):
    @classmethod
    def is_valid(cls, val):
        is_method = (
            inspect.ismethod(val)
            or inspect.isfunction(val)
            or inspect.ismethoddescriptor(val)
        )

        if is_method:
            return False

        ret = False
        if isinstance(val, getattr(types, "InstanceType", object)):
            # this is an old-school non object inherited class
            ret = True

        else:
            if self.has_attr("__dict__"):
                ret = True
                for a in ["func_name", "im_func"]:
                    if self.has_attr(a):
                        ret = False
                        break

        return ret

    def _get_instance_type(self):
        return "instance"

    def val_value(self):
        return self.object_value()


class DescriptorValue(Value):
    """Handle user defined properties (things like @property)

    https://docs.python.org/3/howto/descriptor.html
    """
    @classmethod
    def is_valid(cls, val):
        is_descriptor = isinstance(val, (property, functools.cached_property))
        if not is_descriptor:
            is_descriptor = True
            for name in ["__get__", "__set__", "__delete__"]:
                try:
                    if not getattr(val, name, None):
                        is_descriptor = False
                        break

                except Exception:
                    is_descriptor = False
                    break

        return is_descriptor

    def string_value(self):
        ret = f"<{self.prefix_value()}>"
        ret = Color.color_meta(ret)
        return ret


class BuiltinValue(InstanceValue):
    """Handles python's builtin types and makes it so object value won't be
    printed out unless it's a child of a built-in type
    """
    SHOW_OBJECT_STRING = False

    @classmethod
    def is_valid(cls, val):
        try:
            return isinstance(val, cls.get_types())

        except (TypeError, NotImplementedError):
            return False

    @classmethod
    def get_types(cls):
        """Returns a tuple of the types this Value class represents

        :returns: tuple[Any]
        """
        return NotImplementedError()


class DictValue(BuiltinValue):
    @classmethod
    def get_types(cls):
        return dict

    def name_callback(self, k):
        quote = self.KEY_QUOTE_CHAR

        if isinstance(k, (bytes, bytearray)):
            ret = "b{}{}{}".format(quote, String(k), quote)

        elif isinstance(k, basestring):
            ret = "{}{}{}".format(quote, String(k), quote)

        else:
            ret = String(k)

        ret = Color.color_key(ret)
        return ret

    def __iter__(self):
        """This iterates a key/val tuple"""
        for v in self.val.items():
            yield v

    def count_value(self):
        try:
            return len(self.val)

        except (TypeError, KeyError, AttributeError) as e:
            logger.debug(e, exc_info=True)
            return 0

    def has_body(self):
        return True if self.val else False

    def start_val_value(self):
        return "{"

    def stop_val_value(self):
        return "}"

    def val_value(self):
        '''turn an iteratable value into a string representation

        :returns: string
        '''
        s_body = []
        depth = self.depth
        ITERATE_LIMIT = self.ITERATE_LIMIT

        try:
            count = 0
            for k, v in self:
                count += 1
                if ITERATE_LIMIT > 0 and count > ITERATE_LIMIT:
                    try:
                        total_rows = len(self.val)

                    except Exception:
                        s_body.append("...")

                    else:
                        s_body.append(
                            "... Truncated {}/{} rows ...".format(
                                total_rows - ITERATE_LIMIT,
                                total_rows
                            )
                        )

                    break

                else:
                    v = self.get_instance(v)
                    k = self.name_callback(k)
                    if k is None:
                        s_body.append(v.string_value())

                    else:
                        s_body.append("{}: {}".format(k, v))

        except Exception as e:
            logger.exception(e)
            s_body.append(
                "... {} Error {} ...".format(e, e.__class__.__name__)
            )

        return ",\n".join(s_body)


class DictProxyValue(DictValue):
    @classmethod
    def get_types(cls):
        return (MappingProxyType,)


class SQLiteRowValue(DictValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, sqlite3.Row)

    def __iter__(self):
        for v in dict(self.val).items():
            yield v


class ListValue(DictValue):
    @classmethod
    def get_types(cls):
        return (list,)

    def name_callback(self, k):
        """Returns just a string representation of the integer k

        if SHOW_SIMPLE is True then this returns None
        """
        if not self.SHOW_SIMPLE:
            return Color.color_key(str(k))

    def start_val_value(self):
        return "["

    def stop_val_value(self):
        return "]"

    def __iter__(self):
        """DictValue iterators (which this extends) need to yield a key/val
        tuple"""
        for v in enumerate(self.val):
            yield v


class ArrayValue(ListValue):
    """Handles array.array instances"""
    @classmethod
    def get_types(cls):
        return (array.array,)

    def classpath_value(self):
        return "{}.{} ({}{}{})".format(
            self.val.__class__.__module__,
            self.val.__class__.__name__,
            self.KEY_QUOTE_CHAR,
            self.val.typecode,
            self.KEY_QUOTE_CHAR
        )


class SetValue(ListValue):
    @classmethod
    def get_types(cls):
        return (set, frozenset, Set)

    def start_val_value(self):
        return "{"

    def stop_val_value(self):
        return "}"

    def empty_value(self):
        return "set()"

    def name_callback(self, k):
        """Having this return a None value means DictValue's key stuff won't
        include a key"""
        return None


class MappingViewValue(SetValue):
    @classmethod
    def get_types(cls):
        return (MappingView,)

    def start_val_value(self):
        return "(["

    def stop_val_value(self):
        return "])"


class TupleValue(ListValue):
    @classmethod
    def get_types(cls):
        return (tuple,)

    def start_val_value(self):
        return "("

    def stop_val_value(self):
        return ")"


class NamedTupleValue(TupleValue):
    SHOW_INSTANCE_TYPE = True

    @classmethod
    def is_valid(cls, val):
        fields = getattr(val, "_fields", None)
        if fields is not None and isinstance(fields, tuple):
            if field := getattr(type(val), fields[0], None):
                return "_tuplegetter" in str(field)

        return False

    def name_callback(self, k):
        if not self.SHOW_SIMPLE:
            name = self.val._fields[k]
            #return super().name_callback(f"{name} ({k})")
            #return super().name_callback(f"{k}. {name}")
            return super().name_callback(f"{k} {name}")

    def _get_instance_type(self):
        return "namedtuple"


class GeneratorValue(TupleValue):
    """Print a generator value

    After years of doing this:

        pout.v(list(func_that_yields()))

    I decided on 2024-9-16 that I might as well print the generator items
    since I almost never want to just see if the value *is* a generator
    """
    @classmethod
    def get_types(cls):
        return (types.GeneratorType, range, map)

    def count_value(self):
        """get how many elements were in the generator, this only works if
        this is called after .val_value"""
        try:
            return self.count

        except AttributeError:
            return None

    def _get_instance_type(self):
        return "generator"

    def __iter__(self):
        self.count = 0
        for i, v in super().__iter__():
            self.count += 1
            yield i, v


class PrimitiveValue(BuiltinValue):
    """Internal class. The base class for the primitives: bool, None, int, 
    and float"""
    SHOW_ALWAYS = True

    def _wrap_val_value(self, value):
        return value if self.SHOW_SIMPLE else super()._wrap_val_value(value)

    def set_instance_attributes(self, **kwargs):
        super().set_instance_attributes(**kwargs)

        if not self.SHOW_INSTANCE_ID and not self.SHOW_INSTANCE_TYPE:
            # don't wrap the value
            self.SHOW_SIMPLE = True
            # get rid of the prefix
            self.SHOW_SIMPLE_PREFIX = True

    def val_color(self, val):
        return val

    def val_value(self):
        return self.val_color(str(self.val))


class NoneValue(PrimitiveValue):
    @classmethod
    def get_types(cls):
        return type(None)

    def val_color(self, val):
        return Color.color(val, bold=True)


class IntValue(PrimitiveValue):
    @classmethod
    def get_types(cls):
        return int

    def val_color(self, val):
        return Color.color_number(val)


class BoolValue(IntValue):
    @classmethod
    def get_types(cls):
        return bool

    def val_color(self, val):
        return Color.color(val, bold=True)


class FloatValue(IntValue):
    @classmethod
    def get_types(cls):
        return float


class StringValue(BuiltinValue):
    SHOW_ALWAYS = True

    @classmethod
    def get_types(cls):
        return str

    def count_value(self):
        return len(self.val)

    def start_val_value(self):
        return Color.color_string("\"")

    def stop_val_value(self):
        return Color.color_string("\"")

    def has_body(self):
        return True if self.val else False

    def val_value(self):
        try:
            s = String(self.val)

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s

    def _wrap_val_value(self, value):
        value = Color.color_string(value)
        if self.SHOW_SIMPLE:
            start_wrapper = self.start_val_value()
            stop_wrapper = self.stop_val_value()
            ret = start_wrapper + value + stop_wrapper

        else:
            ret = super()._wrap_val_value(value)

        #ret = Color.color_string(ret)
        return ret


class StringLikeValue(StringValue):
    """Certain subclasses revert to a string values when they are simplified,
    this is the parent class for those subclasses"""
    @classmethod
    def get_types(cls):
        raise NotImplementedError()

    def count_value(self):
        return len(str(self.val))

    def start_val_value(self):
        if self.SHOW_SIMPLE:
            ret = super().start_val_value()

        else:
            ret = super().start_object_value()

        return ret

    def stop_val_value(self):
        if self.SHOW_SIMPLE:
            ret = super().stop_val_value()

        else:
            ret = super().stop_object_value()

        return ret


class BytesValue(StringValue):
    @classmethod
    def get_types(cls):
        return (bytes, bytearray, memoryview)

    def start_val_value(self):
        return Color.color_string("b\"")

    def val_value(self):
        try:
            s = repr(bytes(self.val))
            if s.startswith("b'"):
                s = s[2:-1] # strip preceding b' and trailing '

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s


class ExceptionValue(InstanceValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, BaseException)


class ModuleValue(InstanceValue):
    @classmethod
    def is_valid(cls, val):
        # this has to go before the object check since a module will pass the
        # object tests
        return isinstance(val, types.ModuleType)

    def _get_instance_type(self):
        return "module"

    def val_value(self):
        s = ""
        val = self.val

        file_path = Path(self._get_src_file(val))
        if file_path:
            s += '{} ({})\n'.format(val.__name__, file_path)

        modules = {}
        funcs = {}
        classes = {}
        properties = {}

        for k, v in self.getmembers():
            if v.typename == "CALLABLE":
                funcs[k] = v

            elif v.typename == "MODULE":
                modules[k] = v

            elif v.typename in ["TYPE", "INSTANCE"]:
                classes[k] = v

            else:
                properties[k] = v

        if modules:
            header = Color.color_header("Modules")
            s += f"\n{header}:\n"
            for k, v in modules.items():
                k = Color.color_attr(k)
                module_path = Path(self._get_src_file(v.val))
                s += self._add_indent("{} ({})".format(k, module_path), 1)
                s += "\n"

        if funcs:
            header = Color.color_header("Functions")
            s += f"\n{header}:\n"

            for k, v in funcs.items():
                k = Color.color_attr(k)
                s += self._add_indent(v, 1)
                s += "\n"

        if classes:
            header = Color.color_header("Classes")
            s += f"\n{header}:\n"

            for k, v in classes.items():
                k = Color.color_attr(k)
                s += self._add_indent(k, 1)
                s += "\n"

        if properties:
            header = Color.color_header("Properties")
            s += f"\n{header}:\n"
            for k, v in properties.items():
                k = Color.color_attr(k)
                s += self._add_indent(k, 1)
                s += "\n"

        return s.strip()


class TypeValue(Value):
    """A class-like value, basically, this is things like a class that hasn't
    been initiated yet

    :Example:
        class Foo(object):
            pass

        Value(Foo).typename # TYPE
        Value(Foo()).typename # INSTANCE
    """
    SHOW_INSTANCE_TYPE = True

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, type)

    def _get_instance_type(self):
        return "class"

    def val_value(self):
        s_body = ""

        info_dict = self._get_info()

        if class_dict := info_dict["class_properties"]:
            header = Color.color_header(
                f"Class Properties ({len(class_dict)})"
            )
            s_body += f"{header}:\n"

            for k, v in OrderedItems(class_dict):
                k = Color.color_attr(k)
                s_var = '{} = '.format(k)
                s_var += v.string_value()

                s_body += self._add_indent(s_var, 1)
                s_body += "\n"

        return s_body.strip()


class RegexValue(InstanceValue):
    @classmethod
    def is_valid(cls, val):
        s = repr(val)
        # SRE_Pattern check might be <py3 only
        return s.startswith("SRE_Pattern") \
            or s.startswith("re.compile(")

    def classpath_value(self):
        return self._get_name(self.val)

    def val_value(self):
        # https://docs.python.org/2/library/re.html#regular-expression-objects
        val = self.val

        flags = {}
        for m, mv in inspect.getmembers(re):
            if not m.startswith("_") and m.isupper() and isinstance(mv, int):
                flags.setdefault(mv, m)
                if len(m) > len(flags[mv]):
                    flags[mv] = m

        s = []

        s.append("pattern: {}".format(val.pattern))
        s.append("groups: {}".format(val.groups))
        # TODO -- we could parse out the groups and put them here, that
        # would be kind of cool

        fv = val.flags
        s.append("flags: {}".format(fv))
        for flag_val, flag_name in flags.items():
            enabled = 1 if fv & flag_val else 0
            s.append(self._add_indent("{}: {}".format(flag_name, enabled), 1))

        return "\n".join(s)


class RegexMatchValue(RegexValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, re.Match)

    def val_value(self):
        body = [
            f"Pattern: {self.val.re.pattern}",
            "",
        ]

        for i, gs in enumerate(self.val.regs, 0):
            start, stop = gs
            match = self.val.string[start:stop]
            body.append(f"Group {i} from {start} to {stop}: {match}")

        return "\n".join(body)


class CallableValue(Value):
    @classmethod
    def is_valid(cls, val):
        """Not sure why class methods pulled from __class__ fail the callable
        check

        * if it has a __call__ and __func__ it's a method
        * if it has a __call__ and __name__ it's a function
        * if it just has a __call__ it's most likely an object instance
        """
        ret = False
        d = dir(val)
        if "__call__" in d:
            ret = "__func__" in d or "__name__" in d

        else:
            # classmethod's have __func__ and __name__ but I'm not sure how 
            # unique that is
            ret = isinstance(val, (
                types.FunctionType,
                types.LambdaType,
                types.MethodWrapperType,
                types.WrapperDescriptorType,
                types.MethodDescriptorType,
                classmethod,
            ))

        return ret

    def string_value(self):
        val = self.val
        typename = "function"
        classpath = ""

        try:
            signature = "{}".format(inspect.signature(val))

        except (TypeError, ValueError):
            signature = "(...)"

        try:
            classpath = self._get_name(val)

        except AttributeError:
            if isinstance(val, staticmethod):
                classpath = self._get_name(val)

            else:
                classpath = "UNKNOWN"

        if isinstance(val, types.MethodType):
            typename = "method"
            classpath = self._get_name(val)

            klass = getattr(val, "__self__", None)
            if klass:
                #classpath = self._get_name(klass)
                classname = getattr(klass, "__name__", "")
                if classname:
                    typename = "classmethod"

        elif isinstance(val, staticmethod):
            typename = "staticmethod"

        else:
            cp = classpath
            parts = classpath.split(":")
            if len(parts) > 1:
                cp = parts[1]

            if "." in cp and not re.search(r">\.[^\.]+$", cp):
                # this could also be something like builtin-method, this is for
                # things like object.__new__ that are technically static
                # methods but look like functions
                if signature.startswith("(self,"):
                    typename = "method"

                else:
                    typename = "staticmethod"

        if self.SHOW_INSTANCE_ID:
            ret = "<{} {}{} at {}>".format(
                typename,
                classpath,
                signature,
                self._get_id(self.val)
            )

        else:
            ret = "<{} {}{}>".format(
                typename,
                classpath,
                signature,
            )

        ret = Color.color_meta(ret)

        return ret


class DatetimeValue(StringLikeValue):
    """
    https://docs.python.org/3/library/datetime.html
    """
    @classmethod
    def get_types(cls):
        return (datetime.datetime, datetime.date)

    def val_value(self):
        if self.SHOW_SIMPLE_VALUE:
            ret = String(self.val)

        else:
            body = [
                String(self.val),
                "",
                f"year: {self.val.year}",
                f"month: {self.val.month}",
                f"day: {self.val.day}",
            ]

            if isinstance(self.val, datetime.datetime):
                body.extend([
                    "",
                    f"hour: {self.val.hour}",
                    f"minute: {self.val.minute}",
                    f"second: {self.val.second}",
                    f"microsecond: {self.val.microsecond}",
                    f"tzinfo: {self.val.tzinfo}",
                ])

            ret = "\n".join(body)

        return ret


class TimedeltaValue(InstanceValue):
    """
    https://docs.python.org/3/library/datetime.html#timedelta-objects
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, datetime.timedelta)

    def val_value(self):
        body = [
            String(self.val),
            "",
            f"days: {self.val.days}",
            f"seconds: {self.val.seconds}",
            f"microseconds: {self.val.microseconds}",
        ]

        return "\n".join(body)


class PathValue(StringLikeValue):
    """
    https://docs.python.org/3/library/pathlib.html
    """
    @classmethod
    def get_types(cls):
        return PurePath

    def val_value(self):
        return String(self.val)


class UUIDValue(StringLikeValue):
    """
    https://docs.python.org/3/library/uuid.html#uuid.UUID
    """
    @classmethod
    def get_types(cls):
        return uuid.UUID

    def val_value(self):
        if self.SHOW_SIMPLE_VALUE:
            ret = String(self.val)

        else:
            ret = "\n".join([
                String(self.val),
                "",
                f"version: {self.val.version}",
                f"hex: {self.val.hex}",
                f"int: {self.val.int}",
                "bytes (big endian): {}".format(
                    BytesValue(self.val.bytes).val_value()
                ),
                "bytes (little endian): {}".format(
                    BytesValue(self.val.bytes_le).val_value()
                ),
            ])

        return ret


class ASTValue(InstanceValue):
    """
    https://docs.python.org/3/library/ast.html#ast.AST
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, ast.AST)

    def val_value(self):
        return ast.dump(self.val, indent=self.INDENT_STRING)

