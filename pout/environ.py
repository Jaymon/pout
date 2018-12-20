# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import codecs


ENCODING = os.environ.get("POUT_ENCODING", "UTF-8")
ENCODING_REPLACE = os.environ.get("POUT_ENCODING_REPLACE", "pout.replace")


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

