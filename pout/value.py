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

from .compat import *
from . import environ
from .path import Path
from .utils import String, Bytes


logger = logging.getLogger(__name__)


class Values(list):
    def __init__(self):
        super().__init__()

        self.indexes = {}
        self.cutoff_class = Value

        module = sys.modules[__name__]
        for ni, vi in inspect.getmembers(module, inspect.isclass):
            if issubclass(vi, self.cutoff_class):
                self.insert(vi)

        #print(self)

    def insert(self, value_class):
        index = len(self)
        #print("================================\n")
        for vclass in reversed(inspect.getmro(value_class)):
            if issubclass(vclass, self.cutoff_class):
                #print(vclass)
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

    values_class = Values
    """Holds the class this will use to find the right Value class to return"""

    values_instance = None
    """Holds a cached instance of value_class for faster searches"""

    @property
    def typename(self):
        s = self.__class__.__name__.replace("Value", "")
        return String(s).snakecase().upper()

    @property
    def raw(self):
        return self.val
    value = raw

    @classmethod
    def find_class(cls, val):
        """Return the *Value class that represents val"""
        if not cls.values_instance:
            cls.values_instance = cls.values_class()
        return cls.values_instance.find_class(val)

    @classmethod
    def is_valid(cls, val):
        return True

    def __new__(cls, val, depth=0):
        """through magic, instantiating an instance will actually create
        subclasses of the different *Value classes, once again, through magic"""

        # we don't pass in (val, depth) because this just returns the instance
        # and then __init__ is called with those values also
        return super().__new__(cls.find_class(val))

    def __init__(self, val, depth=0):
        self.val = val
        self.depth = depth
        self.indent = 1 if depth > 0 else 0

    def string_value(self):
        return "{}".format(repr(self.val))
    string_val = string_value

    def bytes_value(self):
        s = self.string_value()
        return Bytes(s)
    bytes_val = bytes_value

    def __repr__(self):
        s = self.string_value()
        return s

    def __format__(self, format_str):
        return self.string_value() if isinstance(format_str, String.types) else self.bytes_value()

    def info(self):
        methods = []
        properties = []
        for ni, vi in inspect.getmembers(self.val):
#             i = self.inspect_class(vi)
            #print(ni, i.typename, type(vi))
            #print(ni, type(vi))
            if TypeValue.is_valid(vi):
                properties.append((ni, vi))
            elif CallableValue.is_valid(vi):
                methods.append((ni, vi))
            else:
                properties.append((ni, vi))

#             if i.is_type():
#                 properties.append((ni, vi))
#             elif i.is_callable():
#                 methods.append((ni, vi))
#             else:
#                 properties.append((ni, vi))

        full_info = repr(self)
        info = "MEMBERS:\n"

        info += self._add_indent("Methods:", 1)
        info += "\n"
        for name, vi in methods:
            info += self._add_indent(Value(vi), 2)
            info += "\n"

        info += self._add_indent("Properties:", 1)
        info += "\n"
        for name, vi in properties:
            info += self._add_indent(name, 2)
            info += "\n"


        full_info = full_info.rstrip().rstrip('>')
        full_info += "\n"
        full_info += self._add_indent(info.strip(), 1)
        full_info += "\n>"
        full_info += "\n\n"
        return full_info

    def _str_iterator(self, iterator, name_callback=None, prefix="\n", left_paren='[', right_paren=']', depth=0):
        '''
        turn an iteratable value into a string representation

        iterator -- iterator -- the value to be iterated through
        name_callback -- callback -- if not None, a function that will take the key of each iteration
        prefix -- string -- what will be prepended to the generated value
        left_paren -- string -- what will open the generated value
        right_paren -- string -- what will close the generated value
        depth -- integer -- how deep into recursion we are

        return -- string
        '''
        indent = 1 if depth > 0 else 0

        s = []
        s.append('{}{}'.format(prefix, self._add_indent(left_paren, indent)))

        s_body = []

        try:
            for k, v in iterator:
                k = k if name_callback is None else name_callback(k)
                v = Value(v, depth+1)
                try:
                    # TODO -- right here we should check some flag or something to
                    # see if lists should render objects
                    if k is None:
                        s_body.append("{}".format(v))
                    else:
                        s_body.append("{}: {}".format(k, v))

                except RuntimeError as e:
                    # I've never gotten this to work
                    s_body.append("{}: ... Recursion error ...".format(k))

                except UnicodeError as e:
                    print(v.val)
                    print(type(v.val))

        except Exception as e:
            s_body.append("... {} Error {} ...".format(e, e.__class__.__name__))

        s_body = ",\n".join(s_body)
        s_body = self._add_indent(s_body, indent + 1)

        s.append(s_body)
        s.append("{}".format(self._add_indent(right_paren, indent)))

        return "\n".join(s)

    def _add_indent(self, val, indent_count):
        '''
        add whitespace to the beginning of each line of val

        link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        val -- string
        indent -- integer -- how much whitespace we want in front of each line of val

        return -- string -- val with more whitespace
        '''
        if isinstance(val, Value):
            val = val.string_value()

        return String(val).indent(indent_count)

    def _get_unicode(self, arg):
        '''
        make sure arg is a unicode string

        arg -- mixed -- arg can be anything
        return -- unicode -- a u'' string will always be returned
        '''
        return String(arg)


class ObjectValue(Value):
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
        return "{} instance at 0x{:02x}".format(full_name, id(self.val))

    def string_value(self):
        val = self.val
        depth = self.depth
        indent = self.indent

        src_file = ""
        val_class = self._getattr(val, "__class__", None)
        if val_class:
            src_file = self._get_src_file(val_class, default="")

        try:
            instance_dict = {k: Value(v, depth+1) for k, v in vars(val).items()}

        except TypeError as e:
            # using vars(val) will give the instance's __dict__, which doesn't
            # include methods because those are set on the instance's __class__.
            # Since vars() failed we are going to try and make inspect.getmembers
            # act like vars()
            instance_dict = {}
            for k, v in inspect.getmembers(val):
                if not self._is_magic(k):
                    v = Value(v, depth+1)
                    if v.typename != 'CALLABLE':
                        instance_dict[k] = v

        s = self.prefix_value()
        s_body = ""

        pout_method = self._getattr(val, "__pout__", None)
        if pout_method and callable(pout_method):
            v = Value(pout_method())
            s_body = v.string_value()

        else:
            if depth < environ.OBJECT_DEPTH:
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

                if val_class:

                    # build a full class variables dict with the variables of 
                    # the full class hierarchy
                    class_dict = {}
                    for pcls in reversed(inspect.getmro(val_class)):
                        for k, v in vars(pcls).items():
                            # filter out anything that's in the instance dict also
                            # since that takes precedence.
                            # We also don't want any __blah__ type values
                            if k not in instance_dict and not self._is_magic(k):
                                class_dict[k] = Value(v, depth+1)

                    if class_dict:

                        s_body += "\nClass Properties:\n"

                        for k, v in class_dict.items():
                            if v.typename != 'CALLABLE':

                                s_var = '{} = '.format(k)
                                s_var += v.string_value()
                                s_body += self._add_indent(s_var, 1)
                                s_body += "\n"

                if instance_dict:
                    s_body += "\nInstance Properties:\n"

                    for k, v in instance_dict.items():
                        s_var = '{} = '.format(k)
                        s_var += v.string_value()

                        s_body += self._add_indent(s_var, 1)
                        s_body += "\n"

                if self.typename == 'EXCEPTION':
                    s_body += "\n"
                    s_body += "\n".join(traceback.format_exception(None, val, val.__traceback__))

            else:
                s_body = String(repr(val))

        return self.finalize_value(s, s_body)

    def finalize_value(self, prefix, body, start_wrapper="<", stop_wrapper=">"):
        indent = self.indent
        start_wrapper = self._add_indent(f"\n{start_wrapper}", indent) + "\n"
        body = self._add_indent(body.strip(), indent + 1)
        stop_wrapper = self._add_indent(f"\n{stop_wrapper}", indent)
        return prefix + start_wrapper + body + stop_wrapper


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
    prefix = "\n"

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, dict)

    def name_callback(self, k):
        if isinstance(k, basestring):
            ret = "'{}'".format(self._get_unicode(k))
        else:
            ret = self._get_unicode(k)
        return ret

    def __iter__(self):
        for v in self.val.items():
            yield v

    def string_value(self):
        val = self.val
        if len(val) > 0:

            s = self._str_iterator(
                iterator=self, 
                name_callback=self.name_callback,
                left_paren=self.left_paren,
                right_paren=self.right_paren,
                prefix=self.prefix,
                depth=self.depth,
            )

        else:
            s = "{}{}".format(self.left_paren, self.right_paren)

        return s


class DictProxyValue(DictValue):
    left_paren = 'dict_proxy({'
    right_paren = '})'
    prefix = ""

    @classmethod
    def is_valid(cls, val):
        return isinstance(val, MappingProxyType)


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

    @property
    def left_paren(self):
        return "{}([".format(
            self.val.__class__.__name__,
        )

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

    def string_value(self):
        val = self.val
        file_path = Path(self._get_src_file(val))
        s = '{} module ({})\n'.format(val.__name__, file_path)

        s += "\nid: {}\n".format(id(val))

        modules = {}
        funcs = {}
        classes = {}
        properties = {}

        for k, v in inspect.getmembers(val):

            # canary, ignore magic values
            if self._is_magic(k): continue

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

                #func_args = inspect.formatargspec(*inspect.getfullargspec(v))
                #pout2.v(func_args)

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


class TypeValue(Value):
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, type)

    def string_value(self):
        return '{}'.format(self.val)


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

        return ret

    def string_value(self):
        val = self.val
        try:
            if is_py2:
                func_args = inspect.formatargspec(*inspect.getfullargspec(val))
            else:
                func_args = "{}".format(inspect.signature(val))
        except (TypeError, ValueError):
            func_args = "(...)"

        signature = "{}{}".format(val.__name__, func_args)
        if isinstance(val, types.MethodType):
            ret = "<method {} at 0x{:02x}>".format(signature, id(val))

        else:
            ret = "<function {} at 0x{:02x}>".format(signature, id(val))

        return ret


class PathValue(ObjectValue):
    """
    https://docs.python.org/3/library/pathlib.html
    """
    @classmethod
    def is_valid(cls, val):
        return isinstance(val, PurePath)

    def string_value(self):
        prefix = self.prefix_value()
        body = String(self.val)
        return self.finalize_value(prefix, body)



