# Pout

A collection of handy functions for printing out variables and debugging code.

`print()` was too hard to read, `pprint` wasn't much better. I was also getting sick of typing: `print "var = {}".format(var)`. 

This tries to print out variables with their name, and for good measure, it also prints where the pout function was called from, so you can easily find it and delete it when you're done.

## Methods

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
            2:
                    [
                            0: 3,
                            1: 4
                    ],
            3: 5
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

### pout.h() -- easy way to print "here" in the code

example

    pout.h(1)
    # do something else
    pout.h(2)
    
    # do even more of something else
    pout.h()
    
Should print something like:

    here 1 (/file.py:line)
    
    here 2 (/file.py:line)

    here (/file.py:line)

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
   
### pout.p([title]) -- quick and dirty profiling

example

    p("starting profile")
    time.sleep(1)
    p() # stop the "starting profile" session

    # you can go N levels deep
    p("one")
    p("two")
    time.sleep(0.5)
    p() # stop profiling of "two"
    time.sleep(0.5)
    p() # stop profiling of "one"

should print something like:

    starting profile - 1008.2 ms
      start: 1368137723.7 (/file/path:n)
      stop: 1368137724.71(/file/path:n)


    one > two - 509.2 ms
      start: 1368137722.69 (/file/path:n)
      stop: 1368137723.2(/file/path:n)


    one - 1025.9 ms
      start: 1368137722.68 (/file/path:n)
      stop: 1368137723.7(/file/path:n)

### pout.x([exit_code]) -- like sys.exit(exit_code)

This just prints out where it was called from, so you can remember where you exited the code
while debugging

example:
  
    pout.x()

will print something like this before exiting with an exit code of 1:

    exit (/file/path:n)


### pout.b([title[, rows[, sep]]]) -- prints lots of lines to break up output

This is is handy if you are printing lots of stuff in a loop and you want to break up
the output into sections

example:

    pout.b()
    pout.b('this is the title')
    pout.b('this is the title 2', 5)
    pout.b('this is the title 3', 3, '=')

Would result in output like:

    ********************************************************************************
    (/file/path:n)


    ****************************** this is the title *******************************
    (/file/path:n)


    ********************************************************************************
    ********************************************************************************
    ***************************** this is the title 2 ******************************
    ********************************************************************************
    ********************************************************************************
    (/file/path:n)


    ================================================================================
    ============================= this is the title 3 ==============================
    ===============================================================================
    (/file/path:n)

### pout.c(str1, [str2, ...]) -- print info about each char in each str

Kind of like `od -c`

example:

    pout.c('this')

will print something like:

    Total Characters: 4
    t	't'	\u0074	LATIN SMALL LETTER T
    h	'h'	\u0068	LATIN SMALL LETTER H
    i	'i'	\u0069	LATIN SMALL LETTER I
    s	's'	\u0073	LATIN SMALL LETTER S
    (/file/path:n)

This could fail if Python isn't compiled with 4 byte unicode support, just something
to be aware of, but chances are, if you don't have 4 byte unicode supported Python, you're
not doing much with 4 byte unicode.

## Console commands

### pout.json

running a command on the command line that outputs a whole a bunch of json? Pout can help:

    $ some-command-that-outputs-json | pout.json

### pout.char

Runs `pout.c` but on the output from a command line script:

    $ echo "some string with chars to analyze" | pout.char

## Install

Use PIP

    pip install pout

Generally, the pypi version and the github version shouldn't be that out of sync, but just in case, you can install from github also:

    pip install git+https://github.com/Jaymon/pout#egg=pout

## Make Pout easier to use

### Add pout to a configuration file for your app

If, like me, you hate having to constantly do `import pout` at the top of every module you
want to use `pout` in, you can put this snippet of code in your dev environment so you no longer
have to import pout:

    # handy for dev environment, make pout available to all modules without an import
    import __builtin__
    try:
      import pout
      __builtin__.pout = pout
    except ImportError:
      pass
      
[Read more](http://stackoverflow.com/questions/142545/python-how-to-make-a-cross-module-variable) 
on what the above snippet does.

### Add pout to usercustomize.py

run this in terminal:

    $ python -c "import site; site._script()"

if at the end you see something like this:

    USER_BASE: '/home/USERNAME/.local' (exists)
    USER_SITE: '/home/USERNAME/.local/lib/python2.7/site-packages' (exists)
    ENABLE_USER_SITE: True

that means you can add a usercustomize.py module:

    $ mkdir -p ~/.local/lib/python2.7/site-packages
    $ touch ~/.local/lib/python2.7/site-packages/usercustomize.py

that will be included every time python is ran and so you can put this code in:

    import __builtin__
    try:
      import pout
      __builtin__.pout = pout
    except ImportError:
      pass

### Add pout to sitecustomize.py

run this in terminal:

    $ python -c "import site; print site.getsitepackages()[0]

That should print out a good place to add a `sitecustomize.py` file. Create that file and include the pout import code in it.

### Add pout to site.py

If none of the above options work for you, you can also actually edit Python's `site.py` file. If you do this, you should most definitely only ever do it on your dev box in your dev environment, I would **NOT** do something like this on a production server:

1 - Find the `site.py` file for your python installation

You can find where your python installation lives through the Python shell:

    $ python
    >>> import sys
    >>> sys.prefix
    '/path/to/python/install'

2 - Go to that directory's `lib/pythonX.Y` directory

So, if you were using Python 2.7, you would go to `/path/to/python/install/lib/python2.7`

3 - edit the `site.py` file
    
add this to somewhere near the end of the `site.py` file

    try:
      import pout
      __builtin__.pout = pout
    except ImportError:
      pass

4 - Now any python code will be able to use `pout` without you having to explicitely import it.

[Read more](http://docs.python.org/2/library/site.html), also [here](http://stackoverflow.com/a/8255752)

## Bugs

This doesn't work:

    if hasattr(self, name): pout.v(name); return object.__setattr__(self, name, val)

