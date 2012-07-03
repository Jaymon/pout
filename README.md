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
