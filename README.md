# Pout

A collection of handy functions for printing out variables and debugging Python code.

[print](https://docs.python.org/3/library/functions.html#print) didn't give enough information while debugging, [pprint](https://docs.python.org/3/library/pprint.html) wasn't much better. I was also getting sick of typing things like: `print("var = ", var)`.

Pout tries to print out variables with their name, and for good measure, it also prints where the `pout` function was called so you can easily find it and delete it when you're done debugging.

I use pout extensively in basically every python project I work on.


## Methods

### pout.v(arg1, [arg2, ...]) -- easy way to print variables

example

```python
foo = 1
pout.v(foo)

bar = [1, 2, [3, 4], 5]
pout.v(bar)
```

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


```python
# pass in as many variables as you want
pout.v(foo, bar, che)

# a multi-line call is also fine
pout.v(
    foo,
    bar
)
```


### pout.h() -- easy way to print "here" in the code

example

```python
pout.h(1)
# do something else
pout.h(2)

# do even more of something else
pout.h()
```

Should print something like:

    here 1 (/file.py:line)

    here 2 (/file.py:line)

    here N (/file.py:N)


### pout.t() -- print a backtrace

Prints a nicely formatted backtrace, by default this should compact system python calls (eg, anything in dist-packages) which makes the backtrace easier for me to follow.

example:

```python
pout.t()
```

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

```python
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


# you can also use with
with p("benchmarking"):
    time.sleep(0.5)
```

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


### pout.x(arg1, [arg2, ...]) -- like pout.v but then will run sys.exit(1)

This just prints out where it was called from, so you can remember where you exited the code while debugging

example:
  
```python
pout.x()
```

will print something like this before exiting with an exit code of 1:

```python
exit (/file/path:n)
```


### pout.b([title[, rows[, sep]]]) -- prints lots of lines to break up output

This is is handy if you are printing lots of stuff in a loop and you want to break up the output into sections.

example:

```python
pout.b()
pout.b('this is the title')
pout.b('this is the title 2', 5)
pout.b('this is the title 3', 3, '=')
```

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

Kind of like `od -c` on the command line.

example:

```python
pout.c('this')
```

will print something like:

    Total Characters: 4
    t	't'	\u0074	LATIN SMALL LETTER T
    h	'h'	\u0068	LATIN SMALL LETTER H
    i	'i'	\u0069	LATIN SMALL LETTER I
    s	's'	\u0073	LATIN SMALL LETTER S
    (/file/path:n)

This could fail if Python isn't compiled with 4 byte unicode support, just something to be aware of, but chances are, if you don't have 4 byte unicode supported Python, you're not doing much with 4 byte unicode.


### pout.s(arg1, [arg2, ...]) -- easy way to return pretty versions of variables

  Just like `pout.v()` but will return the value as a string


### pout.ss(arg1, [arg2, ...]) -- easy way to return pretty versions of variables without meta information

  Just like `pout.vv()` but will return the value as a string


### pout.l([logger_name, [logger_level]]) -- turn logging on just for this context

Turns logging on for the given level (defaults to `logging.DEBUG`) and prints the logs to __stderr__. Useful when you just want to check the logs of something without modifying your current logging configuration.

example:

```python
with pout.l():
    logger.debug("This will print to the screen even if logging is off")
logger.debug("this will not print if logging is off")

with pout.l("name"):
    # if "name" logger is used it will print to stderr
# "name" logger goes back to previous configuration
```

### pout.tofile([path])

Routes pout's output to a file (defaults to `./pout.txt`)

example:

```python
with pout.tofile():
	# everything in this with block will print to a file in current directory
	pout.b()
	s = "foo"
	pout.v(s)
	
pout.s() # this will print to stderr
```


## Customizing Pout

### object magic method

Any class object can define a `__pout__` magic method, similar to Python's built in `__str__` magic method that can return a customized string of the object if you want to. This method can return anything, it will be run through Pout's internal stringify methods to convert it to a string and print it out.


## Console commands

### pout json

running a command on the command line that outputs a whole a bunch of json? Pout can help:

    $ some-command-that-outputs-json | pout json


### pout char

Runs `pout.c` but on the output from a command line script:

    $ echo "some string with chars to analyze" | pout char


## Install

Use PIP

    pip install pout

Generally, the pypi version and the github version shouldn't be that out of sync, but just in case, you can install from github also:

    pip install -U "git+https://github.com/Jaymon/pout#egg=pout"


-------------------------------------------------------------------------------

## Make Pout easier to use

When debugging, it's really nice not having to put `import pout` at the top of every module you want to use it in, so there's a command for that, if you put:

```python
import pout
pout.inject()
```

Somewhere near the top of your application startup script, then `pout` will be available in all your files whether you imported it or not, it will be just like `str`, `object`, or the rest of python's standard library.

If you don't even want to bother with doing that, then just run:

```
$ pout inject
```

from the command line and it will modify your python environment to make pout available as a builtin module, just like the python standard library. This is super handy for development virtual environments.

