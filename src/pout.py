"""
prints out variables and other handy things to help with debugging

print was too hard to read, pprint wasn't much better. I was getting sick of typing: 
print "var name: {}".format(var). This tries to print out variables with their name, 
and where the print statement was called (so you can easily find it and delete it later).

link -- http://stackoverflow.com/questions/3229419/pretty-printing-nested-dictionaries-in-python
link -- http://docs.python.org/library/pprint.html
link -- http://docs.python.org/library/inspect.html

in the future, to list method arguments:
link -- http://stackoverflow.com/questions/3517892/python-list-function-argument-names

note -- this is still really basic, I'm adding things as I need them

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

def h(count=0):
    '''
    prints "here count"
    
    example -- 
        h(1) # here 1 (/file:line)
        h() # here line (/file:line)
        

    count -- integer -- the number you want to put after "here"
    '''

    call_info = _get_arg_info()
    args = ["here {} ".format(count if count > 0 else call_info['line'])]
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
    
    args = ["{}\n\n".format(_str(v['name'], v['val'])) for v in call_info['args']]
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
        sys.stderr.write(str(arg))
        
    sys.stderr.write("({}:{})\n\n".format(call_info['file'], call_info['line']))
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
    
    if isinstance(val, (dict, list, tuple)):
    
        count = len(val)
        s = "{} ({}) = {}".format(name, count, _str_val(val, depth=0))
       
    else:
        if name:
            s = "{} = {}".format(name, _str_val(val))
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

    s = ''
    if isinstance(val, dict):
        
        if len(val) > 0:
        
            s = _str_iterator(
                iterator=val.iteritems(), 
                name_callback= lambda k: "'{}'".format(k),
                left_paren='{', 
                right_paren='}',
                depth=depth
            )
            
        else:
            s = "{}"
        
    
    elif isinstance(val, list):
    
        if len(val) > 0:
      
            s = _str_iterator(iterator=enumerate(val), depth=depth)
      
        else:
            s = "[]"
     
    elif isinstance(val, tuple):

        if len(val) > 0:
      
            s = _str_iterator(iterator=enumerate(val), left_paren='(', right_paren=')', depth=depth)
      
        else:
            s = "()"
      
    elif isinstance(val, basestring):
        s = '"{}"'.format(str(val))
    
    elif isinstance(val, BaseException):
    
        # http://docs.python.org/library/traceback.html
        # http://www.doughellmann.com/PyMOTW/traceback/
        # http://stackoverflow.com/questions/4564559
        # http://stackoverflow.com/questions/6626342
    
        full_name = _get_name(val)
        exc_type, exc_value, exc_tb = sys.exc_info()
        
        # todo -- go through the traceback and collapse site-packages files as they make
        # the traceback a lot harder to read and most of the time the problem is in our
        # code
        
        s = "{} - {}\n\n{}".format(full_name, val, "".join(traceback.format_exception(exc_type, exc_value, exc_tb)))
    
    elif hasattr(val, '__dict__'):
        
        d = {}
        full_name = _get_name(val)
        to_string = ''
        if hasattr(val, '__str__'):
            to_string = '{}'.format(str(val))
        
        if depth < 2:
        
            # this would get into a recursion error when used with Django models
            #d = {k: v for k, v in inspect.getmembers(val) if not callable(getattr(val,k)) and (k[:2] != '__' and k[-2:] != '__')}
            
            # todo -- vars does not get class members
            d = vars(val)
            d["__str__"] = to_string
        
            # http://stackoverflow.com/questions/109087/python-get-instance-variables
            
            s = _str_iterator(
                iterator=d.iteritems(), 
                prefix="{} instance\n".format(full_name),
                left_paren='<', 
                right_paren='>',
                depth=depth
            )
            
        else:
            s = '{} instance\n"{}"'.format(full_name, to_string)
        
    else:
        s = str(val)

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
    
    arg_vals -- list -- the arguments passed to one of the public methods
    back_i -- integer -- how far back in the stack the method call was
    
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
        ret_dict['frame'] = frames[back_i]
        ret_dict['line'] = frames[back_i][2]
        ret_dict['file'] = os.path.abspath(inspect.getfile(frames[back_i][0]))
    
    # build the arg list if values have been passed in
    if len(arg_vals) > 0:
        
        args = []
        
        if frames[back_i][4] is not None:
            
            #print frames[back_i][0].f_code
            print frames[back_i]
            
            stack_paren = []
            stack_bracket = []
            stack_quote = []
            has_name = True
            arg_build = False
            arg_name = ''
            arg_names = []
            
            for c in frames[back_i][4][0]:
            
                if c == '(' and (len(stack_quote) == 0):
                    stack_paren.append(c)
                    if len(stack_paren) == 1:
                        # we've found the first paren of the pout call
                        arg_build = True
                        continue
                
                elif c == ')' and (len(stack_quote) == 0):
                    stack_paren.pop()
                    
                    if len(stack_paren) == 0:
                        arg_names.append(arg_name if has_name else '')
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
                        arg_names.append(arg_name if has_name else '')
                        has_name = True
                        arg_name = ''
                        continue
                
                if arg_build:
                    arg_name += c
            
            # match the found arg names to their respective values
            for i, arg_name in enumerate(arg_names):
                args.append({'name': arg_name.strip(), 'val': arg_vals[i]})
            
        else:
            # we can't autodiscover the names, in an interactive shell session?
            for i, arg_val in enumerate(arg_vals):
                args.append({'name': 'Unknown {}'.format(i), 'val': arg_val})
            
        ret_dict['args'] = args    
    
    return ret_dict

