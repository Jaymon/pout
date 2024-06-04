# -*- coding: utf-8 -*-
import inspect
import os
import codecs
import ast
import re
import logging
import io
import tokenize

from .compat import *
from . import environ
from .path import Path
from .utils import String


logger = logging.getLogger(__name__)


class CallString(String):
    """Contains the actual pout.* call, this is needed to find the argument
    names and stuff"""
    @property
    def tokens(self):
        # https://github.com/python/cpython/blob/3.7/Lib/token.py
        logger.debug("Callstring [{}] being tokenized".format(self))
        return tokenize.generate_tokens(StringIO(self).readline)

    def is_complete(self):
        """Return True if this call string is complete, meaning it has a
        function name and balanced parens"""
        try:
            [t for t in self.tokens]
            ret = True
            logger.debug("CallString [{}] is complete".format(self.strip()))

        except tokenize.TokenError:
            logger.debug(
                "CallString [{}] is NOT complete".format(self.strip())
            )
            ret = False

        return ret

    def call_statements(self):
        statements = []
        splitters = set([";", ":"])

        statement = ""
        for token in self.tokens:
            if token.string in splitters:
                statements.append(
                    type(self)(statement.strip())
                )

                statement = ""

            else:
                statement += token.string

        return statements

    def _append_name(self, arg_names, arg_name):
        n = ""
        is_string = []
        in_root = True
        last_tok_end = -1
        for token in arg_name:
            # https://github.com/python/cpython/blob/3.7/Lib/token.py
            # https://github.com/python/cpython/blob/3.7/Lib/tokenize.py
            c = token.string
            if last_tok_end < 0:
                last_tok_end = token.end[1]
            else:
                n += " " * (token.start[1] - last_tok_end)
                last_tok_end = token.end[1]

            if token.type == tokenize.STRING and in_root:
                is_string.append(True)

            elif token.type == tokenize.NAME:
                if c == "in":
                    is_string.append(False)

            else:
                if c in set(["[", "("]):
                    in_root = False
                elif c in set(["]", ")"]):
                    in_root = True

            n += c

        if is_string and all(is_string):
            arg_names.append("")
            logger.debug('Appending "{}" as a string'.format(n))
        else:
            n = n.strip()
            if n:
                logger.debug('Appending "{}"'.format(n))
                arg_names.append(n)

    def arg_names(self):
        arg_names = []
        try:
            tokens = list(self.tokens)

        except tokenize.TokenError:
            return arg_names

        # let's find the (
        token = tokens.pop(0)
        while token.string != "(":
            token = tokens.pop(0)


        # now we will divide by comma and find all the argument names
        arg_name = []
        token = tokens.pop(0)
        #stop_c = set([")", ","])
        stop_stack = [set([")", ","])]
        in_root = True
        while tokens and token.string != ";":
            c = token.string
            stop_c = stop_stack[-1]
            append_c = True
            logger.debug(
                'Checking "{}" ({}), in_root={}'.format(
                    c,
                    tokenize.tok_name[token.type],
                    in_root
                )
            )

            if c in stop_c:
                if in_root:
                    #arg_names.append(self._normalize_name(arg_name))
                    self._append_name(arg_names, arg_name)
                    #append_name(arg_name)
                    arg_name = []
                    append_c = False

                else:
                    stop_stack.pop()
                    in_root = len(stop_stack) == 1
                    #in_root = True
                    #stop_c = set([")", ","])

            else:
                if c == "(":
                    in_root = False
                    #stop_c = set([")"])
                    stop_stack.append(set([")"]))

                elif c == "[":
                    in_root = False
                    #stop_c = set(["]"])
                    stop_stack.append(set(["]"]))

            if append_c:
                arg_name.append(token)
                #pout2.v(arg_name)
                #print(arg_name)

            token = tokens.pop(0)

        #self._append_name(arg_names, arg_name)

        #pout2.v(arg_names)
        return arg_names


class Call(object):
    """Wraps a generic frame_tuple returned from like inspect.stack() and makes
    the information containded in that FrameInfo tuple a little easier to
    digest

    since -- 7-2-12 -- Jay

    This wraps a .info dict that contains a bunch of information about the
    call:
        * line: int, what line the call originated on
        * file, str, the full filepath the call was made from
        * call, CallString|str, the full text of the call (currently, this
            might be missing a closing paren)
        * arg_names, list, the values passed to cthe call statement

    https://docs.python.org/3/library/inspect.html
    """
    @classmethod
    def get_src_lines(cls, path):
        """Read the src file at path and return the lines as a list

        :param path: str|Path, the full path to the source file
        :returns: list[str], the lines of the source file or empty list if it
            couldn't be loaded
        """
        try:
            open_kwargs = dict(
                mode='r',
                errors='replace',
                encoding=environ.ENCODING
            )
            with open(path, **open_kwargs) as fp:
                return fp.readlines()

        except (IOError, SyntaxError) as e:
            # we failed to open the file, IPython has this problem
            return []

    @classmethod
    def find_names(cls, called_module, called_func, ast_tree=None):
        """
        scan the abstract source tree looking for possible ways to call the
        called_module and called_func

        since -- 7-2-12 -- Jay

        :example:
            # import the module a couple ways:
            import pout
            from pout import v
            from pout import v as voom
            import pout as poom

            # this function would return: ['pout.v', 'v', 'voom', 'poom.v']

        module finder might be useful someday
        link -- http://docs.python.org/library/modulefinder.html
        link -- http://stackoverflow.com/questions/2572582/return-a-list-of-imported-python-modules-used-in-a-script

        :param ast_tree: _ast.* instance, the internal ast object that is being
            checked, returned from compile() with ast.PyCF_ONLY_AST flag
        :param called_module: str, we are checking the ast for imports of this
            module
        :param called_func: str, we are checking the ast for aliases of this
            function
        :returns: set, the list of possible calls the ast_tree could make to
            call the called_func
        """
        s = set()

        func_name = called_func
        if not isinstance(called_func, str):
            func_name = called_func.__name__

        module_name = called_module
        if not isinstance(called_module, str):
            module_name = called_module.__name__

        # always add the default call, the set will make sure there are no
        # dupes...
        s.add("{}.{}".format(module_name, func_name))

        if ast_tree:
            if hasattr(ast_tree, 'name'):
                if ast_tree.name == func_name:
                    # the function is defined in this module
                    s.add(func_name)

            if hasattr(ast_tree, 'body'):
                # further down the rabbit hole we go
                if isinstance(ast_tree.body, Iterable):
                    for ast_body in ast_tree.body:
                        s.update(
                            cls.find_names(
                                module_name,
                                func_name,
                                ast_body
                            )
                        )

            elif hasattr(ast_tree, 'names'):
                # base case
                if hasattr(ast_tree, 'module'):
                    # we are in a from ... import ... statement
                    if ast_tree.module == module_name:
                        for ast_name in ast_tree.names:
                            if ast_name.name == func_name:
                                if ast_name.asname is None:
                                    s.add(ast_name.name)

                                else:
                                    s.add(str(ast_name.asname))

                else:
                    # we are in an import ... statement
                    for ast_name in ast_tree.names:
                        if (
                            hasattr(ast_name, 'name')
                            and (ast_name.name == module_name)
                        ):
                            if ast_name.asname is None:
                                name = ast_name.name

                            else:
                                name = ast_name.asname

                            call = "{}.{}".format(
                                name,
                                func_name
                            )
                            s.add(call)

        return s

    @classmethod
    def find_call_info(cls, called_module, called_func, called_frame_info):
        """This has the same signature as .__init__ and is just here to
        get the caller frame info and then call .find_callstring_info

        :returns dict: see .find_callstring_info
        """
        try:
            frames = inspect.getouterframes(called_frame_info.frame)
            caller_frame_info = frames[1]

        except Exception as e:
            #logger.exception(e)
            # the call was from the outermost script/module
            caller_frame_info = called_frame_info

        finally:
            call_info = cls.find_callstring_info(
                called_module,
                called_func,
                caller_frame_info
            )

        return call_info

    @classmethod
    def find_callstring_info(cls, called_module, called_func, caller_frame_info):
        """Do the best we can to find the actual call string (ie, the function
        name and the arguments passed to the function when called) in the
        actual code

        This is where all the magic happens

        :param called_module: str|types.ModuleType, the module that was called,
            this should almost always be pout
        :param called_func: str|callable, this is the pout function that was
            called
        :param caller_frame_info: inspect.FrameInfo, this is the frame
            information about the caller (the code that called the module
            and func

            https://docs.python.org/3/library/inspect.html#the-interpreter-stack
            https://docs.python.org/3/reference/datamodel.html#frame-objects

        :returns: dict, a dictionary containing all the found information
            about the call
        """
        call_info = {}

        call_info["call"] = ""
        call_info["call_modname"] = called_module
        call_info["call_funcname"] = called_func
        call_info["arg_names"] = []

        call_info["file"] = Path(caller_frame_info.filename)
        call_info["line"] = caller_frame_info.lineno
        call_info["start_line"] = caller_frame_info.lineno
        call_info["stop_line"] = caller_frame_info.lineno

        if caller_frame_info.code_context is not None:
            src_lines = []

            cs = CallString(
                caller_frame_info.code_context[caller_frame_info.index]
            )
            if not cs.is_complete():
                # our call statement is actually multi-line so we will need to
                # load the file to find the full statement
                if src_lines := cls.get_src_lines(call_info["file"]):
                    total_lines = len(src_lines)
                    start_lineno = call_info["line"] - 1
                    stop_lineno = call_info["line"] + 1
                    while not cs.is_complete() and stop_lineno <= total_lines:
                        cs = CallString(
                            "".join(
                                src_lines[start_lineno:stop_lineno]
                            )
                        )
                        stop_lineno += 1

                    call_info["stop_line"] = stop_lineno - 1

            call_info["call"] = cs

            statements = cs.call_statements()
            if len(statements) > 1:
                # the line includes semi-colons so we need to find the correct
                # calling statement
                def get_call(statements, names):
                    for statement in statements:
                        for name in names:
                            if statement.startswith(name):
                                return statement

                names = cls.find_names(called_module, called_func)
                cs = get_call(statements, names)

                if not cs:
                    if not src_lines:
                        src_lines = cls.get_src_lines(call_info["file"])

                    if src_lines:
                        # we failed to easily find the correct calling statement
                        # so we are going to try a little harder this time
                        ast_tree = compile(
                            "".join(src_lines),
                            call_info['file'],
                            'exec',
                            ast.PyCF_ONLY_AST
                        )

                        names = cls.find_names(
                            called_module,
                            called_func,
                            ast_tree,
                        )
                        cs = get_call(statements, names)

            if cs:
                call_info["arg_names"] = cs.arg_names()

        return call_info

    def __init__(self, called_module, called_func, called_frame_info):
        """Get information about the call

        :param called_module: str|types.ModuleType, the called module (should
            almost always be "pout"
        :param called_func: str|callable, the pout function that was called
        :param called_outer_frame: inspect.FrameInfo, the frame information
            for the actual call, this will be used to find the caller, one row
            of the inspect.getouterframes return list
        """
        self.info = self.find_call_info(
            called_module,
            called_func,
            called_frame_info
        )


class Reflect(object):
    """This provides the meta information (file, line number) for the actual
    pout call
    """
    def __init__(self, module, module_function_name, function_arg_vals):
        self.module = module
        self.module_function_name = module_function_name
        self.arg_vals = function_arg_vals or []

    def __enter__(self):
        frame = frames = None

        try:
            # we want to get the frame of the current pout.* call
            frames = inspect.stack()
            frame = frames[1]
            self.call = Call(
                self.module.__name__,
                self.module_function_name,
                frame
            )

        except IndexError as e:
            # There was a very specific bug that would cause
            # inspect.getouterframes(frame) to fail when pout was called from
            # an object's method that was called from within a Jinja template,
            # it seemed like it was going to be annoying to reproduce and so I
            # now catch the IndexError that inspect was throwing
            #logger.exception(e)
            self.call = None

        self.info = self._get_arg_info()

        return self

    def __exit__(self, exception_type, exception_val, trace):
        del self.call

    def _get_arg_info(self):
        '''
        get all the info of a method call

        this will find what arg names you passed into the method and tie them
        to their passed in values, it will also find file and line number

        :returns: dict, a bunch of info on the call
        '''
        ret_dict = {
            'args': [],
            #'frame': None,
            'line': 'Unknown',
            'file': 'Unknown',
            'arg_names': []
        }
        #modname = self.modname

        c = self.call
        if c:
            ret_dict.update(c.info)

        arg_vals = self.arg_vals
        if len(arg_vals) > 0:
            args = []

            if len(ret_dict['arg_names']) > 0:
                # match the found arg names to their respective values
                for i, arg_name in enumerate(ret_dict['arg_names']):
                    try:
                        args.append({'name': arg_name, 'val': arg_vals[i]})

                    except IndexError:
                        # arg_vals[i] will fail with keywords passed into the
                        # method
                        break

            else:
                # we can't autodiscover the names, in an interactive shell
                # session?
                for i, arg_val in enumerate(arg_vals):
                    args.append(
                        {'name': 'Unknown {}'.format(i), 'val': arg_val}
                    )

            ret_dict['args'] = args

        return ret_dict

