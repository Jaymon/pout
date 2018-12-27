# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import codecs


DEBUG = bool(int(os.environ.get("POUT_DEBUG", 0)))
"""Set this to turn on debug output that is more verbose than pout's normal output, 
this is handy when trying to figure out what pout is doing and why it is failing, mainly
handy for writing tests and adding functionality, normally pout's logger is the NullHandler
"""

ENCODING = os.environ.get("POUT_ENCODING", "UTF-8")
"""The encoding pout will use internally"""

ENCODING_REPLACE = os.environ.get("POUT_ENCODING_REPLACE", "pout.replace")
"""The method to replace bad unicode characters, normally you shouldn't have to mess
with this"""

OBJECT_DEPTH = int(os.environ.get("POUT_OBJECT_DEPTH", 4))
"""Change this to set how far down in depth pout will wrap instances with an
ObjectValue instance while it is compiling the value for the passed in instance.

some objects have many layers of nested objects which makes their pout.v() output
annoying, but setting this to like 1 would cause all those nested instances to just
have repr(instance) be printed instead"""


def handle_decode_replace(cls, e):
    """this handles replacing bad characters when printing out

    http://www.programcreek.com/python/example/3643/codecs.register_error
    http://bioportal.weizmann.ac.il/course/python/PyMOTW/PyMOTW/docs/codecs/index.html
    https://pymotw.com/2/codecs/
    """
    count = e.end - e.start
    return "." * count, e.end


# register our decode replace method when encoding
codecs.register_error(ENCODING_REPLACE, handle_decode_replace)

