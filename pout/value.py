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

from .compat import *
from . import environ
from .path import Path
from .utils import String, OrderedItems


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
        self.cutoff_class = Value

        module = sys.modules[__name__]
        for ni, vi in inspect.getmembers(module, inspect.isclass):
            if issubclass(vi, self.cutoff_class):
                self.insert(vi)

    def insert(self, value_class):
        index = len(self)
        for vclass in reversed(inspect.getmro(value_class)):
            if issubclass(vclass, self.cutoff_class):
                index_name = f"{vclass.__module__}.{vclass.__name__}"
                if index_name in self.indexes:
                    index = min(index, self.indexes[index_name])

                else:
                    self.indexes[index_name] = len(self)
                    super().insert(index, vclass)

    def find_class(self, val):
        """Return the *Value class that represents val"""
        for vcls in self:
            if vcls.is_valid(val):
                value_cls = vcls
                break
        return value_cls


class Value(object):
    """Pout is mainly used to print values of different objects, and that
    printing of objects happens in subclasses of this parent class. See the
    .interface.V class for how this is hooked into pout.v

    The most important method in this class is .string_value, check out that
    docblock for the order all the other *_value methods are called
    """
    values_class = Values
    """Holds the class this will use to find the right Value class to return"""

    values_instance = None
    """Holds a cached instance of values_class for faster searches"""

    SHOW_METHODS = False
    """Whether object info includes methods by default"""

    SHOW_MAGIC = False
    """Whether object info includes magic variables/methods by default"""

    SHOW_STR = True
    """Whether object info includes __str__ method output by default"""

    SHOW_ALWAYS = False
    """Whether the object should always be expanded, if False then the first
    time an object is seen it will be expanded, if True then everytime the
    object is seen it will be expanded"""

    SHOW_SIMPLE = False
    """Output the value without all the bells and whistles. You would use this
    flag to get a value that is close to actual python code"""

    @property
    def typename(self):
        s = self.__class__.__name__.replace("Value", "")
        return String(s).snakecase().upper()

    @classmethod
    def find_class(cls, val):
        """Return the *Value class that represents val"""
        if cls is Value:
            if not cls.values_instance:
                cls.values_instance = cls.values_class()

            return cls.values_instance.find_class(val)

        else:
            return cls

    @classmethod
    def is_valid(cls, val):
        return True

    def __new__(cls, val, depth=0, **kwargs):
        """through magic, instantiating an instance will actually create
        subclasses of the different *Value classes, once again, through magic
        """

        # we don't pass in (val, depth) because this just returns the instance
        # and then __init__ is called with those values also
        return super().__new__(cls.find_class(val))

    def __init__(self, val, depth=0, **kwargs):
        self.val = val
        self.depth = depth

        # tracks which instances have been seen so they are only fully expanded
        # the first time they're seen for this call
        self.seen = kwargs.pop("seen", Counter())
        vid = self.id_value()
        self.seen[vid] += 1
        self.seen_first = self.seen[vid] == 1

        self.set_instance_attributes(**kwargs)

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

        self.OBJECT_STR_LIMIT = kwargs.get(
            "object_str_limit",
            environ.OBJECT_STR_LIMIT
        )

        self.ITERATE_LIMIT = kwargs.get(
            "iterate_limit",
            environ.ITERATE_LIMIT
        )

        self.INDENT_STRING = kwargs.get(
            "indent_string",
            kwargs.get("indent", environ.INDENT_STRING)
        )

        self.OBJECT_DEPTH = kwargs.get(
            "object_depth",
            environ.OBJECT_DEPTH
        )

        self.SHORT_PREFIX = kwargs.get(
            "short_prefix",
            environ.SHORT_PREFIX
        )

        self.KEY_QUOTE_CHAR = kwargs.get(
            "key_quote_char",
            environ.KEY_QUOTE_CHAR
        )

        if self.SHOW_SIMPLE:
            self.SHOW_ALWAYS = True
            self.ITERATE_LIMIT = 0

        self.kwargs = kwargs

    def create_instance(self, val, **kwargs):
        """Sometimes while generating the .string_value for .val sub Value
        instances need to be created, they should be created using this method

        :param val: Any, the value to be wrapped in a Value instance
        :param **kwargs:
        :returns: Value, the val wrapped in a Value instance
        """
        kwargs.setdefault("depth", self.depth + 1)
        kwargs.setdefault("seen", self.seen)
        return Value(val, **{**self.kwargs, **kwargs})

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

    def info(self, **kwargs):
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

        SHOW_METHODS = kwargs.get("show_methods", False)
        SHOW_MAGIC = kwargs.get("show_magic", False)

        try:
            for k, v in vars(val).items():
                if SHOW_MAGIC or not self._is_magic(k):
                    v = self.create_instance(v)
                    if v.typename == 'CALLABLE':
                        if SHOW_METHODS:
                            methods_dict[k] = v
                    else:
                        if val is val_class:
                            class_dict[k] = v

                        else:
                            instance_dict[k] = v

        except TypeError as e:
            # Since vars() failed we are going to try and make
            # inspect.getmembers act like vars()
            # Also, I could get a recursion error if I tried to just do
            # inspect.getmembers in certain circumstances, I have no idea why
            for k, v in inspect.getmembers(val):
                v = self.create_instance(v)
                if SHOW_MAGIC or not self._is_magic(k):
                    if v.typename == 'CALLABLE':
                        if SHOW_METHODS:
                            methods_dict[k] = v
                    else:
                        instance_dict[k] = v

        if val_class:
            # build a full class variables dict with the variables of 
            # the full class hierarchy.
            # The reversing makes us go from parent -> child
            for pcls in reversed(inspect.getmro(val_class)):
                for k, v in vars(pcls).items():
                    # filter out anything that's in the instance dict also
                    # since that takes precedence.
                    if k not in instance_dict:
                        v = self.create_instance(v, key=k)
                        if SHOW_MAGIC or not self._is_magic(k):
                            if v.typename == 'CALLABLE':
                                if SHOW_METHODS:
                                    methods_dict[k] = v

                            else:
                                #class_dict.setdefault(k, v)
                                if k in class_dict:
                                    v.seen_first = class_dict[k].seen_first

                                class_dict[k] = v

        return {
            "val_class": val_class,
            "instance_properties": instance_dict,
            "class_properties": class_dict,
            "methods": methods_dict,
        }

    def object_value(self):
        return self._object_value()

    def _object_value(self, **kwargs):
        """Internal method

        This generates all the information about the Value as an object, it
        is used in .info_value() and is broken out so it can be more easily
        used in subclasses

        :param **kwargs:
            - show_magic: bool, True if you want to generate method information,
                default is False
            - show_magic: bool, True if you want to generate magic properties
                and methods values, default is False
        :returns: str, the object information body
        """
        s_body = ""
        src_file = ""

        val = self.val
        depth = self.depth

        SHOW_METHODS = kwargs.get("show_methods",self.SHOW_METHODS)
        SHOW_MAGIC = kwargs.get("show_magic", self.SHOW_MAGIC)
        SHOW_STR = kwargs.get("show_str", self.SHOW_STR)

        info_dict = self.info(
            show_methods=SHOW_METHODS,
            show_magic=SHOW_MAGIC,
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
                        s_body += "{} ({})".format(pname, psrc_file)

                    else:
                        s_body += "{}".format(pname)
                    s_body += "\n"

        if SHOW_STR and hasattr(val, "__str__"):
            s_str = String(val)
            strlen = len(s_str)
            OBJECT_STR_LIMIT = self.OBJECT_STR_LIMIT

            if strlen > OBJECT_STR_LIMIT:
                s_str = s_str.truncate(OBJECT_STR_LIMIT)
                s_str += "... Truncated {}/{} chars ...".format(
                    strlen - OBJECT_STR_LIMIT,
                    strlen
                )

            s_body += "\n__str__ ({}):\n".format(strlen)
            s_body += self._add_indent(s_str, 1)
            s_body += "\n"

        if class_dict := info_dict["class_properties"]:
            s_body += f"\nClass Properties ({len(class_dict)}):\n"

            for k, v in OrderedItems(class_dict):
                s_var = '{} = '.format(k)
                s_var += v.string_value()
                s_body += self._add_indent(s_var, 1)
                s_body += "\n"

        if instance_dict := info_dict["instance_properties"]:
            s_body += f"\nInstance Properties ({len(instance_dict)}):\n"

            for k, v in OrderedItems(instance_dict):
                s_var = '{} = '.format(k)
                s_var += v.string_value()
                s_body += self._add_indent(s_var, 1)
                s_body += "\n"

        if methods_dict := info_dict["methods"]:
            s_body += f"\nMethods ({len(methods_dict)}):\n"

            for k, v in OrderedItems(methods_dict):
                s_body += self._add_indent(v.string_value(), 1)
                s_body += "\n"

        if self.typename == 'EXCEPTION':
            s_body += "\n"
            s_body += "\n".join(
                traceback.format_exception(None, val, val.__traceback__)
            )

        return s_body.strip()

    def info_value(self):
        """If you want to get all the information about the value as an object
        then you can use this method

        :returns: str, the full object information string
        """
        prefix = self.prefix_value()
        start_wrapper = self._add_indent(self.start_object_value(), 1)
        body = self._add_indent(
            self._object_value(show_methods=True, show_magic=True),
            2
        )
        stop_wrapper = self._add_indent(self.stop_object_value(), 1)

        return prefix + "\n" \
            + start_wrapper + "\n" \
            + body + "\n" \
            + stop_wrapper

    def method_value(self):
        return self._getattr(self.val, "__pout__", None)

    def string_value(self):
        """This is the main "value" generation method, this is the method that
        should be called from external sources

        If a value has no body, then it returns a value like this:

            <OBJECT_START_VALUE><PREFIX_VALUE><OBJECT_STOP_VALUE>

        If there is a body, then the value will look more or less like this:

            <PREFIX_VALUE>
                <OBJECT_START_VALUE>
                    <OBJECT_VALUE>
                <OBJECT_STOP_VALUE>
                <START_VALUE>
                    <BODY_VALUE>
                <STOP_VALUE>

        If the value doesn't have a <PREFIX_VALUE> (eg, a primitive like int)
        then it will return basically the string version of that primitive value

        :returns: str, a string suitable to be printed or whatever
        """
        if self.SHOW_SIMPLE:
            prefix = ""

        else:
            prefix = self.prefix_value()

        body = ""
        pout_method = None

        depth = self.depth
        if depth < self.OBJECT_DEPTH or self.SHOW_ALWAYS:
            pout_method = self.method_value()

            if pout_method and callable(pout_method):
                object_body = self.create_instance(pout_method()).body_value()
                value_body = ""

            else:
                pout_method = None
                object_body = self.object_value()
                value_body = self.body_value()

        else:
            object_body = ""
            value_body = ""

        if self.seen_first or self.SHOW_ALWAYS:
            body = self.bodies_value(
                object_body,
                value_body,
                pout_method=pout_method
            )

        if body:
            if prefix: 
                ret = prefix + "\n" + body

            else:
                ret = body

        else:
            if value_body:
                ret = self.summary_value()

            else:
                ret = self.empty_value()

        return ret

    def prefix_value(self):
        """Returns the prefix value

        The prefix value will usually look like this:

            <CLASSPATH> <INSTANCE_VALUE> at <ID_VALUE>

        :returns: str
        """
        if self.SHORT_PREFIX:
            return "{} {}".format(
                self.classpath_value(),
                self.instance_value(),
            ).rstrip()

        else:
            return "{} {} at {}".format(
                self.classpath_value(),
                self.instance_value(),
                self.id_value(),
            )

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

    def instance_value(self, **kwargs):
        """Returns the instance name that's usually used in setting up the 
        prefix value

        :param **kwargs:
            - value: str, the instance value if you want it to be something
                other than the default value
        :returns: str
        """
        if self.SHORT_PREFIX:
            instance_value = ""

        else:
            instance_value = kwargs.get("value", self.typename.lower())

        count_value = self.count_value()
        if count_value is not None:
            if instance_value:
                instance_value = f"({count_value}) {instance_value}"

            else:
                instance_value = f"({count_value})"

        return instance_value

    def id_value(self):
        """Returns the Python memory object id as a nicely formatted string

        :returns: str, .val's id in hex format
        """
        return "0x{:02x}".format(id(self.val))

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

    def start_value(self):
        """this is the start wrapper value for .body_value

        :returns: str
        """
        return "<"

    def stop_value(self):
        """this is the stop wrapper value for .body_value

        :returns: str
        """
        return ">"

    def simple_value(self, object_body, value_body, **kwargs):
        """Internal method called instead of .bodies_value when .SHOW_SIMPLE
        is True.

        see .bodies_value
        """
        if value_body:
            start_wrapper = self.start_value()
            stop_wrapper = self.stop_value()

            body = start_wrapper + "\n" \
                + self._add_indent(value_body, 1) + "\n" \
                + stop_wrapper

        else:
            body = object_body

        return body

    def bodies_value(self, object_body, value_body, **kwargs):
        """Internal method to combine the object and value bodies, called from
        .string_value

        :param object_body: str, the value returned from .object_value
        :param value_body: str, the value returned from .body_value
        :param **kwargs:
            - pout_method: callable, the pout method used to generate
                object_body
        :returns: str, the combined bodies
        """
        body = ""

        if self.SHOW_SIMPLE:
            body = self.simple_value(
                object_body,
                value_body,
                **kwargs
            )

        else:
            if object_body:
                start_wrapper = self.start_object_value()
                stop_wrapper = self.stop_object_value()
                body = self._add_indent(start_wrapper, 1) + "\n" \
                    + self._add_indent(object_body, 2) + "\n" \
                    + self._add_indent(stop_wrapper, 1)

            if value_body:
                start_wrapper = self.start_value()
                stop_wrapper = self.stop_value()

                if body:
                    body += "\n"

                body += self._add_indent(start_wrapper, 1) + "\n" \
                    + self._add_indent(value_body, 2) + "\n" \
                    + self._add_indent(stop_wrapper, 1)

        return body

    def body_value(self):
        """This is the method that will be most important to subclasses since
        the meat of generating the value of whatever value being represented
        will be generated

        :returns: str
        """
        return "{}".format(repr(self.val))

    def empty_value(self):
        """If there is no body then this will be called to generate an
        appropriate summary value

        :returns: str
        """
        return self.summary_value()

    def summary_value(self):
        """Prints a short summary of the value

        :returns: str
        """
        start_wrapper = self.start_object_value()
        stop_wrapper = self.stop_object_value()
        prefix = self.prefix_value()
        return f"{start_wrapper}{prefix}{stop_wrapper}"

    def name_value(self, name):
        """wrapper method that the interface can use to customize the name for a
        given Value instance"""
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

        return String(val).indent(self.INDENT_STRING, indent_count)


class ObjectValue(Value):
    @classmethod
    def is_valid(cls, val):
        is_method = inspect.ismethod(val) \
            or inspect.isfunction(val) \
            or inspect.ismethoddescriptor(val)

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

    def instance_value(self, **kwargs):
        kwargs.setdefault("value", "instance")
        return super().instance_value(**kwargs)

    def body_value(self):
        return ""


class DescriptorValue(ObjectValue):
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
        return f"<{self.prefix_value()}>"


class BuiltinValue(ObjectValue):
    """Handles python's builtin types and makes it so object value won't be
    printed out unless it's a child of a built-in type
    """
    SHOW_STR = False

    SHOW_OBJECT = False
    """turns out, it's actually really annoying to me having extended built-in
    classes print their object value, it's 95% noise to the 5% I would find it
    handy"""

    @classmethod
    def is_valid(cls, val):
        try:
            return isinstance(val, cls.get_types())

        except TypeError:
            return False

    @classmethod
    def get_types(cls):
        """Returns a tuple of the types this Value class represents

        :returns: tuple[Any]
        """
        return NotImplementedError()

    def object_value(self):
        if self.SHOW_OBJECT:
            types = set(self.get_types())
            val_type = type(self.val)
            for t in types:
                try:
                    if isinstance(self.val, t) and val_type not in types:
                        return super().object_value()

                except TypeError:
                    pass

        return ""

    def empty_value(self):
        if self.SHORT_PREFIX or self.SHOW_SIMPLE:
            start = self.start_value()
            stop = self.stop_value()
            return f"{start}{stop}"

        else:
            return super().empty_value()

    def bodies_value(self, object_body, value_body, **kwargs):
        body = ""
        if value_body or kwargs.get("pout_method", None):
            body = super().bodies_value(object_body, value_body)

        return body


class DictValue(BuiltinValue):
    @classmethod
    def get_types(cls):
        return (dict,)

    def name_callback(self, k):
        quote = self.KEY_QUOTE_CHAR

        if isinstance(k, (bytes, bytearray)):
            ret = "b{}{}{}".format(quote, String(k), quote)

        elif isinstance(k, basestring):
            ret = "{}{}{}".format(quote, String(k), quote)

        else:
            ret = String(k)

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

    def start_value(self):
        return "{"

    def stop_value(self):
        return "}"

    def body_value(self):
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
                    v = self.create_instance(v)
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
        """Returns just a string representation of the integer k"""
        if not self.SHOW_SIMPLE:
            return str(k)

    def start_value(self):
        return "["

    def stop_value(self):
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
        return "{}.{}".format(
            self.val.__class__.__module__,
            self.val.__class__.__name__,
        )

    def instance_value(self):
        return f"('{self.val.typecode}') {super().instance_value()}"


class SetValue(ListValue):
    @classmethod
    def get_types(cls):
        return (set, frozenset, Set)

    def start_value(self):
        return "{"

    def stop_value(self):
        return "}"

    def name_callback(self, k):
        """Having this return a None value means DictValue's key stuff won't
        include a key"""
        return None


class MappingViewValue(SetValue):
    @classmethod
    def get_types(cls):
        return (MappingView,)

    def start_value(self):
        return "(["

    def stop_value(self):
        return "])"


class GeneratorValue(SetValue):
    @classmethod
    def get_types(cls):
        return (types.GeneratorType, range, map)

    def instance_value(self, **kwargs):
        kwargs.setdefault("value", "generator")
        return super().instance_value(**kwargs)

    def string_value(self):
        s = self.prefix_value()
        return f"<{s}>"


class TupleValue(ListValue):
    @classmethod
    def get_types(cls):
        return (tuple,)

    def start_value(self):
        return "("

    def stop_value(self):
        return ")"


class PrimitiveValue(BuiltinValue):
    """is the value a built-in primitive type?"""
    SHOW_ALWAYS = True

    @classmethod
    def get_types(cls):
        return (
            type(None),
            bool,
            int,
            float
        )

    def set_instance_attributes(self, **kwargs):
        super().set_instance_attributes(**kwargs)

        if self.SHORT_PREFIX:
            self.SHOW_SIMPLE = True

    def simple_value(self, object_body, value_body, **kwargs):
        if value_body:
            return value_body

        else:
            return object_body

    def body_value(self):
        return str(self.val)


class StringValue(BuiltinValue):
    SHOW_ALWAYS = True

    @classmethod
    def get_types(cls):
        return basestring

    def count_value(self):
        return len(self.val)

    def start_value(self):
        return "\""

    def stop_value(self):
        return "\""

    def body_value(self):
        try:
            s = String(self.val)

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s

    def simple_value(self, object_body, value_body, **kwargs):
        if value_body:
            start_wrapper = self.start_value()
            stop_wrapper = self.stop_value()
            body = start_wrapper + value_body + stop_wrapper

        else:
            body = super().simple_value(object_body, value_body, **kwargs)

        return body


class BinaryValue(StringValue):
    @classmethod
    def get_types(cls):
        return (bytes, bytearray, memoryview)

    def start_value(self):
        return "b\""

    def body_value(self):
        try:
            s = repr(bytes(self.val))
            if s.startswith("b'"):
                s = s[2:-1] # strip preceding b' and trailing '

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s


class ExceptionValue(ObjectValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, BaseException)


class ModuleValue(ObjectValue):
    @classmethod
    def is_valid(cls, val):
        # this has to go before the object check since a module will pass the
        # object tests
        return isinstance(val, types.ModuleType)

    def instance_value(self):
        return "module"

    def object_value(self):
        s = ""
        SHOW_MAGIC = self.SHOW_MAGIC

        val = self.val

        file_path = Path(self._get_src_file(val))
        if file_path:
            s += '{} ({})\n'.format(val.__name__, file_path)

        modules = {}
        funcs = {}
        classes = {}
        properties = {}

        for k, v in inspect.getmembers(val):
            if self._is_magic(k) and not SHOW_MAGIC: continue

            v = Value(v)
            if v.typename == 'CALLABLE':
                funcs[k] = v
            elif v.typename == 'MODULE':
                modules[k] = v
            elif v.typename == 'OBJECT':
                classes[k] = v
            else:
                properties[k] = v

        if modules:
            s += "\nModules:\n"
            for k, v in modules.items():
                module_path = Path(self._get_src_file(v.val))
                s += self._add_indent("{} ({})".format(k, module_path), 1)
                s += "\n"

        if funcs:
            s += "\nFunctions:\n"

            for k, v in funcs.items():
                s += self._add_indent(v, 1)
                s += "\n"

        if classes:
            s += "\nClasses:\n"

            for k, v in classes.items():

                s += self._add_indent(k, 1)
                s += "\n"

                # add methods
                for m, mv in inspect.getmembers(v):
                    mv = Value(mv)
                    if mv.typename == 'CALLABLE':
                        s += self._add_indent(mv, 2)
                        s += "\n"
                s += "\n"

        if properties:
            s += "\nProperties:\n"
            for k, v in properties.items():
                s += self._add_indent(k, 1)
                s += "\n"

        return s


class TypeValue(ObjectValue):
    """A class-like value, basically, this is things like a class that hasn't
    been initiated yet

    :Example:
        class Foo(object):
            pass

        Value(Foo).typename # TYPE
        Value(Foo()).typename # INSTANCE
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, type)

    def method_value(self):
        return self._getattr(self.val, "__pout_class__", None)

    def instance_value(self, **kwargs):
        kwargs.setdefault("value", "class")
        return super().instance_value(**kwargs)

    def object_value(self):
        s_body = ""

        SHOW_MAGIC = self.SHOW_MAGIC
        info_dict = self.info(show_magic=SHOW_MAGIC)

        if class_dict := info_dict["class_properties"]:
            s_body += f"Class Properties ({len(class_dict)}):\n"

            for k, v in OrderedItems(class_dict):
                s_var = '{} = '.format(k)
                s_var += v.string_value()

                s_body += self._add_indent(s_var, 1)
                s_body += "\n"

        return s_body


class RegexValue(ObjectValue):
    @classmethod
    def is_valid(cls, val):
        s = repr(val)
        # SRE_Pattern check might be <py3 only
        return "SRE_Pattern" in repr(val) \
            or "re.compile" in s

    def classpath_value(self):
        return self._get_name(self.val)

    def object_value(self):
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

    def object_value(self):
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

        return "<{} {}{} at {}>".format(
            typename,
            classpath,
            signature,
            self.id_value()
        )


class DatetimeValue(ObjectValue):
    """
    https://docs.python.org/3/library/datetime.html
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, (datetime.datetime, datetime.date))

    def object_value(self):
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

        return "\n".join(body)


class TimedeltaValue(ObjectValue):
    """
    https://docs.python.org/3/library/datetime.html#timedelta-objects
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, datetime.timedelta)

    def object_value(self):
        body = [
            String(self.val),
            "",
            f"days: {self.val.days}",
            f"seconds: {self.val.seconds}",
            f"microseconds: {self.val.microseconds}",
        ]

        return "\n".join(body)


class PathValue(ObjectValue):
    """
    https://docs.python.org/3/library/pathlib.html
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, PurePath)

    def object_value(self):
        return String(self.val)


class UUIDValue(ObjectValue):
    """
    https://docs.python.org/3/library/uuid.html#uuid.UUID
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, uuid.UUID)

    def object_value(self):
        return "\n".join([
            String(self.val),
            "",
            f"version: {self.val.version}",
            f"hex: {self.val.hex}",
            f"int: {self.val.int}",
            "bytes (big endian): {}".format(
                BinaryValue(self.val.bytes).body_value()
            ),
            "bytes (little endian): {}".format(
                BinaryValue(self.val.bytes_le).body_value()
            ),
        ])

