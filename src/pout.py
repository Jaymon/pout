"""
prints out variables and other handy things to help with debugging

print was too hard to read, pprint wasn't much better. I was getting sick of typing: 
print "var name: {}".format(var). This tries to print out variables with their name, 
and where the print statement was called (so you can easily find it and delete it later).

link -- http://stackoverflow.com/questions/3229419/pretty-printing-nested-dictionaries-in-python
link -- http://docs.python.org/library/pprint.html
link -- http://docs.python.org/library/inspect.html
link -- http://www.doughellmann.com/PyMOTW/inspect/

in the future, to list method arguments:
link -- http://stackoverflow.com/questions/3517892/python-list-function-argument-names

should take a look at this in more detail:
link -- http://docs.python.org/library/repr.html

module finder might be useful someday
link -- http://docs.python.org/library/modulefinder.html
link -- http://stackoverflow.com/questions/2572582/return-a-list-of-imported-python-modules-used-in-a-script

api --
    h() -- easy way to print "here" in the code
    v(arg1, [arg2, ...]) -- print out arg1 = val, etc. with info like file and line numbers

example -- put this module in every other module without having to import it
    import pout
    import __builtin__
    __builtin__.pout = pout

since -- 6-26-12
author -- Jay Marcyes
license -- MIT -- http://www.opensource.org/licenses/mit-license.php
"""

import inspect
import os
import sys
import traceback
import ast
import re
import collections
import types

#import pout2

def t(inspect_packages=False, depth=0):
    '''
    print a backtrace
    
    since -- 7-6-12
    
    ignore_packages -- boolean -- if True, then anything from site-packages will be skipped
    inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
        in the pythonN directories, that cuts out a lot of the noise, set this to True if you
        want a full stacktrace
    depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
        the last three calls, pass in depth=3 so you only get the last 3 rows of the stack
    '''
    frame = inspect.currentframe()
    frames = inspect.getouterframes(frame)
    call_info = _get_arg_info()
    calls = _get_backtrace(frames=frames, inspect_packages=inspect_packages, depth=depth)
    _print(calls, call_info)
    
def h(count=0):
    '''
    prints "here count"
    
    example -- 
        h(1) # here 1 (/file:line)
        h() # here line (/file:line)
        

    count -- integer -- the number you want to put after "here"
    '''

    call_info = _get_arg_info()
    args = [u"here {} ".format(count if count > 0 else call_info['line'])]
    _print(args, call_info)

def v(*args):
    '''
    print the name = values of any passed in variables
    
    this prints out the passed in name, the value, and the file:line where the v()
    method was called so you can easily find it and remove it later
    
    example -- 
        foo = 1
        bar = [1, 2, 3]
        out.v(foo, bar)
        """ prints out:
        foo = 1

        bar = 
        [
            0: 1,
            1: 2,
            2: 3
        ]
        
        (/file:line)
        """
    
    *args -- list -- the variables you want to see pretty printed for humans
    '''    
    
    assert len(args) > 0, "you didn't pass any arguments to print out"
    
    call_info = _get_arg_info(args)
    
    args = [u"{}\n\n".format(_str(v['name'], v['val'])) for v in call_info['args']]
    _print(args, call_info)

def _print(args, call_info):
    '''
    handle printing args to the screen
    
    currently, we use stderr

    link -- http://stackoverflow.com/questions/5574702/how-to-print-to-stderr-in-python
    
    args -- list -- the list of string args to print
    call_info -- dict -- returned from _get_arg_info()
    '''

    sys.stderr.write("\n")

    for arg in args:
        sys.stderr.write(u"{}".format(arg))
        
    sys.stderr.write(u"({}:{})\n\n".format(call_info['file'], call_info['line']))
    sys.stderr.flush()
    
   
def _str(name, val):
    '''
    return a string version of name = val that can be printed
    
    example -- 
        _str('foo', 'bar') # foo = bar
    
    name -- string -- the variable name that was passed into one of the public methods
    val -- mixed -- the variable at name's value
    
    return -- string
    '''
    
    s = ''
    
    if name:
        
        if hasattr(val, '__len__'):
            count = len(val)
            s = u"{} ({}) = {}".format(name, count, _str_val(val, depth=0))
           
        else:
            s = u"{} = {}".format(name, _str_val(val))
            
    else:
        s = _str_val(val)
    
    return s

def _str_val(val, depth=0):
    '''
    turn val into a string representation of val
    
    val -- mixed -- the value that will be turned into a string
    depth -- integer -- how many levels of recursion we've done
    
    return -- string
    '''

    s = u''
    t = _get_type(val)
    
    if t == 'DICT':
        
        if len(val) > 0:
        
            s = _str_iterator(
                iterator=val.iteritems(), 
                name_callback= lambda k: u"'{}'".format(k),
                left_paren='{', 
                right_paren='}',
                depth=depth
            )
            
        else:
            s = u"{}"
        
    
    elif t == 'LIST':
    
        if len(val) > 0:
      
            s = _str_iterator(iterator=enumerate(val), depth=depth)
      
        else:
            s = u"[]"
     
    elif t == 'TUPLE':

        if len(val) > 0:
      
            s = _str_iterator(iterator=enumerate(val), left_paren='(', right_paren=')', depth=depth)
      
        else:
            s = u"()"
      
    elif t == 'STRING':
        #s = unicode(val, encoding='utf-8', errors='replace')
        #s = unicode(val, errors='replace')
        #s = val.decode('utf-8', errors='replace')
        try:
            s = u"{}".format(val)
        except (TypeError, UnicodeError), e:
            s = u"<TRANSLATION ERROR>"
            
    
    elif t == 'EXCEPTION':
        # http://docs.python.org/library/traceback.html
        # http://www.doughellmann.com/PyMOTW/traceback/
        # http://stackoverflow.com/questions/4564559
        # http://stackoverflow.com/questions/6626342
    
        calls = []
        full_name = _get_name(val)
        exc_type, exc_value, exc_tb = sys.exc_info()
        
        # this just doesn't work right
        if exc_tb:
            frames = inspect.getinnerframes(exc_tb)[::-1]
            for i, frame in enumerate(frames, 1):
                calls.append(
                    _get_call_summary(_get_call_info(frame), index=i, inspect_packages=False)
                )
        
                calls.reverse()
        
        else:
            frame = inspect.currentframe()
            frames = inspect.getouterframes(frame)[2:]
            calls = _get_backtrace(frames)
        
        s = u"{} - {}\n\n{}".format(full_name, val, u"".join(calls))
        #s = u"{} - {}\n\n{}".format(full_name, val, u"".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    
    elif t == 'OBJECT':
        d = {}
        full_name = _get_name(val)
        
        s = u"{} instance".format(full_name)
        
        if depth < 4:
        
            s += "\n<"
            s_body = u''
        
            if hasattr(val, '__str__'):
                
                s_body += "\n__str__:\n"
                s_body += _add_indent(str(val), 1)
                s_body += "\n"

            if hasattr(val, '__class__'):

                # we don't want any __blah__ type values
                class_dict = {k: v for k, v in vars(val.__class__).iteritems() if not _is_magic(k)}
                if class_dict:
                
                    s_body += "\nClass Variables:\n"
                
                    for k, v in class_dict.iteritems():
                        vt = _get_type(v)
                        if vt != 'FUNCTION':
                        
                            s_var = u'{} = '.format(k)
                        
                            if vt == 'OBJECT':
                                s_var += repr(v)
                            else:
                                s_var += _str_val(v, depth=depth+1)
                            
                            s_body += _add_indent(s_var, 1)
                            s_body += "\n"
        
            instance_dict = vars(val)
            if instance_dict:
                s_body += "\nInstance Variables:\n"                
                
                for k, v in instance_dict.iteritems():
                    vt = _get_type(v)
                    s_var = u'{} = '.format(k)
                    if vt == 'OBJECT':
                        s_var += repr(v)
                    else:
                        s_var += _str_val(v, depth=depth+1)
                    
                    s_body += _add_indent(s_var, 1)
                    s_body += "\n"
            
            s += _add_indent(s_body.rstrip(), 1)
            s += "\n>\n"
            
        else:
            s = repr(val)
    
    elif t == 'MODULE':
    
        file_path = os.path.realpath(inspect.getfile(val))
        s = u'{} module ({})\n'.format(val.__name__, file_path, '')
        
        modules = {}
        funcs = {}
        classes = {}
        
        for k, v in inspect.getmembers(val):
            
            # canary, ignore magic values
            if _is_magic(k): continue
            
            vt = _get_type(v)
            if vt == 'FUNCTION':
                funcs[k] = v
            elif vt == 'MODULE':
                modules[k] = v
            elif vt == 'OBJECT':
                classes[k] = v
            
            #pout2.v('%s %s: %s' % (k, vt, repr(v)))
        
        if modules:
            s += "\nModules:\n"
            for k, v in modules.iteritems():
                try:
                    module_path = os.path.realpath(inspect.getfile(v))
                except TypeError:
                    module_path = 'Unknown'
            
                s += _add_indent("{} ({})".format(k, module_path), 1)
                s += "\n"
        
        if funcs:
            s += "\nFunctions:\n"
            
            for k, v in funcs.iteritems():
            
                func_args = inspect.formatargspec(*inspect.getargspec(v))
                #pout2.v(func_args)
            
                s += _add_indent("{}{}".format(k, func_args), 1)
                s += "\n"
                
        if classes:
            s += "\nClasses:\n"
            
            for k, v in classes.iteritems():
            
                #func_args = inspect.formatargspec(*inspect.getargspec(v))
                #pout2.v(func_args)
            
                s += _add_indent("{}".format(k), 1)
                s += "\n"
                
                # add methods
                for m, mv in inspect.getmembers(v):
                    #if _is_magic(m): continue
                    if _get_type(mv) == 'FUNCTION':
                        try:
                            func_args = inspect.formatargspec(*inspect.getargspec(mv))
                            s += _add_indent(".{}{}".format(m, func_args), 2)
                            s += "\n"
                        except TypeError:
                            pass
                
                s += "\n"
    
    else:
        s = u"{}".format(val)

    s = u"{}".format(s)
    return s

def _str_iterator(iterator, name_callback=None, prefix="\n", left_paren='[', right_paren=']', depth=0):
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

    s = '{}{}\n'.format(prefix, _add_indent(left_paren, indent))
            
    s_body = ''
        
    for k, v in iterator:
        k = k if name_callback is None else name_callback(k)
        try:
            s_body += "{}: {},\n".format(k, _str_val(v, depth=depth+1))
        except RuntimeError, e:
            # I've never gotten this to work
            s_body += "{}: ... Recursion error ...,\n".format(k)
    
    s_body = s_body.rstrip(",\n")
    s_body = _add_indent(s_body, indent + 1)
    
    s += s_body
    s += "\n{}".format(_add_indent(right_paren, indent))
    
    return s

def _get_name(val, default='Unknown'):
    '''
    get the full namespaced (module + class) name of the val object
    
    since -- 6-28-12
    
    val -- mixed -- the value (everything is an object) object
    default -- string -- the default name if a decent name can't be found programmatically
    
    return -- string -- the full.module.Name
    '''
    module_name = '{}.'.format(getattr(val, '__module__', '')).lstrip('.')
    class_name = getattr(getattr(val, '__class__'), '__name__', default)
    full_name = "{}{}".format(module_name, class_name)
    
    return full_name

def _add_indent(val, indent):
    '''
    add whitespace to the beginning of each line of val
    
    link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/
    
    val -- string
    indent -- integer -- how much whitespace we want in front of each line of val
    
    return -- string -- val with more whitespace
    '''

    # canary
    if indent < 1: return val

    s = val.split('\n')
    s = [("\t" * indent) + line for line in s]
    s = "\n".join(s)
    return s

def _get_arg_info(arg_vals={}, back_i=0):
    '''
    get all the info of a method call
    
    this will find what arg names you passed into the method and tie them to their passed in values,
    it will also find file and line number
    
    note -- 7-3-12 -- I can't help but think this whole function could be moved into other
        parts of other functions now, since it sets defaults in ret_dict that would probably
        be better being set in _get_call_info() and combines args that might be better
        done in a combined _get_arg_names() method
    
    arg_vals -- list -- the arguments passed to one of the public methods
    back_i -- integer -- how far back in the stack the method call was, this moves back from 2
        already (ie, by default, we add 2 to this value to compensate for the call to this method
        and the previous method (both of which are usually internal))
    
    return -- dict -- a bunch of info on the call
    '''
    
    ret_dict = {
        'args': {},
        'frame': None,
        'line': 'Unknown',
        'file': 'Unknown'
    }
    args = {}
    
    back_i += 2 # move past the call to the outer frames and the call to this function
    frame = inspect.currentframe()
    frames = inspect.getouterframes(frame)
    
    if len(frames) > back_i:
        ret_dict.update(_get_call_info(frames[back_i], __name__, frames[back_i - 1][3]))
        
    print ret_dict
    # build the arg list if values have been passed in
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
    
    return ret_dict

def _get_call_info(frame_tuple, called_module='', called_func=''):
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

    call_info = {}
    call_info['frame'] = frame_tuple
    call_info['line'] = frame_tuple[2]
    call_info['file'] = os.path.abspath(inspect.getfile(frame_tuple[0]))
    call_info['call'] = u''
    call_info['arg_names'] = []
    
    if frame_tuple[4] is not None:
        
        stop_lineno = call_info['line']
        start_lineno = call_info['line'] - 1
        arg_names = []
        call = u''
        
        if called_func and called_func != '__call__':
            
            # get the call block
            try:
                caller_src = open(call_info['file'], 'rU').read()
                ast_tree = compile(caller_src, call_info['file'], 'exec', ast.PyCF_ONLY_AST)
                
                func_calls = _find_calls(ast_tree, called_module, called_func)
                
                # now get the actual calling codeblock
                regex = u"\s*(?:{})\s*\(".format(u"|".join([str(v) for v in func_calls]))
                r = re.compile(regex) 
                caller_src_lines = caller_src.split("\n")
                total_lines = len(caller_src_lines)
                
                # we need to move up one line until we get to the beginning of the call
                while start_lineno >= 0:
                
                    call = u"\n".join(caller_src_lines[start_lineno:stop_lineno])
                    if(r.search(call)):
                        break
                    else:
                        start_lineno -= 1
                
                if start_lineno > -1:
                    # now we need to make sure we have the end of the call also
                    while stop_lineno < total_lines:
                    
                        arg_names, is_balanced = _get_arg_names(call)
                    
                        if is_balanced:
                            break
                        else:
                            call += u"\n{}".format(caller_src_lines[stop_lineno])
                            stop_lineno += 1
                            
                else:
                    call = u''

            except IOError:
                # we failed to open the file, IPython has this problem
                pass
                    
        
        if not call:
            # we couldn't find the call, so let's just use what python gave us, this can
            # happen when something like: method = func; method() is done and we were looking for func() 
            call = frame_tuple[4][0]
            start_lineno = frame_tuple[2]
            
        call_info['start_line'] = start_lineno
        call_info['stop_line'] = stop_lineno
        call_info['call'] = call.strip()
        call_info['arg_names'] = arg_names
    
    return call_info
    
def _find_calls(ast_tree, called_module, called_func):
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
    s.add(u"{}.{}".format(called_module, called_func))

    if hasattr(ast_tree, 'name'):
        if ast_tree.name == called_func:
            # the function is defined in this module
            s.add(called_func)
    
    if hasattr(ast_tree, 'body'):
        # further down the rabbit hole we go
        if isinstance(ast_tree.body, collections.Iterable):
            for ast_body in ast_tree.body:
                s.update(_find_calls(ast_body, called_module, called_func))
            
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
                if ast_name.name == called_module:
                    call = u"{}.{}".format(
                        ast_name.asname if ast_name.asname is not None else ast_name.name,
                        called_func
                    )
                    s.add(call)
    
    return s
    
def _get_arg_names(call_str):
    '''
    get the arguments that were passed into the call
    
    example -- 
        call_str = "func(foo, bar, baz)"
        arg_names, is_balanced = _get_arg_names(call_str)
        print arg_names # ['foo', 'bar', 'baz']
        print is_balanced # True
    
    since -- 7-3-12 -- Jay
    
    call_str -- string -- the call string to parse
    
    return -- tuple -- [], is_balanced where [] is a list of the parsed arg names, and is_balanced is
        True if the right number of parens where found and False if they weren't, this is necessary
        because functions can span multiple lines and we might night have the full call_str yet
    '''

    #canary
    if not call_str: return [], True

    stack_paren = []
    stack_bracket = []
    stack_quote = []
    has_name = True
    arg_build = False
    arg_name = u''
    arg_names = []
    is_balanced = False

    for c in call_str:
    
        if c == '(' and (len(stack_quote) == 0):
            stack_paren.append(c)
            if len(stack_paren) == 1:
                # we've found the first paren of the pout call
                arg_build = True
                continue
        
        elif c == ')' and (len(stack_quote) == 0):
            stack_paren.pop()
            
            if len(stack_paren) == 0:
                is_balanced = True
                arg_names.append(arg_name.strip() if has_name else u'')
                break
        
        elif c == '[' and (len(stack_quote) == 0):
            stack_bracket.append(c)
        elif c == ']' and (len(stack_quote) == 0):
            stack_bracket.pop()
        elif c == '"' or c == "'":
            # we only pop on unescaped matches, (eg, strings that start with ' can have ")
            if len(stack_quote) > 0:
                if (stack_quote[-1] == c) and (arg_name[-1] != '\\'):
                    stack_quote.pop()
            else:
                # a string was passed in
                if (len(stack_paren) == 1) and (len(stack_bracket) == 0):
                    has_name = False
            
                stack_quote.append(c)
        
        elif c == ',':
            # we have finished compiling an argument name
            if (len(stack_paren) == 1) and (len(stack_bracket) == 0) and (len(stack_quote) == 0):
                arg_names.append(arg_name.strip() if has_name else u'')
                has_name = True
                arg_name = u''
                continue
        
        if arg_build:
            arg_name += c
    
    else:
        # run this if we didn't break to clean up:
        # http://psung.blogspot.com/2007/12/for-else-in-python.html
        if arg_name:
            is_balanced = False
            arg_names.append(arg_name.strip() if has_name else u'')
            
    return arg_names, is_balanced

def _get_backtrace(frames, inspect_packages=False, depth=0):
    '''
    get a nicely formatted backtrace
    
    since -- 7-6-12
    
    frames -- list -- the frame_tuple frames to format
    inpsect_packages -- boolean -- by default, this only prints code of packages that are not 
        in the pythonN directories, that cuts out a lot of the noise, set this to True if you
        want a full stacktrace
    depth -- integer -- how deep you want the stack trace to print (ie, if you only care about
        the last three calls, pass in depth=3 so you only get the last 3 rows of the stack
       
    return -- list -- each line will be a nicely formatted entry of the backtrace
    '''
    calls = []
    count = 1
    
    for i, f in enumerate(frames[1:]):
        prev_f = frames[i]
        called_module = inspect.getmodule(prev_f[0]).__name__
        called_func = prev_f[3]
        
        d = _get_call_info(f, called_module, called_func)
        s = _get_call_summary(d, inspect_packages=inspect_packages, index=count)
        calls.append(s)
        count += 1
        
        if depth and (count > depth):
            break
    
    # reverse the order on return so most recent is on the bottom
    return calls[::-1]

def _get_call_summary(call_info, index=0, inspect_packages=True):
    '''
    get a call summary
    
    a call summary is a nicely formatted string synopsis of the call
    
    handy for backtraces
    
    since -- 7-6-12
    
    call_info -- dict -- the dict returned from _get_call_info()
    index -- integer -- set to something above 0 if you would like the summary to be numbered
    inspect_packages -- boolean -- set to True to get the full format even for system frames
    
    return -- string
    '''
    inspect_regex = re.compile(u'[\\\\/]python\d(?:\.\d+)?', re.I)
    
    # truncate the filepath if it is super long
    f = call_info['file']
    if len(f) > 75:
        f = u"{}...{}".format(f[0:30], f[-45:])
    
    if inspect_packages or not inspect_regex.search(call_info['file']): 
            
        s = u"{}:{}\n\n{}\n\n".format(
            f,
            call_info['line'],
            _add_indent(call_info['call'], 1)
        )
        
    else:
        
        s = u"{}:{}\n".format(
            f,
            call_info['line']
        )
    
    if index > 0:
        s = u"{:02d} - {}".format(index, s)

    return s

def _get_type(val):
    '''
    get the type of val
    
    there are multiple places where we want to know if val is an object, or a string, or whatever,
    this method allows us to find out that information
    
    since -- 7-10-12
    
    val -- mixed -- the value to check
    
    return -- string -- the type
    '''

    t = 'DEFAULT'

    if isinstance(val, (types.NoneType, types.BooleanType, types.IntType, types.LongType, types.FloatType)):
        t = 'DEFAULT'

    elif isinstance(val, dict):
        t = 'DICT'
        
    elif isinstance(val, list):
        t = 'LIST'
     
    elif isinstance(val, tuple):
        t = 'TUPLE'
      
    elif  isinstance(val, types.StringTypes): #isinstance(val, basestring):
        t = 'STRING'
    
    elif isinstance(val, BaseException):
        t = 'EXCEPTION'
    
    elif isinstance(val, types.ModuleType):
        # this has to go before the object check since a module will pass the object tests
        t = 'MODULE'
    
    elif isinstance(val, types.InstanceType) or hasattr(val, '__dict__') and not (hasattr(val, 'func_name') or hasattr(val, 'im_func')):
        t = 'OBJECT'
    
    elif isinstance(val, (types.FunctionType, types.BuiltinFunctionType)) and hasattr(val, '__call__'):
        # this has to go after object because lots of times objects can be classified as functions
        # http://stackoverflow.com/questions/624926/
        t = 'FUNCTION'
    
    else:
        t = 'DEFAULT'

    return t

def _is_magic(name):
    '''
    return true if the name is __name__
    
    since -- 7-10-12
    
    name -- string -- the name to check
    
    return -- boolean
    '''
    return (name[:2] == '__' and name[-2:] == '__')
