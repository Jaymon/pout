"""
prints out variables and other handy things to help with debugging

print was too hard to read, pprint wasn't much better. I was getting sick of typing: 
print "var name: {}".format(var). This tries to print out variables with their name, 
and where the print statement was called (so you can easily find it and delete it later).

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
    
    args = ["{}\n".format(_str(k, v)) for k, v in call_info['args'].items()]
    _print(args, call_info)

def _print(args, call_info):
    '''
    handle printing args to the screen
    
    currently, we use stderr

    link -- http://stackoverflow.com/questions/5574702/how-to-print-to-stderr-in-python
    
    args -- list -- the list of string args to print
    call_info -- dict -- returned from _get_arg_info()
    '''

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
    
    if isinstance(val, dict):
    
        count = len(val)
        s = "{} ({}) = {}".format(name, count, _str_val(val, depth=0))
       
    elif isinstance(val, list):
    
        count = len(val)
        s = "{} ({}) = {}".format(name, count, _str_val(val, depth=0))
    
    else:
        s = "{} = {}".format(name, _str_val(val))
    
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
        
    elif isinstance(val, basestring):
        s = '"{}"'.format(str(val))
        
    elif hasattr(val, '__dict__'):
    
        # http://stackoverflow.com/questions/109087/python-get-instance-variables
        s = _str_iterator(
            iterator={k: v for k, v in inspect.getmembers(val) if not callable(getattr(val,k)) and (k[:2] != '__' and k[-2:] != '__')}.iteritems(), 
            prefix="{}\n".format(val.__class__),
            left_paren='<', 
            right_paren='>',
            depth=depth
        )
        
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
        s_body += "{}: {},\n".format(k, _str_val(v, depth=depth+1))
    
    s_body = s_body.rstrip(",\n")
    s_body = _add_indent(s_body, indent + 1)
    
    s += s_body
    s += "\n{}".format(_add_indent(right_paren, indent))
    
    return s

def _add_indent(val, indent):
    '''
    add whitespace to the beginning of each line of val
    
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
    
    ret_dict = {}
    args = {}
    
    back_i += 2 # move past the call to the outer frames and the call to this function
    frame = inspect.currentframe()
    frames = inspect.getouterframes(frame)
    
    ret_dict['frame'] = frames[back_i]
    ret_dict['line'] = frames[back_i][2]
    ret_dict['file'] = os.path.abspath(inspect.getfile(frames[back_i][0]))
    
    # build the arg list if values have been passed in
    if len(arg_vals) > 0:
        
        # first thing we need to do is move to the first paren:
        append = False
        arg_str = ''
        for c in frames[back_i][4][0]:
    
            if c == '(':
                append = True
                continue
            elif c == ')':
                append = False
                continue
        
            if append:
                arg_str += c
        
        for i, arg_name in enumerate([x.strip() for x in arg_str.split(',')]):
            args[arg_name] = arg_vals[i]
        
        ret_dict['args'] = args
    
    return ret_dict

