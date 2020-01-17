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

from .compat import *
from . import environ
from .path import Path
from .utils import String, Bytes


logger = logging.getLogger(__name__)


class Inspect(object):
    """Identify what a python object is (eg, FUNCTION, STRING, etc)"""

    @property
    def classname(self):
        name = self.typename
        class_name = "{}Value".format(name.title().replace("_", ""))
        return class_name

    @property
    def classtype(self):
        classname = self.classname
        module = sys.modules[__name__]
        return getattr(module, classname)

    @property
    def cls(self):
        return self.val.__class__ if self.has_attr('__class__') else None

    @property
    def typename(self):
        '''
        get the type of val

        there are multiple places where we want to know if val is an object, or a string, or whatever,
        this method allows us to find out that information

        since -- 7-10-12

        val -- mixed -- the value to check

        return -- string -- the type
        '''
        t = 'DEFAULT'
        # http://docs.python.org/2/library/types.html
#         func_types = (
#             types.FunctionType,
#             types.BuiltinFunctionType,
#             types.MethodType,
#             types.UnboundMethodType,
#             types.BuiltinFunctionType,
#             types.BuiltinMethodType,
#             classmethod
#         )

        if self.is_primitive():
            t = 'DEFAULT'

        elif self.is_dict():
            t = 'DICT'

        elif self.is_list():
            t = 'LIST'

        elif self.is_array():
            t = 'ARRAY'

        elif self.is_tuple():
            t = 'TUPLE'

        elif self.is_type():
            t = 'TYPE'

        elif self.is_binary():
            t = 'BINARY'

        elif self.is_str():
            t = 'STRING'

        elif self.is_exception():
            t = 'EXCEPTION'

        elif self.is_module():
            # this has to go before the object check since a module will pass the object tests
            t = 'MODULE'

        elif self.is_callable():
            t = 'FUNCTION'

            # not doing this one since it can cause the class instance to do unexpected
            # things just to print it out
            #elif isinstance(val, property):
            # uses the @property decorator and the like
            #t = 'PROPERTY'

        elif self.is_dict_proxy():
            # maybe we have a dict proxy?
            t = 'DICT_PROXY'

        elif self.is_generator():
            t = 'GENERATOR'

        elif self.is_set():
            t = 'SET'

        elif self.is_object():
            t = 'OBJECT'

#         elif isinstance(val, func_types) and hasattr(val, '__call__'):
#             # this has to go after object because lots of times objects can be classified as functions
#             # http://stackoverflow.com/questions/624926/
#             t = 'FUNCTION'

        elif self.is_regex():
            t = 'REGEX'

        else:
            t = 'DEFAULT'

        return t

    def __init__(self, val):
        self.val = val
        self.attrs = set(dir(val))

    def is_generator(self):
        if is_py2:
            return isinstance(self.val, (types.GeneratorType, range))
        else:
            return isinstance(self.val, (types.GeneratorType, range, map))

    def is_set(self):
        return isinstance(self.val, (set, frozenset, Set))

    def is_primitive(self):
        """is the value a built-in type?"""
        if is_py2:
            return isinstance(
                self.val, 
                (
                    types.NoneType,
                    types.BooleanType,
                    types.IntType,
                    types.LongType,
                    types.FloatType
                )
            )

        else:
            return isinstance(
                self.val,
                (
                    type(None),
                    bool,
                    int,
                    float
                )
            )

    def is_dict(self):
        return isinstance(self.val, dict)

    def is_list(self):
        return isinstance(self.val, (list, KeysView))

    def is_array(self):
        return isinstance(self.val, array.array)

    def is_tuple(self):
        return isinstance(self.val, tuple)

    def is_type(self):
        return isinstance(self.val, type)

    def is_binary(self):
        return isinstance(self.val, (bytes, bytearray, memoryview))

    def is_str(self):
        return isinstance(self.val, basestring)

    def is_exception(self):
        return isinstance(self.val, BaseException)

    def is_module(self):
        # this has to go before the object check since a module will pass the object tests
        return isinstance(self.val, types.ModuleType)

    def is_object(self):
#         print("{}".format(isinstance(self.val, (types.FunctionType, types.BuiltinFunctionType, types.MethodType))))
#         pout2.v(inspect.ismethod(self.val))
#         pout2.v(inspect.isfunction(self.val))
#         pout2.v(dir(self.val))
#         pout2.v(self.val.__class__)
#         pout2.v(inspect.ismethoddescriptor(self.val))
        if inspect.ismethod(self.val) or inspect.isfunction(self.val) or inspect.ismethoddescriptor(self.val):
            return False

        ret = False
        if isinstance(self.val, getattr(types, "InstanceType", object)):
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

    def is_callable(self):
        # not sure why class methods pulled from __class__ fail the callable check

        # if it has a __call__ and __func__ it's a method
        # if it has a __call__ and __name__ it's a function
        # if it just has a __call__ it's most likely an object instance
        ret = False
        d = dir(self.val)
        if "__call__" in d:
            ret = "__func__" in d or "__name__" in d

#         if hasattr(self.val, "__call__") and hasattr(self.val, "__func__"):
#             ret = True
# 
#         elif hasattr(self.val, "__call__") and hasattr(self.val, "__name__"):
#             ret = True

        return ret
        #return isinstance(self.val, Callable) or isinstance(self.val, classmethod)

    def is_dict_proxy(self):
        # NOTE -- in 3.3+ dict proxy is exposed, from types import MappingProxyType
        # https://github.com/eevee/dictproxyhack/blob/master/dictproxyhack.py
        ret = True
        attrs = self.attrs
        for a in ["__getitem__", "keys", "values"]:
            if not self.has_attr(a):
                ret = False
                break
        return ret

    def is_regex(self):
        return "SRE_Pattern" in repr(self.val)

    def has_attr(self, k):
        """return True if this instance has the attribute"""
        return k in self.attrs


class Value(object):

    inspect_class = Inspect

    @property
    def raw(self):
        return self.val
    value = raw

    def __new__(cls, val, depth=0):
        """through magic, instantiating an instance will actually create
        subclasses of the different *Value classes, once again, through magic"""
        t = cls.inspect_class(val)
        typename = t.typename
        try:
            value_cls = t.classtype
        except AttributeError:
            value_cls = DefaultValue

        # we don't pass in (val, depth) because this just returns the instance
        # and then __init__ is called with those values also
        instance = super(Value, cls).__new__(value_cls)
        instance.typename = typename
        return instance

    def __init__(self, val, depth=0):
        self.val = val
        self.depth = depth

    def string_value(self):
        raise NotImplementedError()
    string_val = string_value

    def bytes_value(self):
        s = self.string_value()
        return Bytes(s)
    bytes_val = bytes_value

    def __repr__(self):
        if is_py2:
            s = self.bytes_value()
        else:
            s = self.string_value()
        return s

    def __format__(self, format_str):
        return self.string_value() if isinstance(format_str, String.types) else self.bytes_value()

    def info(self):
        methods = []
        properties = []
        for ni, vi in inspect.getmembers(self.val):
            i = self.inspect_class(vi)
            #print(ni, i.typename, type(vi))
            #print(ni, type(vi))
            if i.is_type():
                properties.append((ni, vi))
            elif i.is_callable():
                methods.append((ni, vi))
            else:
                properties.append((ni, vi))

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


class DefaultValue(Value):
    def string_value(self):
        return "{}".format(repr(self.val))


class DictValue(Value):
    left_paren = "{"
    right_paren = "}"
    prefix = "\n"

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


class ListValue(DictValue):
    left_paren = '['
    right_paren = ']'
    name_callback = None

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


class SetValue(ListValue):
    left_paren = '{'
    right_paren = '}'

    def name_callback(self, k):
        return None


class TupleValue(ListValue):
    left_paren = '('
    right_paren = ')'


class BinaryValue(Value):
    def string_value(self):
        val = self.val
        try:
            if is_py2:
                s = "b'{}'".format(String(bytes(val)))
                #s = "b'{}'".format(bytes(val).decode(environ.ENCODING, errors=environ.ENCODING_REPLACE))

            else:
                s = repr(bytes(val))

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s


class StringValue(Value):
    def string_value(self):
        val = self.val
        try:
            if isinstance(val, unicode):
                s = '"{}"'.format(val)

            else:
                # !!! 12-27-2017 - with the new BINARY typename I don't think
                # this is reachable anymore
                # we need to convert the byte string to unicode
                #s = u'"{}"'.format(val.decode('utf-8', 'replace'))
                s = 'b"{}"'.format(val.decode(environ.ENCODING, environ.ENCODING_REPLACE))

        except (TypeError, UnicodeError) as e:
            s = "<UNICODE ERROR>"

        return s


class ObjectValue(Value):
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

    def string_value(self):
        val = self.val
        depth = self.depth
        d = {}
        vt = Inspect(val)
        errmsgs = []

        src_file = ""
        cls = vt.cls
        if cls:
            src_file = self._get_src_file(cls, default="")

        full_name = self._get_name(val, src_file=src_file)

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
                    if v.typename != 'FUNCTION':
                        instance_dict[k] = v

            #instance_dict = {}
            #instance_dict = {k: Value(v, depth+1) for k, v in inspect.getmembers(val)}
            #errmsgs.append("Failed to get vars because: {}".format(e))

        s = "{} instance".format(full_name)

        if vt.has_attr('__pout__'):
            s += repr(Value(val.__pout__()))

        else:
            if depth < environ.OBJECT_DEPTH:
                s += "\n<"
                s_body = ''

                s_body += "\nid: {}\n".format(id(val))
                if src_file:
                    s_body += "\npath: {}\n".format(Path(src_file))

                if cls:
                    pclses = inspect.getmro(cls)
                    if pclses:
                        s_body += "\nAncestry:\n"
                        for pcls in pclses:
                            psrc_file = self._get_src_file(pcls, default="")
                            if psrc_file:
                                psrc_file = Path(psrc_file)
                            pname = self._get_name(pcls, src_file=psrc_file)
                            if psrc_file:
                                s_body += self._add_indent(
                                    "{} ({})".format(pname, psrc_file),
                                    1
                                )
                            else:
                                s_body += self._add_indent(
                                    "{}".format(pname),
                                    1
                                )
                            s_body += "\n"

                if hasattr(val, '__str__'):

                    s_body += "\n__str__:\n"
                    s_body += self._add_indent(String(val), 1)
                    s_body += "\n"

                if cls:

                    # build a full class variables dict with the variables of 
                    # the full class hierarchy
                    class_dict = {}
                    for pcls in reversed(inspect.getmro(cls)):
                        for k, v in vars(pcls).items():
                            # filter out anything that's in the instance dict also
                            # since that takes precedence.
                            # We also don't want any __blah__ type values
                            if k not in instance_dict and not self._is_magic(k):
                                class_dict[k] = Value(v, depth+1)

                    if class_dict:

                        s_body += "\nClass Properties:\n"

                        for k, v in class_dict.items():
                            #if k in instance_dict:
                            #    continue

                            if v.typename != 'FUNCTION':

                                s_var = '{} = '.format(k)
                                s_var += v.string_value()

#                                 if v.typename == 'OBJECT':
#                                     s_var += repr(v.val)
#                                 else:
#                                     s_var += repr(v)

                                s_body += self._add_indent(s_var, 1)
                                s_body += "\n"

                if instance_dict:
                    s_body += "\nInstance Properties:\n"

                    for k, v in instance_dict.items():
                        s_var = '{} = '.format(k)
                        s_var += v.string_value()
#                         if v.typename == 'OBJECT':
#                             s_var += repr(v.val)
#                         else:
#                             s_var += repr(v)

                        s_body += self._add_indent(s_var, 1)
                        s_body += "\n"

                if errmsgs:
                    s_body += "\nREAD ERRORS: \n"
                    s_body += self._add_indent("\n".join(errmsgs), 1)
                    s_body += "\n"

                if not is_py2 and self.typename == 'EXCEPTION':
                    s_body += "\n"
                    s_body += "\n".join(traceback.format_exception(None, val, val.__traceback__))

                s += self._add_indent(s_body.rstrip(), 1)
                s += "\n>\n"

            else:
                s = String(repr(val))

        return s


class ExceptionValue(ObjectValue):
    pass


class ModuleValue(ObjectValue):
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
            if v.typename == 'FUNCTION':
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

                s += self._add_indent("{}".format(k), 1)
                s += "\n"

                # add methods
                for m, mv in inspect.getmembers(v):
                    mv = Value(mv)
                    if mv.typename == 'FUNCTION':
                        s += self._add_indent(".{}".format(mv), 2)
                        s += "\n"
                s += "\n"

        if properties:
            s += "\nProperties:\n"
            for k, v in properties.items():
                s += self._add_indent("{}".format(k), 1)
                #s += self._add_indent("{} = {}".format(k, self._str_val(v, depth=2)), 1)
                #s += self._add_indent("{} = {}".format(k, self._get_unicode(v)), 1)
                s += "\n"

        return s


class TypeValue(Value):
    def string_value(self):
        return '{}'.format(self.val)


class RegexValue(Value):
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


class FunctionValue(Value):
    def string_value(self):
        val = self.val
        try:
            if is_py2:
                func_args = inspect.formatargspec(*inspect.getfullargspec(val))
            else:
                func_args = "{}".format(inspect.signature(val))
        except (TypeError, ValueError):
            func_args = "(...)"

        return "{}{}".format(val.__name__, func_args)


