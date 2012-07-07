# Pout -- Easy Python variable printing

`print()` was too hard to read, `pprint` wasn't much better. I was also getting sick of typing: 
`print "var = {}".format(var)`. 

This tries to print out variables with their name, for good measure, it also prints 
where the print statement is located (so you can easily find it and delete it when you're done).

## Methods

### pout.h() -- easy way to print "here" in the code

example

    pout.h(1)
    # do something else
    pout.h(2)
    
Should print something like:

    here 1 (/file.py:line)
    
    here 2 (/file.py:line)

### pout.v(arg1, [arg2, ...]) -- easy way to print variables

example

    foo = 1
    pout.v(foo)
    
    bar = [1, 2, [3, 4], 5]
    pout.v(bar)
    
should print something like:

    foo = 1
    (/file.py:line)

    bar (4) =
    [
            0: 1,
            1: 2,
            3:
                    [
                            0: 3,
                            1: 4
                    ],
            4: 5
    ]
    (/file.py:line)

You can send as many variables as you want into the call

    # pass in as many variables as you want
    pout.v(foo, bar, che)
    
    # a multi-line call is also fine
    pout.v(
        foo,
        bar
    )

### pout.t() -- print a backtrace

Prints a nicely formatted backtrace, by default this should compact system python
calls (eg, anything in dist-packages) which makes the backtrace easier for me to
read.

example:

    pout.t()
    
should print something like:

    15 - C:\Python27\lib\runpy.py:162
    14 - C:\Python27\lib\runpy.py:72
    13 - C:\Python27\lib\unittest\__main__.py:12
    12 - C:\Python27\lib\unittest\main.py:95
    11 - C:\Python27\lib\unittest\main.py:229
    10 - C:\Python27\lib\unittest\runner.py:151
    09 - C:\Python27\lib\unittest\suite.py:65
    08 - C:\Python27\lib\unittest\suite.py:103
    07 - C:\Python27\lib\unittest\suite.py:65
    06 - C:\Python27\lib\unittest\suite.py:103
    05 - C:\Python27\lib\unittest\suite.py:65
    04 - C:\Python27\lib\unittest\suite.py:103
    03 - C:\Python27\lib\unittest\case.py:376
    02 - C:\Python27\lib\unittest\case.py:318
    01 - C:\Projects\Pout\_pout\src\test_pout.py:50
    
            pout.t()
   
## Install

Use PIP

    pip install git+https://github.com/Jaymon/pout#egg=pout

that's it, the module is still pretty basic but scratches my itch right now, I'm sure
I'll add more stuff, and fix bugs, as I find, and fix, them.

## Other Things

If, like me, you hate having to constantly do `import pout` at the top of every module you
want to use `pout` in, you can put this snippet of code in your dev environment so you no longer
have to import pout:

    # handy for dev environment, make pout available to all modules without an import
    import pout
    import __builtin__
    __builtin__.pout = pout
    
[Read more](http://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable) 
on what the above snippet does.
