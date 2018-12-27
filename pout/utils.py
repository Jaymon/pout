# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import logging

from .compat import String as BaseString, Bytes
from . import environ


class String(BaseString):
    """Small wrapper around string/unicode that guarantees output will be a real
    string ("" in py3 and u"" in py2) and won't fail with a UnicodeException"""
    def __new__(cls, arg):
        '''
        make sure arg is a unicode string

        arg -- mixed -- arg can be anything
        return -- unicode -- a u'' string will always be returned
        '''
        if isinstance(arg, Bytes):
            arg = arg.decode(environ.ENCODING, environ.ENCODING_REPLACE)

        else:
            if not isinstance(arg, BaseString):
                arg = BaseString(arg)

        return super(String, cls).__new__(cls, arg)

    def indent(self, indent_count):
        '''
        add whitespace to the beginning of each line of val

        link -- http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        val -- string
        indent -- integer -- how much whitespace we want in front of each line of val

        return -- string -- val with more whitespace
        '''
        if indent_count < 1: return self

        s = [("\t" * indent_count) + line for line in self.splitlines(False)]
        s = "\n".join(s)
        return type(self)(s)


class Stream(object):
    def __init__(self):
        # this is the pout printing logger, if it hasn't been touched it will be
        # configured to print to stderr, this is what is used in pout_class._print()
        # TODO -- make this configurable to dump to a file
        logger = logging.getLogger("{}.stream".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.StreamHandler(stream=sys.stderr)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger

    def writeline(self, s):
        self.logger.debug(s)


