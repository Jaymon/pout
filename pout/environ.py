# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import codecs
import uuid

from .compat import *


DEBUG = bool(int(os.environ.get("POUT_DEBUG", 0)))
"""Set this to turn on debug output that is more verbose than pout's normal output, 
this is handy when trying to figure out what pout is doing and why it is failing, mainly
handy for writing tests and adding functionality, normally pout's logger is the NullHandler
"""


ENCODING = os.environ.get("POUT_ENCODING", "UTF-8")
"""The encoding pout will use internally"""


ENCODING_REPLACE_METHOD = os.environ.get(
    "POUT_ENCODING_REPLACE_METHOD",
    "pout.replace.{}".format(uuid.uuid4().hex) # unique value so we can perform lookup
)
"""The method to replace bad unicode characters, normally you shouldn't have to mess
with this"""


# https://en.wikipedia.org/wiki/Specials_(Unicode_block)#Replacement_character
ENCODING_REPLACE_CHAR = String(os.environ.get("POUT_ENCODING_REPLACE_CHAR", String("\uFFFD")))
"""The character used to replace bad unicode characters, I previously used the period but 
figured I should use the actual replacement character"""


OBJECT_DEPTH = int(os.environ.get("POUT_OBJECT_DEPTH", 3))
"""Change this to set how far down in depth pout will print instances with full
ObjectValue output while it is compiling the value for the passed in instance.

some objects have many layers of nested objects which makes their pout.v() output
annoying, but setting this to like 1 would cause all those nested instances to just
have repr(instance) be printed instead"""


ITERATE_LIMIT = int(os.environ.get("POUT_ITERATE_LIMIT", os.environ.get("POUT_ITERATOR_LIMIT", 101)))
"""Change this to limit how many rows of list/set/etc and how many keys of dict you
want to print out. Turns out, after so many it becomes a pain to actually inspect
the object"""


#INDENT_STRING = os.environ.get("POUT_INDENT_STRING", "\t")
INDENT_STRING = os.environ.get("POUT_INDENT_STRING", "    ")
"""This is what pout uses to indent when it is creating the output"""


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
    raise ValueError("{} has already been registered".format(ENCODING_REPLACE_METHOD))

