# -*- coding: utf-8 -*-
import sys
import logging
import re
import textwrap

from .compat import String as BaseString, Bytes
from . import environ


class String(BaseString):
    """Small wrapper around string/unicode that guarantees output will be a real
    string ("" in py3 and u"" in py2) and won't fail with a UnicodeException"""

    types = (BaseString,)

    def __new__(cls, arg):
        """make sure arg is a unicode string

        :param arg: mixed, arg can be anything
        :returns: unicode, a u"" string will always be returned
        """
        try:
            if isinstance(arg, Bytes):
                arg = arg.decode(
                    environ.ENCODING,
                    errors=environ.ENCODING_REPLACE_METHOD
                )

            else:
                if not isinstance(arg, BaseString):
                    try:
                        arg = BaseString(arg)
                    except TypeError:
                        # this error can happen if arg.__str__() doesn't return
                        # a string, so we call the method directly and go back
                        # through the __new__() flow
                        if hasattr(arg, "__str__"):
                            arg = cls(arg.__str__())

        except RuntimeError as e:
            arg = e

        return super().__new__(cls, arg)

    def truncate(self, size, postfix="", sep=None): # copied from datatypes
        """similar to a normal string slice but it actually will split on a word
        boundary

        :Example:
            s = "foo barche"
            print s[0:5] # "foo b"
            s2 = String(s)
            print s2.truncate(5) # "foo"

        truncate a string by word breaks instead of just length
        this will guarantee that the string is not longer than length, but it
        could be shorter

        * http://stackoverflow.com/questions/250357/smart-truncate-in-python/250373#250373
        * This was originally a method called word_truncate by Cahlan Sharp for
          Undrip.
        * There is also a Plancast Formatting.php substr method that does
          something similar

        :param size: int, the size you want to truncate to at max
        :param postfix: str, what you would like to be appended to the
            truncated string
        :param sep: str, by default, whitespace is used to decide where to
            truncate the string, but if you pass in something for sep then that
            will be used to truncate instead
        :returns: str, a new string, truncated
        """
        if len(self) < size:
            return self

        # our algo is pretty easy here, it truncates the string to size -
        # postfix size then right splits the string on any whitespace for a
        # maximum of one time and returns the first item of that split right
        # stripped of whitespace (just in case)
        postfix = type(self)(postfix)
        ret = self[0:size - len(postfix)]
        # if rsplit sep is None, any whitespace string is a separator
        ret = ret[:-1].rsplit(sep, 1)[0].rstrip()
        return type(self)(ret + postfix)

    def indent(self, indent, count=1): # copied from datatypes
        """add whitespace to the beginning of each line of val

        http://code.activestate.com/recipes/66055-changing-the-indentation-of-a-multi-line-string/

        :param indent: str, what you want the prefix of each line to be
        :param count: int, how many times to apply indent to each line
        :returns: str, string with prefix at the beginning of each line
        """
        if not indent:
            return self

        s = ((indent * count) + line for line in self.splitlines(True))
        s = "".join(s)
        return type(self)(s)

    def dedent(self):
        """Dedent common whitespace from the string

        https://docs.python.org/3/library/textwrap.html

        :returns: str, a new string instance with removed common whitespace
        """
        return type(self)(textwrap.dedent(self))

    def camelcase(self):
        """Convert a string to use camel case (spaces removed and capital
        letters)"""
        return "".join(map(lambda s: s.title(), re.split(r"[_-]+", self)))

    def snakecase(self):
        """Convert a string to use snake case (lowercase with underscores in
        place of spaces)"""
        s = []
        prev_ch_was_lower = False

        for i, ch in enumerate(self):
            if ch.isupper():
                if i and prev_ch_was_lower:
                    s.append("_")

                prev_ch_was_lower = False

            else:
                prev_ch_was_lower = True

            s.append(ch)
        return re.sub(r"[\s-]+", "_", "".join(s)).lower()

    def __format__(self, format_str):
        return String(self)


class Stream(object):
    """A Stream object that pout needs to be able to write to something, an
    instance of some stream instance needs to be set in pout.stream.

    The only interface this object needs is the writeline() function, I thought
    about using an io ABC but that seemed more complicated than it was worth

    https://docs.python.org/3/library/io.html#class-hierarchy
    """
    def writeline(self, s):
        """write out a line and add a newline at the end

        the requirement for the newline is because the children use the logging
        module and it prints a newline at the end by default in 2.7 (you can
        override it in >3.2)

        :param s: string, this will be written to the stream and a newline will
            be added to the end
        """
        raise NotImplementedError()


class StderrStream(Stream):
    """A stream object that writes out to stderr"""
    def __init__(self):
        # this is the pout printing logger, if it hasn't been touched it will be
        # configured to print to stderr, this is what is used in
        # pout_class._print()
        logger = logging.getLogger("stderr.{}".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.StreamHandler(stream=sys.stderr)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger

    def writeline(self, s):
        self.logger.debug(String(s))


class FileStream(StderrStream):
    """A stream object that writes to a file path passed into it"""
    def __init__(self, path):
        logger = logging.getLogger("file.{}".format(__name__.split(".")[0]))
        if len(logger.handlers) == 0:
            logger.setLevel(logging.DEBUG)
            log_handler = logging.FileHandler(path)
            log_handler.setFormatter(logging.Formatter('%(message)s'))
            logger.addHandler(log_handler)
            logger.propagate = False

        self.logger = logger


class OrderedItems(object):
    """Returns the items of the wrapped dict in alphabetical/sort order of the
    keys"""
    def __init__(self, d: dict):
        self.d = d

    def __iter__(self):
        keys = list(self.d.keys())
        keys.sort()
        for k in keys:
            yield k, self.d[k]


class Color(object):
    @classmethod
    def color_header(cls, text):
        return cls.color(text, bold=True)

    @classmethod
    def color_meta(cls, text):
        return cls.color(text, "LIGHTGRAY")

    @classmethod
    def color_string(cls, text):
        return cls.color(text, "RED")

    @classmethod
    def color_key(cls, text):
        return cls.color(text, "CYAN")

    @classmethod
    def color_attr(cls, text):
        return cls.color(text, "BLUE")

    @classmethod
    def color_number(cls, text):
        return cls.color(text, "MAGENTA")

    @classmethod
    def color(cls, text, fg="", bg="", **kwargs):
        """Wrap text in fg and bg color

        See:
            - https://github.com/Jaymon/pout/issues/94
            - https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
            - https://unix.stackexchange.com/questions/105568/

        Based off of this:
            https://github.com/django/django/blob/main/django/utils/termcolors.py

        The supported color names:
            - BLACK
            - RED
            - GREEN
            - YELLOW
            - BLUE
            - MAGENTA
            - CYAN
            - WHITE

        :param text: str, the text to wrap with fg and bg colors
        :param fg: str, the foreground color
        :param bg: str, the background color
        :param **kwargs:
            - bold: bool, True to make text bold
            - underline: bool, True to underline text
        :returns: str, text wrapped with terminal color if supported
        """
        if text and environ.has_color_support():

            color_names = (
                "BLACK",
                "RED",
                "GREEN",
                "YELLOW",
                "BLUE",
                "MAGENTA",
                "CYAN",
                "WHITE"
            )
            foreground = {color_names[x]: f"3{x}" for x in range(8)}
            background = {color_names[x]: f"4{x}" for x in range(8)}

            # bright versions
            for x in range(8):
                foreground[f"BRIGHT{color_names[x]}"] = f"9{x}"
                background[f"BRIGHT{color_names[x]}"] = f"10{x}"

            foreground["NONE"] = 0

            aliases = [
                ("LIGHTGRAY", "WHITE"),
                ("BRIGHTGRAY", "BRIGHTBLACK"),
                ("GRAY", "WHITE"),
                ("PURPLE", "MAGENTA"),
            ]
            for k1, k2 in aliases:
                foreground[k1] = foreground[k2]
                background[k1] = background[k2]

            options = {
                "bold": "1",
                "underscore": "4",
                "underline": "4",
                "blink": "5",
                "reverse": "7",
                "conceal": "8",
            }

            codes = []
            if fg:
                codes.append(foreground[fg.upper()])

            if bg:
                codes.append(background[bg.upper()])

            for k, v in kwargs.items():
                if v:
                    k = k.lower()
                    if options.get(k, False):
                        codes.append(options[k])

            color = reset = ""
            if codes:
                color = "\033[{}m".format(";".join(codes))
                reset = "\033[{}m".format(foreground["NONE"])

            text = f"{color}{text}{reset}"

        return text

