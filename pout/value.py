# -*- coding: utf-8 -*-
"""
The Value classes in this file manage taking any python object and converting it
into a string that can be printed out

The Inspect class identifies what the object actually is
"""
from __future__ import unicode_literals, division, print_function, absolute_import
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
from collections import defaultdict
import functools
import sqlite3
import datetime

from .compat import *
from . import environ
from .path import Path
from .utils import String, Bytes, OrderedItems


logger = logging.getLogger(__name__)


class Values(list):
    """We want to keep a particular order of the Value subclasses to make sure
    that certain classes are checked before others, this is because certain values
    might actually resolve into 2 different sub values, so order becomes important

    this class maintains that order, basically, it makes sure all subclasses get
    checked before the parent class, so if you want your CustomValue to evaluate
    before DictValue, you would just have CustomValue extend DictValue
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
    """Pout is mainly used to print values of different objects, and that printing
    of objects happens in subclasses of this parent class. See the .interface.V
    class for how this is hooked into pout.v
    """
    values_class = Values
    """Holds the class this will use to find the right Value class to return"""

    values_instance = None
    """Holds a cached instance of values_class for faster searches"""

    @property
    def typename(self):
        s = self.__class__.__name__.replace("Value", "")
        return String(s).snakecase().upper()

    @property
    def instancename(self):
        return self.typename.lower()

    @property
    def raw(self):
        return self.val
    value = raw

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
        subclasses of the different *Value classes, once again, through magic"""

        # we don't pass in (val, depth) because this just returns the instance
        # and then __init__ is called with those values also
        return super().__new__(cls.find_class(val))

    def __init__(self, val, depth=0, **kwargs):
        self.val = val
        self.depth = depth
        self.indent = 1 if depth > 0 else 0
        self.kwargs = kwargs

    def string_value(self):
        return "{}".format(repr(self.val))

    def bytes_value(self):
        s = self.string_value()
        return Bytes(s)

    def name_value(self, name):
        """wrapper method that the interface can use to customize the name for a
        given Value instance"""
        return name

    def __repr__(self):
        s = self.string_value()
        return s

    def __format__(self, format_str):
        return self.string_value() if isinstance(format_str, String.types) else self.bytes_value()

    def _add_indent(self, val, indent_count):
        '''
        add whitespace to the beginning of each line of val

        link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        val -- string
        indent -- integer -- how much whitespace we want in front of each line of val

        return -- string -- val with more whitespace
        '''
        INDENT_STRING = self.kwargs.get("indent_string", environ.INDENT_STRING)

        if isinstance(val, Value):
            val = val.string_value()

        return String(val).indent(indent_count, INDENT_STRING)

    def _get_unicode(self, arg):
        '''
        make sure arg is a unicode string

        arg -- mixed -- arg can be anything
        return -- unicode -- a u'' string will always be returned
        '''
        return String(arg)

    def get_id(self):
        """Return .val's id in hex format"""
        return "0x{:02x}".format(id(self.val))


class ObjectValue(Value):
    @property
    def instancename(self):
        return "instance"

    @classmethod
    def is_valid(cls, val):
        if inspect.ismethod(val) or inspect.isfunction(val) or inspect.ismethoddescriptor(val):
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

    def _is_magic(self, name):
        '''
        return true if the name is __name__

        since -- 7-10-12

        name -- string -- the name to check

        return -- boolean
        '''
        #return (name[:2] == u'__' and name[-2:] == u'__')
        return name.startswith('__') and name.endswith('__')

    def _getattr(self, val, key, default_val):
        """wrapper around global getattr(...) method that suppresses any exception raised"""
        try:
            ret = getattr(val, key, default_val)

        except Exception as e:
            logger.exception(e)
            ret = default_val

        return ret

    def _get_name(self, val, src_file, default='Unknown'):
        '''
        get the full namespaced (module + class) name of the val object

        since -- 6-28-12

        val -- mixed -- the value (everything is an object) object
        default -- string -- the default name if a decent name can't be found programmatically

        return -- string -- the full.module.Name
        '''
        module_name = ''
        if src_file:
            module_name = '{}.'.format(self._getattr(val, '__module__', default)).lstrip('.')

        class_name = self._getattr(val, '__name__', None)
        if not class_name:
            class_name = default
            cls = self._getattr(val, '__class__', None)
            if cls:
                class_name = self._getattr(cls, '__name__', default)

        full_name = "{}{}".format(module_name, class_name)

        return full_name

    def _get_src_file(self, val, default='Unknown'):
        '''
        return the source file path

        since -- 7-19-12

        val -- mixed -- the value whose path you want

        return -- string -- the path, or something like 'Unknown' if you can't find the path
        '''
        path = default

        try:
            # http://stackoverflow.com/questions/6761337/inspect-getfile-vs-inspect-getsourcefile
            # first try and get the actual source file
            source_file = inspect.getsourcefile(val)
            if not source_file:
                # get the raw file since val doesn't have a source file (could be a .pyc or .so file)
                source_file = inspect.getfile(val)

            if source_file:
                path = os.path.realpath(source_file)

        except TypeError as e:
            path = default

        return path

    def prefix_value(self):
        #full_name = self._get_name(val, src_file=src_file) # full classpath
        full_name = self._get_name(self.val, src_file="") # just the classname
        v = Value(self.val)
        return "{} {} at 0x{:02x}".format(full_name, v.instancename, id(self.val))

    def info(self):
        """Gathers all the information about this object

        each dict's key is the name of the property and the value is the actual
        property

        :returns: tuple, (class_name, instance_dict, class_dict, methods_dict
        """
        val = self.val
        depth = self.depth
        val_class = self._getattr(val, "__class__", None)
        class_dict = {}
        methods_dict = {}
        instance_dict = {}

        SHOW_METHODS = self.kwargs.get("show_methods", False)
        SHOW_MAGIC = self.kwargs.get("show_magic", False)

        try:
            for k, v in vars(val).items():
                if SHOW_MAGIC or not self._is_magic(k):
                    v = Value(v, depth+1)
                    if v.typename == 'CALLABLE':
                        if SHOW_METHODS:
                            methods_dict[k] = v
                    else:
                        instance_dict[k] = v

            #instance_dict = {k: Value(v, depth+1) for k, v in vars(val).items()}

        except TypeError as e:
            # Since vars() failed we are going to try and make inspect.getmembers
            # act like vars()
            # Also, I could get a recursion error if I tried to just do
            # inspect.getmembers in certain circumstances, I have no idea why
            for k, v in inspect.getmembers(val):
                v = Value(v, depth+1)
                if SHOW_MAGIC or not self._is_magic(k):
                    if v.typename == 'CALLABLE':
                        if SHOW_METHODS:
                            methods_dict[k] = v
                    else:
                        instance_dict[k] = v

        if val_class:
            # build a full class variables dict with the variables of 
            # the full class hierarchy
            for pcls in reversed(inspect.getmro(val_class)):
                for k, v in vars(pcls).items():
                    # filter out anything that's in the instance dict also
                    # since that takes precedence.
                    if k not in instance_dict:
                        v = Value(v, depth+1)
                        if SHOW_MAGIC or not self._is_magic(k):
                            if v.typename == 'CALLABLE':
                                if SHOW_METHODS:
                                    methods_dict[k] = v
                            else:
                                class_dict[k] = v

        return val_class, instance_dict, class_dict, methods_dict

    def string_value(self):
        val = self.val
        depth = self.depth
        indent = self.indent

        OBJECT_DEPTH = self.kwargs.get("object_depth", environ.OBJECT_DEPTH)
        val_class, instance_dict, class_dict, methods_dict = self.info()

        src_file = ""
        if val_class:
            src_file = self._get_src_file(val_class, default="")

        s = self.prefix_value()
        s_body = ""

        pout_method = self._getattr(val, "__pout__", None)
        if pout_method and callable(pout_method):
            v = Value(pout_method())
            s_body = v.string_value()

        else:
            if depth < OBJECT_DEPTH:
                if val_class:
                    pclses = inspect.getmro(val_class)
                    if pclses:
                        s_body += "\n"
                        for pcls in pclses:
                            psrc_file = self._get_src_file(pcls, default="")
                            if psrc_file:
                                psrc_file = Path(psrc_file)
                            pname = self._get_name(pcls, src_file=psrc_file)
                            if psrc_file:
                                s_body += "{} ({})".format(pname, psrc_file)
                            else:
                                s_body += "{}".format(pname)
                            s_body += "\n"

                if hasattr(val, '__str__'):
                    s_body += "\n__str__:\n"
                    s_body += self._add_indent(String(val), 1)

                    s_body += "\n"

                if class_dict:
                    s_body += f"\nClass Properties ({len(class_dict)}):\n"

                    for k, v in OrderedItems(class_dict):
                        s_var = '{} = '.format(k)
                        s_var += v.string_value()
                        s_body += self._add_indent(s_var, 1)
                        s_body += "\n"

                if instance_dict:
                    s_body += f"\nInstance Properties ({len(instance_dict)}):\n"

                    for k, v in OrderedItems(instance_dict):
                        s_var = '{} = '.format(k)
                        s_var += v.string_value()
                        s_body += self._add_indent(s_var, 1)
                        s_body += "\n"

                if methods_dict:
                    s_body += f"\nMethods ({len(methods_dict)}):\n"

                    for k, v in OrderedItems(methods_dict):
                        s_body += self._add_indent(v.string_value(), 1)
                        s_body += "\n"

                if self.typename == 'EXCEPTION':
                    s_body += "\n"
                    s_body += "\n".join(traceback.format_exception(None, val, val.__traceback__))

        return self.finalize_value(body=s_body, prefix=s)

    def finalize_value(self, body, prefix="", start_wrapper="<", stop_wrapper=">"):
        prefix = prefix or self.prefix_value()
        if body:
            indent = self.indent
            start_wrapper = self._add_indent(f"\n{start_wrapper}", indent) + "\n"
            body = self._add_indent(body.strip(), indent + 1)
            stop_wrapper = self._add_indent(f"\n{stop_wrapper}", indent)
            ret = prefix + start_wrapper + body + stop_wrapper

        else:
            ret = f"{start_wrapper}{prefix}{stop_wrapper}"
        return ret


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


class PrimitiveValue(Value):
    @classmethod
    def is_valid(cls, val):
        """is the value a built-in type?"""
        return isinstance(
            val,
            (
                type(None),
                bool,
                int,
                float
            )
        )


class DictValue(ObjectValue):
    left_paren = "{"
    right_paren = "}"

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, dict)

    def name_callback(self, k):
        if isinstance(k, (bytes, bytearray)):
            ret = "b'{}'".format(self._get_unicode(k))
        elif isinstance(k, basestring):
            ret = "'{}'".format(self._get_unicode(k))
        else:
            ret = self._get_unicode(k)
        return ret

    def __iter__(self):
        for v in self.val.items():
            yield v

    def prefix_value(self):
        try:
            count = f" ({len(self.val)}) "

        except (TypeError, KeyError, AttributeError) as e:
            logger.debug(e, exc_info=True)
            count = " "

        full_name = self._get_name(self.val, src_file="") # just the classname
        return "{}{}instance at 0x{:02x}".format(full_name, count, id(self.val))

    def _str_iterator(self):
        '''
        turn an iteratable value into a string representation

        :returns: string
        '''
        depth = self.depth
        indent = self.indent
        iterator = self
        name_callback = self.name_callback
        left_paren = self.left_paren
        right_paren = self.right_paren
        prefix = f"{self.prefix_value()}\n"
        ITERATE_LIMIT = self.kwargs.get("iterate_limit", environ.ITERATE_LIMIT)

        s = []
        s.append('{}{}'.format(prefix, self._add_indent(left_paren, indent)))

        s_body = []

        try:
            count = 0
            for k, v in iterator:
                count += 1
                if count > ITERATE_LIMIT:
                    try:
                        total_rows = len(self.val)
                    except Exception:
                        s_body.append("...")
                    else:
                        s_body.append("... Truncated {}/{} rows ...".format(total_rows - ITERATE_LIMIT, total_rows))

                    break

                k = k if name_callback is None else name_callback(k)

                v = Value(v, depth+1)
                if k is None:
                    s_body.append("{}".format(v))
                else:
                    s_body.append("{}: {}".format(k, v))

        except Exception as e:
            s_body.append("... {} Error {} ...".format(e, e.__class__.__name__))

        s_body = ",\n".join(s_body)
        s_body = self._add_indent(s_body, indent + 1)

        s.append(s_body)
        s.append("{}".format(self._add_indent(right_paren, indent)))

        return "\n".join(s)

    def string_value(self):
        val = self.val
        OBJECT_DEPTH = self.kwargs.get("object_depth", environ.OBJECT_DEPTH)
        if len(val) > 0:
            pout_method = self._getattr(val, "__pout__", None)
            if pout_method and callable(pout_method):
                v = Value(pout_method())
                s_body = v.string_value()
                s = self.finalize_value(s_body, start_wrapper=self.left_paren, stop_wrapper=self.right_paren)

            else:

                if self.depth < OBJECT_DEPTH:
                    s = self._str_iterator()

                else:
                    s = self.finalize_value(None, prefix=self.prefix_value())
        else:
            s = "{}{}".format(self.left_paren, self.right_paren)

        return s


class DictProxyValue(DictValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, MappingProxyType)


class SQLiteRowValue(DictValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, sqlite3.Row)

    def __iter__(self):
        for v in dict(self.val).items():
            yield v


class ListValue(DictValue):
    left_paren = '['
    right_paren = ']'
    name_callback = None

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, list)

    def __iter__(self):
        for v in enumerate(self.val):
            yield v


class MappingViewValue(ListValue):
    left_paren = '(['
    right_paren = '])'

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, MappingView)

    def __iter__(self):
        for v in enumerate(self.val):
            yield v


class ArrayValue(ListValue):
    """Handles array.array instances"""
    @property
    def left_paren(self):
        return "{}.{}('{}', [".format(
            self.val.__class__.__module__,
            self.val.__class__.__name__,
            self.val.typecode
        )

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, array.array)


class SetValue(ListValue):
    left_paren = '{'
    right_paren = '}'

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, (set, frozenset, Set)) and not isinstance(val, MappingView)

    def name_callback(self, k):
        return None


class GeneratorValue(SetValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, (types.GeneratorType, range, map))

    def string_value(self):
        s = self.prefix_value()
        return f"<{s}>"


class TupleValue(ListValue):
    left_paren = '('
    right_paren = ')'

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, tuple)


class StringValue(ObjectValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, basestring)

    def string_value(self):
        val = self.val
        try:
            s = '"{}"'.format(String(val))

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s

    def name_value(self, name):
        return f"{name} ({len(self.val)})" if name else name


class BinaryValue(StringValue):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, (bytes, bytearray, memoryview))

    def string_value(self):
        val = self.val
        try:
            s = repr(bytes(val))

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
        # this has to go before the object check since a module will pass the object tests
        return isinstance(val, types.ModuleType)

    def prefix_value(self):
        full_name = self._get_name(self.val, src_file="")
        return "{} module at 0x{:02x}".format(full_name, id(self.val))

    def string_value(self):
        s = ""
        depth = self.depth
        OBJECT_DEPTH = self.kwargs.get("object_depth", environ.OBJECT_DEPTH)
        SHOW_MAGIC = self.kwargs.get("show_magic", False)

        if depth < OBJECT_DEPTH:
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

                #pout2.v('%s %s: %s' % (k, vt, repr(v)))

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

        return self.finalize_value(body=s)


class TypeValue(ObjectValue):
    """A class-like value, basically, this is things like a class that hasn't
    been initiated yet

    :Example:
        class Foo(object):
            pass

        Value(Foo).typename # TYPE
        Value(Foo()).typename # INSTANCE
    """
    @property
    def instancename(self):
        return "class"

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, type)

    def string_value(self):
        depth = self.depth
        OBJECT_DEPTH = self.kwargs.get("object_depth", environ.OBJECT_DEPTH)
        SHOW_MAGIC = self.kwargs.get("show_magic", False)

        s_body = ""

        if depth < OBJECT_DEPTH:
            val_class, instance_dict, class_dict, methods_dict = self.info()
            instance_dict = {k:v for k, v in instance_dict.items() if not self._is_magic(k)}
            if instance_dict:
                s_body += f"Properties ({len(instance_dict)}):\n"

                for k, v in OrderedItems(instance_dict):
                    s_var = '{} = '.format(k)
                    s_var += v.string_value()
                    s_body += self._add_indent(s_var, 1)
                    s_body += "\n"

        return self.finalize_value(body=s_body)


class RegexMatchValue(ObjectValue):
    def _get_name(self, *args, **kwargs):
        return "re.Match"

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, re.Match)

    def string_value(self):
        #print(dir(self.val))
        #match = self.val.string[self.val.start():self.val.end()]
        body = [
            f"Pattern: {self.val.re.pattern}",
            "",
            #f"group 0: {match}",
        ]

        for i, gs in enumerate(self.val.regs, 0):
            start, stop = gs
            match = self.val.string[start:stop]
            body.append(f"Group {i} from {start} to {stop}: {match}")

        #for i, g in enumerate(self.val.groups(), 1):
        #    body.append(f"Group {i}: {g}")

        return self.finalize_value(body="\n".join(body))


class RegexValue(Value):
    @classmethod
    def is_valid(cls, val):
        return "SRE_Pattern" in repr(val)

    def string_value(self):
        # https://docs.python.org/2/library/re.html#regular-expression-objects
        val = self.val

        flags = {}
        for m, mv in inspect.getmembers(re):
            if not m.startswith("_") and m.isupper() and isinstance(mv, int):
                flags.setdefault(mv, m)
                if len(m) > len(flags[mv]):
                    flags[mv] = m

        s = ["Compiled Regex"]
        s.append("<")

        s.append(self._add_indent("pattern: {}".format(val.pattern), 1))
        s.append(self._add_indent("groups: {}".format(val.groups), 1))
        # TODO -- we could parse out the groups and put them here, that
        # would be kind of cool

        fv = val.flags
        #s.append(self._add_indent("flags", 1))
        s.append(self._add_indent("flags: {}".format(fv), 1))
        for flag_val, flag_name in flags.items():
            enabled = 1 if fv & flag_val else 0
            s.append(self._add_indent("{}: {}".format(flag_name, enabled), 2))

        s.append(">")

        s = "\n".join(s)
        return s


class CallableValue(Value):
    @classmethod
    def is_valid(cls, val):
        # not sure why class methods pulled from __class__ fail the callable check

        # if it has a __call__ and __func__ it's a method
        # if it has a __call__ and __name__ it's a function
        # if it just has a __call__ it's most likely an object instance
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
        try:
            func_args = "{}".format(inspect.signature(val))

        except (TypeError, ValueError):
            func_args = "(...)"

        try:
            signature = "{}{}".format(val.__name__, func_args)

        except AttributeError:
            if isinstance(val, staticmethod):
                signature = "{}{}".format(val.__func__.__name__, func_args)

            else:
                signature = "UNKNOWN{}".format(func_args)

        if isinstance(val, types.MethodType):
            typename = "method"
            classpath = ""
            klass = getattr(val, "__self__", None)
            if klass:
                modpath = getattr(klass, "__module__", "")
                classname = getattr(klass, "__name__", "")
                if not classname:
                    classpath = f"{modpath}.{klass.__class__.__name__}"

                else:
                    typename = "classmethod"
                    classpath = f"{modpath}.{klass.__name__}"

                if classpath:
                    classpath += "."

            ret = "<{} {}{} at {}>".format(typename, classpath, signature, self.get_id())

        elif isinstance(val, staticmethod):
            ret = "<staticmethod {} at {}>".format(signature, self.get_id())

        else:
            modpath = getattr(val, "__module__", "")
            if modpath and not isinstance(modpath, str):
                modpath = modpath.__name__

            if modpath:
                modpath += "."

            ret = "<function {}{} at {}>".format(modpath, signature, self.get_id())

        return ret


class DatetimeValue(ObjectValue):
    """
    https://docs.python.org/3/library/datetime.html
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, (datetime.datetime, datetime.date))

    def string_value(self):
        body = "\n".join([
            String(self.val),
            "",
            f"year: {self.val.year}",
            f"month: {self.val.month}",
            f"day: {self.val.day}",
        ])

        if isinstance(self.val, datetime.datetime):
            body += "\n".join([
                "",
                f"hour: {self.val.hour}",
                f"minute: {self.val.minute}",
                f"second: {self.val.second}",
                f"microsecond: {self.val.microsecond}",
                f"tzinfo: {self.val.tzinfo}",
            ])

        return self.finalize_value(body)


class PathValue(ObjectValue):
    """
    https://docs.python.org/3/library/pathlib.html
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, PurePath)

    def string_value(self):
        body = String(self.val)
        return self.finalize_value(body)

