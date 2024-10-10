# -*- coding: utf-8 -*-
import os
import codecs
import uuid
import sys

from .compat import *


DEBUG = bool(int(os.environ.get("POUT_DEBUG", 0)))
"""Set this to turn on debug output that is more verbose than pout's normal
output, this is handy when trying to figure out what pout is doing and why it is
failing, mainly handy for writing tests and adding functionality, normally
pout's logger is the NullHandler
"""


ENCODING = os.environ.get("POUT_ENCODING", "UTF-8")
"""The encoding pout will use internally"""


ENCODING_REPLACE_METHOD = os.environ.get(
    "POUT_ENCODING_REPLACE_METHOD",
    "pout.replace.{}".format(uuid.uuid4().hex) # unique value so we can lookup
)
"""The method to replace bad unicode characters, normally you shouldn't have to
mess with this"""


# https://en.wikipedia.org/wiki/Specials_(Unicode_block)#Replacement_character
ENCODING_REPLACE_CHAR = String(os.environ.get(
    "POUT_ENCODING_REPLACE_CHAR",
    String("\uFFFD")
))
"""The character used to replace bad unicode characters, I previously used the
period but figured I should use the actual replacement character"""


SHOW_SIMPLE_PREFIX = bool(int(os.environ.get(
    "POUT_SHOW_SIMPLE_PREFIX",
    False
)))
"""This flips SHOW_INSTANCE_ID and SHOW_INSTANCE_TYPE to its value"""


SHOW_SIMPLE_VALUE = bool(int(os.environ.get("POUT_SHOW_SIMPLE_VALUE", True)))
"""This displays simple values for Value subclasses that support it

This has to be specifically supported by a Value subclass to have any effect

see: https://github.com/Jaymon/pout/issues/95
"""


SHOW_COLOR = bool(int(os.environ.get("POUT_SHOW_COLOR", True)))
"""Set to True for pout to use color if the terminal supports it"""


OBJECT_DEPTH = int(os.environ.get("POUT_OBJECT_DEPTH", 5))
"""Change this to set how far down in depth pout will print instances with full
ObjectValue output while it is compiling the value for the passed in instance.

some objects have many layers of nested objects which makes their pout.v()
output annoying, but setting this to like 1 would cause all those nested
instances to just have repr(instance) be printed instead"""


OBJECT_STRING_LIMIT = int(os.environ.get("POUT_OBJECT_STR_LIMIT", 500))
"""Limits the length of an object's __str__() method output"""


ITERATE_LIMIT = int(os.environ.get(
    "POUT_ITERATE_LIMIT",
    os.environ.get("POUT_ITERATOR_LIMIT", 101)
))
"""Change this to limit how many rows of list/set/etc and how many keys of dict
you want to print out. Turns out, after so many it becomes a pain to actually
inspect the object"""


#INDENT_STRING = os.environ.get("POUT_INDENT_STRING", "\t")
INDENT_STRING = os.environ.get("POUT_INDENT_STRING", "    ")
"""This is what pout uses to indent when it is creating the output"""


KEY_QUOTE_CHAR = os.environ.get("POUT_KEY_QUOTE_CHAR", "\'")
"""pout will use this quotation character to wrap dict keys"""

# we do some tricksy normalizing here for environments where it is
# hard to set the actual quote value in a variable, I was getting a
# bunch of errors like: "unterminated quote" when trying to just set
# a quote value in my environment
if KEY_QUOTE_CHAR == "DOUBLE":
    KEY_QUOTE_CHAR = "\""

elif KEY_QUOTE_CHAR == "SINGLE":
    KEY_QUOTE_CHAR = "'"


def handle_decode_replace(e):
    """this handles replacing bad characters when printing out

    http://www.programcreek.com/python/example/3643/codecs.register_error
    http://bioportal.weizmann.ac.il/course/python/PyMOTW/PyMOTW/docs/codecs/index.html
    https://pymotw.com/2/codecs/
    """
    count = e.end - e.start
    #return "." * count, e.end

    global ENCODING_REPLACE_CHAR
    return ENCODING_REPLACE_CHAR * count, e.end


# register our decode replace method when encoding
try:
    codecs.lookup_error(ENCODING_REPLACE_METHOD)

except LookupError:
    codecs.register_error(ENCODING_REPLACE_METHOD, handle_decode_replace)

else:
    raise ValueError(
        "{} has already been registered".format(ENCODING_REPLACE_METHOD)
    )


def has_color_support():
    """
    This is a simplified version of:
        https://github.com/django/django/blob/main/django/core/management/color.py
    """
    global SHOW_COLOR

    return (
        SHOW_COLOR
        and hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and (
            sys.platform != "win32"
            or "ANSICON" in os.environ
            or
            # Windows Terminal supports VT codes.
            "WT_SESSION" in os.environ
            or
            # Microsoft Visual Studio Code's built-in terminal supports colors.
            os.environ.get("TERM_PROGRAM") == "vscode"
        )
    )

