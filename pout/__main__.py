# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

import sys
import os
import site
import argparse
import logging

import pout


logging.basicConfig(format="%(message)s", level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger(__name__)


class Input(str):
    """On the command line you can pass in a file or you can pipe stdin, this
    class normalizes whichever to just the proper thing we want"""
    def __new__(cls, val):
        if val:
            if os.path.isfile(val):
                path = val
                with open(path, mode="rb") as fp:
                    val = fp.read()

        else:
            # http://stackoverflow.com/questions/8478137/how-redirect-a-shell-command-output-to-a-python-script-input
            val = sys.stdin.read()

        return super(Input, cls).__new__(cls, val)


def main_json(args):
    """
    mapped to pout.j on command line, use in a pipe

    since -- 2013-9-10

        $ command-that-outputs-json | pout.json
    """
    s = Input(args.input)
    pout.j(s)
    #data = sys.stdin.readlines()
    #pout.j(os.sep.join(data))
    return 0


def main_char(args):
    """
    mapped to pout.c on the command line, use in a pipe
    since -- 2013-9-10

        $ echo "some string I want to see char values for" | pout.char
    """
    s = Input(args.input)
    pout.c(s)
    #data = sys.stdin.readlines()
    #pout.c(os.sep.join(data))
    return 0


def main_inject(args):
    """
    mapped to pout.inject on the command line, makes it easy to make pout global
    without having to actually import it in your python environment

    .. since:: 2018-08-13

    :param args: Namespace, the parsed CLI arguments passed into the application
    :returns: int, the return code of the CLI
    """
    ret = 0
    basepath = ""
    try:
        paths = site.getsitepackages()
        basepath = paths[0] 
        logger.info(
            "Found site-packages directory {} using site.getsitepackages".format(
                basepath
            )
        )

    except AttributeError:
        # we are probably running this in a virtualenv, so let's try a different
        # approach
        # try and brute-force discover it since it's not defined where it
        # should be defined
        sitepath = os.path.join(os.path.dirname(site.__file__), "site-packages")
        if os.path.isdir(sitepath):
            basepath = sitepath
            logger.info(
                "Found site-packages directory {} using site.__file__".format(
                    basepath
                )
            )

        else:
            for path in sys.path:
                if path.endswith("site-packages"):
                    basepath = path
                    logger.info(
                        "Found site-packages directory {} using sys.path".format(
                            basepath
                        )
                    )
                    break

    if basepath:
        filepath = os.path.join(basepath, "sitecustomize.py")
        with open(filepath, mode="a+") as fp:
            fp.seek(0)
            body = fp.read()
            print(body)
            if "import pout" not in body:
                #fp.write("\ntry:\n    import pout\npout.inject()\n")
                fp.write("\n".join([
                    "try:",
                    "    import pout",
                    "    pout.inject()",
                    "except ImportError: pass",
                    "",
                ]))
                logger.info("Injected pout into {}".format(filepath))
            else:
                logger.info("Pout has already been injected into {}".format(filepath))

    else:
        logger.error("Could not find site-packages directory")
        ret = 1

    return ret


def main():
    parser = argparse.ArgumentParser(description='Pout CLI')
    parser.add_argument("--version", "-V", action='version', version="%(prog)s {}".format(pout.__version__))

    # some parsers can take an input string, this is the common argument for
    # them
    parent_parser = argparse.ArgumentParser()
    parent_parser.add_argument('input', nargs="?", default=None, help="the input file, value, or pipe")

    subparsers = parser.add_subparsers(dest="command", help="a sub command")
    subparsers.required = True # https://bugs.python.org/issue9253#msg186387

    # $ pout inject
    desc = "inject pout into python builtins so it doesn't need to be imported"
    subparser = subparsers.add_parser(
        "inject",
        help=desc,
        description=desc,
        #add_help=False
        conflict_handler="resolve",
    )
    subparser.set_defaults(func=main_inject)

    # $ pout char
    desc = "Dump all the character information of each character in a string, pout.c() on the command line"
    subparser = subparsers.add_parser(
        "char",
        parents=[parent_parser],
        help=desc,
        description=desc,
        #add_help=False
        conflict_handler="resolve",
    )
    subparser.set_defaults(func=main_char)

    # $ pout json
    desc = "Pretty print json, pout.j() on the command line"
    subparser = subparsers.add_parser(
        "json",
        parents=[parent_parser],
        help=desc,
        description=desc,
        #add_help=False
        conflict_handler="resolve",
    )
    subparser.set_defaults(func=main_json)

    args = parser.parse_args()
    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()

