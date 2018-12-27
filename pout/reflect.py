# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import inspect
import os
import codecs
import ast
import re
import logging
import tokenize
from io import BytesIO
from contextlib import contextmanager

from .compat import *
from . import environ
from .path import ModuleFile, Path
from .utils import String


logger = logging.getLogger(__name__)


# class TokenNames(dict):
#     def __init__(self):
#         import token
#         import tokenize
#         pout2.v(token.tok_name)
#         pout2.v(tokenize.tok_name)
# #         members = inspect.getmembers(token)
# #         for mn, mv in members:
# #             pout2.b()
# #             pout2.v(mn)
# #             pout2.v(mv)


class CallString(String):
    @property
    def tokens(self):
        return tokenize.tokenize(BytesIO(self.encode(environ.ENCODING)).readline)

    def is_complete(self):
        """Return True if this call string is complete, meaning it has a function
        name and balanced parens"""
        try:
            [t for t in self.tokens]
            ret = True
            logger.debug('CallString [{}] is complete'.format(self.strip()))

        except tokenize.TokenError:
            logger.debug('CallString [{}] is NOT complete'.format(self.strip()))
            ret = False

        return ret

    def _append_name(self, arg_names, arg_name):
        n = ""
        is_string = False
        in_root = True
        last_tok_end = -1
        for token in arg_name:
#             pout2.b()
#             pout2.v(tokenize.tok_name[token.type])
#             pout2.v(token.string)
            c = token.string
            if last_tok_end < 0:
                last_tok_end = token.end[1]
            else:
                n += " " * (token.start[1] - last_tok_end)
                last_tok_end = token.end[1]

            if token.type == tokenize.STRING and in_root:
                is_string = True
                break

            else:
                if c in set(["[", "("]):
                    in_root = False
                elif c in set(["]", ")"]):
                    in_root = True

                n += c

        if is_string:
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

        #append_name(arg_name)
        self._append_name(arg_names, arg_name)

        #pout2.v(arg_names)
        return arg_names


class Call(object):

    def __init__(self, frame_tuple, called_module='', called_func=''):
    #def _get_call_info(self, frame_tuple, called_module='', called_func=''):
        '''
        build a dict of information about the call

        since -- 7-2-12 -- Jay

        frame_tuple -- tuple -- one row of the inspect.getouterframes return list
        called_module -- string -- the module that was called, the module we're looking for in the frame_tuple
        called_func -- string -- the function that was called, the function we're looking for in the frame_tuple

        return -- dict -- a bunch of information about the call:
            line -- what line the call originated on
            file -- the full filepath the call was made from
            call -- the full text of the call (currently, this might be missing a closing paren)
        '''

        try:
            frames = inspect.getouterframes(frame_tuple[0])
            #prev_frame = frames[1]
            #print("\t{}:{} {}".format(prev_frame[1], prev_frame[2], prev_frame[4]))
            #pout2.v(prev_frame[0].f_code.co_name)
#             for i, frame in enumerate(frames, 0):
#                 print("\t{}. {}:{} {}".format(i, frame[1], frame[2], frame[4]))

#             m1 = inspect.getmodule(frame_tuple[0]).__name__
#             f1 = frame_tuple[0].f_code.co_name
#             m2 = inspect.getmodule(prev_frame[0]).__name__
#             f2 = prev_frame[0].f_code.co_name
#             print("\t", m1, f1, m2, f2)

            called_module = inspect.getmodule(frame_tuple[0]).__name__
            called_func = frame_tuple[0].f_code.co_name
            prev_frame = frame_tuple
            frame_tuple = frames[1]

#             pout2.v(prev_frame)
#             called_module = inspect.getmodule(prev_frame[0]).__name__
#             called_func = prev_frame[0].f_code.co_name

        except Exception as e:
            logger.exception(e)


#         pout2.v(frame_tuple[0])
#         pout2.v(frame_tuple[0].f_trace_lines)
#         pout2.v(frame_tuple[0].f_lasti)
#         pout2.v(frame_tuple[0].f_code.co_name)
#         pout2.v(frame_tuple[0].f_code.co_code)
#         pout2.v(frame_tuple[0].f_code.co_varnames)
#         pout2.v(frame_tuple[0].f_code.co_freevars)
#         pout2.v(frame_tuple[0].f_code.co_cellvars)
        call_info = {}
        #call_info['frame'] = frame_tuple
        call_info['line'] = frame_tuple[2]
        call_info['file'] = self._get_path(os.path.abspath(inspect.getfile(frame_tuple[0])))
        call_info['call'] = ''
        call_info['arg_names'] = []


#         if not called_module:
#             called_module = inspect.getmodule(frame_tuple[0]).__name__
# 
#         if not called_func:
#             called_func = frame_tuple[0].f_code.co_name

#         pout2.v(frame_tuple[0].f_code.co_filename)
#         pout2.v(called_module)
#         pout2.v(called_func)

        if frame_tuple[4] is not None:
            stop_lineno = call_info['line']
            start_lineno = call_info['line'] - 1
            arg_names = []
            call = ''

            if called_func and called_func != '__call__':
                # get the call block
                try:
                    open_kwargs = dict(mode='r', errors='replace', encoding=environ.ENCODING)
                    with codecs.open(call_info['file'], **open_kwargs) as fp:
                        caller_src = fp.read()

                    ast_tree = compile(
                        caller_src.encode(environ.ENCODING),
                        call_info['file'],
                        'exec',
                        ast.PyCF_ONLY_AST
                    )

                    func_calls = self._find_calls(ast_tree, called_module, called_func)

                    # now get the actual calling codeblock
                    regex = r"\s*(?:{})\s*\(".format("|".join([str(v) for v in func_calls]))
                    r = re.compile(regex) 
                    caller_src_lines = caller_src.splitlines(False)
                    total_lines = len(caller_src_lines)

                    # we need to move up one line until we get to the beginning of the call
                    while start_lineno >= 0:

                        call = "\n".join(caller_src_lines[start_lineno:stop_lineno])
                        match = r.search(call)
                        if(match):
                            call = call[match.start():]
                            break

                        else:
                            start_lineno -= 1

                    if start_lineno > -1:
                        # now we need to make sure we have the end of the call also
                        while stop_lineno < total_lines:
                            c = CallString(call)
                            if c.is_complete():
                                break
                            else:
                                call += "\n{}".format(caller_src_lines[stop_lineno])
                                stop_lineno += 1

                    else:
                        call = ''

                except (IOError, SyntaxError) as e:
                    # we failed to open the file, IPython has this problem
                    call = ""
#                     if len(frame_tuple[4]) > 0:
#                         call = CallString(frame_tuple[4][0])
#                         if not call.is_complete():
#                             call = ''

            if call:
                arg_names = CallString(call).arg_names()

            else:
                # we couldn't find the call, so let's just use what python gave us, this can
                # happen when something like: method = func; method() is done and we were looking for func() 
                call = frame_tuple[4][0]
                start_lineno = frame_tuple[2]

            call_info['start_line'] = start_lineno
            call_info['stop_line'] = stop_lineno
            call_info['call'] = call.strip()
            call_info['arg_names'] = arg_names
            call_info['call_modname'] = called_module
            call_info['call_funcname'] = called_func

        self.info = call_info

    def is_match(self, modname, funcname):
#         pout2.b()
#         pout2.v(self.info["call"])
#         pout2.v(self.info["call_modname"])
#         pout2.v(self.info["call_funcname"])
#         pout2.v(modname)
#         pout2.v(funcname)
        info = self.info
        return modname == info.get("call_modname", "") and funcname == info.get("call_funcname", "")

    def _get_path(self, path):
        return Path(path)

    def _find_calls(self, ast_tree, called_module, called_func):
        '''
        scan the abstract source tree looking for possible ways to call the called_module
        and called_func

        since -- 7-2-12 -- Jay

        example -- 
            # import the module a couple ways:
            import pout
            from pout import v
            from pout import v as voom
            import pout as poom

            # this function would return: ['pout.v', 'v', 'voom', 'poom.v']

        ast_tree -- _ast.* instance -- the internal ast object that is being checked, returned from compile()
            with ast.PyCF_ONLY_AST flag
        called_module -- string -- we are checking the ast for imports of this module
        called_func -- string -- we are checking the ast for aliases of this function

        return -- set -- the list of possible calls the ast_tree could make to call the called_func
        ''' 
        s = set()

        # always add the default call, the set will make sure there are no dupes...
        s.add("{}.{}".format(called_module, called_func))

        if hasattr(ast_tree, 'name'):
            if ast_tree.name == called_func:
                # the function is defined in this module
                s.add(called_func)

        if hasattr(ast_tree, 'body'):
            # further down the rabbit hole we go
            if isinstance(ast_tree.body, Iterable):
                for ast_body in ast_tree.body:
                    s.update(self._find_calls(ast_body, called_module, called_func))

        elif hasattr(ast_tree, 'names'):
            # base case
            if hasattr(ast_tree, 'module'):
                # we are in a from ... import ... statement
                if ast_tree.module == called_module:
                    for ast_name in ast_tree.names:
                        if ast_name.name == called_func:
                            s.add(unicode(ast_name.asname if ast_name.asname is not None else ast_name.name))

            else:
                # we are in a import ... statement
                for ast_name in ast_tree.names:
                    if hasattr(ast_name, 'name') and (ast_name.name == called_module):
                        call = "{}.{}".format(
                            ast_name.asname if ast_name.asname is not None else ast_name.name,
                            called_func
                        )
                        s.add(call)

        return s


class Reflect(object):
#     def __init__(self, modname, funcname="", arg_vals=None):
#         self.modname = modname
#         self.funcname = funcname
#         self.arg_vals = arg_vals or []
#         self.info = self._get_arg_info()

    def __init__(self, call, arg_vals=None):
        self.call = call or self._find_call()
        self.arg_vals = arg_vals or []
        self.info = self._get_arg_info()

    @classmethod
    @contextmanager
    def context(cls, arg_vals=None, **kwargs):

        try:
            # we want to get the frame of the current pout.* call
            frames = inspect.stack()
            frame = frames[2]

            modname = inspect.getmodule(frame[0]).__name__
            funcname = frame[0].f_code.co_name
            #print("{}:{} {} {}.{}".format(frame[1], frame[2], frame[4], modname, funcname))

            yield cls(Call(frame), arg_vals)

        finally:
            del frame
            del frames


    def _get_arg_info(self):
        '''
        get all the info of a method call

        this will find what arg names you passed into the method and tie them to their passed in values,
        it will also find file and line number

        return -- dict -- a bunch of info on the call
        '''
        ret_dict = {
            'args': [],
            #'frame': None,
            'line': 'Unknown',
            'file': 'Unknown',
            'arg_names': []
        }
        arg_vals = self.arg_vals
        #modname = self.modname

        c = self.call
        ret_dict.update(c.info)

        if len(arg_vals) > 0:
            args = []

            if len(ret_dict['arg_names']) > 0:
                # match the found arg names to their respective values
                for i, arg_name in enumerate(ret_dict['arg_names']):
                    args.append({'name': arg_name, 'val': arg_vals[i]})

            else:
                # we can't autodiscover the names, in an interactive shell session?
                for i, arg_val in enumerate(arg_vals):
                    args.append({'name': 'Unknown {}'.format(i), 'val': arg_val})

            ret_dict['args'] = args




        #back_i += 3 # move past the call to the outer frames and the call to this function
#         try:
#             #frame = inspect.currentframe()
#             #frames = inspect.getouterframes(frame)
# 
# #             frame = None
# #             frames = inspect.stack()
# # 
# #             #back_i = self._find_entry_frame(frames)
# #             c = self._find_entry_call(frames)
# #             if c:
# #                 #pout2.v(c.info)
# #                 ret_dict.update(c.info)
# # 
# # #             entry_frame = self._find_entry_frame(frames)
# # #             if entry_frame:
# # #                 #ret_dict.update(Call(frames[back_i], modname).info)
# # #                 ret_dict.update(Call(entry_frame).info)
# # 
# # #             if len(frames) > back_i:
# # #                 ret_dict.update(Call(frames[back_i], modname, frames[back_i - 1][3]).info)
# # 
# #         except IndexError as e:
# #             # There was a very specific bug that would cause inspect.getouterframes(frame)
# #             # to fail when pout was called from an object's method that was called from
# #             # within a Jinja template, it seemed like it was going to be annoying to
# #             # reproduce and so I now catch the IndexError that inspect was throwing
# #             logger.exception(e)
# # 
#         finally:
#             # build the arg list if values have been passed in
#             if len(arg_vals) > 0:
#                 args = []
# 
#                 if len(ret_dict['arg_names']) > 0:
#                     # match the found arg names to their respective values
#                     for i, arg_name in enumerate(ret_dict['arg_names']):
#                         args.append({'name': arg_name, 'val': arg_vals[i]})
# 
#                 else:
#                     # we can't autodiscover the names, in an interactive shell session?
#                     for i, arg_val in enumerate(arg_vals):
#                         args.append({'name': 'Unknown {}'.format(i), 'val': arg_val})
# 
#                 ret_dict['args'] = args
# 
#             # make sure we avoid a reference cycle
#             # https://docs.python.org/3/library/inspect.html#the-interpreter-stack
#             del frame
#             del frames

        #pout2.v(ret_dict)
        return ret_dict

    def _find_call(self):
        try:
            frames = inspect.stack()

            #back_i = self._find_entry_frame(frames)
            c = self._find_entry_call(frames)
            if c:
                #pout2.v(c.info)
                ret_dict.update(c.info)

        except IndexError as e:
            # There was a very specific bug that would cause inspect.getouterframes(frame)
            # to fail when pout was called from an object's method that was called from
            # within a Jinja template, it seemed like it was going to be annoying to
            # reproduce and so I now catch the IndexError that inspect was throwing
            logger.exception(e)

        finally:
            del frames

    def _find_entry_call(self, frames):
        """attempts to auto-discover the correct frame"""

        back_i = 0
        pout_path = self._get_src_file(self.modname)
        for frame_i, frame in enumerate(frames):
            if frame[1] == pout_path:
                back_i = frame_i

        return Call(frames[back_i])





        c = None

#         for i, frame in enumerate(frames, 0):
#             print("{}. {}:{} {}".format(i, frame[1], frame[2], frame[4]))
#             #pout2.v(frame[0].f_code.co_name)
#             #pout2.v(frame[0].f_trace_lines)
#             #pout2.v(frame)
# 
#             try:
#                 c = Call(frame)
#                 print("{}. {}.{}".format(i, c.info["call_modname"], c.info["call_funcname"]))
#             except Exception as e:
#                 pout2.v(e)
#             #pout2.v(c.info["call"])
#             #pout2.v(c.info["call_modname"])
#             #pout2.v(c.info["call_funcname"])
# 
#         return None
        # we find the correct frame by trying to find the last time in a chain
        # pout/__init__.py was called, once it finds the first pout/__init__.py
        # reference we have entered the chain and when we no longer find those
        # calls we have exited the chain and that entry in the frame was the
        # entry we were searching for, see https://github.com/Jaymon/pout/issues/31
        # for more color
        back_i = 0
        found_chain = False
        pout_path = self._get_src_file(self.modname)
        logger.debug("Looking for entry frame for {}".format(pout_path))
        for frame_i, frame in enumerate(frames):
            logger.debug("{}. {}:{}".format(frame_i, frame[1], frame[2]))
            if frame[1] == pout_path:
                back_i = frame_i
                if not found_chain:
                    logger.debug("{}. Chain started at {}:{}".format(frame_i, frame[1], frame[2]))
                found_chain = True

            else:
                if found_chain:
                    #back_i = frame_i

                    modname = self.modname
                    funcname = self.funcname
                    c = Call(frames[back_i])
                    if c.is_match(modname, funcname):
                        logger.debug("{}. Chain broken at {}:{}".format(frame_i, frame[1], frame[2]))
                        #break

                    else:
                        c = None

        logger.debug("Returning entry frame {}:{}".format(frames[back_i][1], frames[back_i][2]))
        #pout2.v(frames[back_i][0].f_code.co_names)
        #pout2.v(frames[back_i])
        return c

    def _find_entry_frame(self, frames):
        """attempts to auto-discover the correct frame"""
        back_i = 0

#         for i, frame in enumerate(frames, 0):
#             print("{}. {}:{} {}".format(i, frame[1], frame[2], frame[4]))
#             #pout2.v(frame[0].f_code.co_name)
#             #pout2.v(frame[0].f_trace_lines)
#             #pout2.v(frame)
# 
#             try:
#                 c = Call(frame)
#                 print("{}. {}.{}".format(i, c.info["call_modname"], c.info["call_funcname"]))
#             except Exception as e:
#                 pout2.v(e)
#             #pout2.v(c.info["call"])
#             #pout2.v(c.info["call_modname"])
#             #pout2.v(c.info["call_funcname"])
# 
#         return None
        # we find the correct frame by trying to find the last time in a chain
        # pout/__init__.py was called, once it finds the first pout/__init__.py
        # reference we have entered the chain and when we no longer find those
        # calls we have exited the chain and that entry in the frame was the
        # entry we were searching for, see https://github.com/Jaymon/pout/issues/31
        # for more color
        found_chain = False
        pout_path = self._get_src_file(self.modname)
        logger.debug("Looking for entry frame for {}".format(pout_path))
        for frame_i, frame in enumerate(frames):
            logger.debug("{}. {}:{}".format(frame_i, frame[1], frame[2]))
            if frame[1] == pout_path:
                back_i = frame_i
                if not found_chain:
                    logger.debug("{}. Chain started at {}:{}".format(frame_i, frame[1], frame[2]))
                found_chain = True

            else:
                if found_chain:
                    #back_i = frame_i

                    modname = self.modname
                    funcname = self.funcname
                    c = Call(frames[back_i])
                    if c.is_match(modname, funcname):
                        logger.debug("{}. Chain broken at {}:{}".format(frame_i, frame[1], frame[2]))
                        break

        logger.debug("Returning entry frame {}:{}".format(frames[back_i][1], frames[back_i][2]))
        #pout2.v(frames[back_i][0].f_code.co_names)
        #pout2.v(frames[back_i])
        return frames[back_i]

    def _get_src_file(self, modname, default='Unknown'):
        '''
        return the source file path

        since -- 7-19-12

        val -- string -- the module's name you're looking for

        return -- string -- the path, or something like 'Unknown' if you can't find the path
        '''
        return ModuleFile(modname) or default


