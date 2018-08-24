# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

import sys
import os
import site
import argparse
import logging
import platform
import inspect

import pout


level = logging.INFO
logging.basicConfig(format="%(message)s", level=level, stream=sys.stdout)
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


class SitePackagesDir(str):
    """Finds the site-packages directory and sets the value of this string to that
    path"""
    def __new__(cls):
        basepath = ""
        try:
            paths = site.getsitepackages()
            basepath = paths[0] 
            logger.debug(
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
                logger.debug(
                    "Found site-packages directory {} using site.__file__".format(
                        basepath
                    )
                )

            else:
                for path in sys.path:
                    if path.endswith("site-packages"):
                        basepath = path
                        logger.debug(
                            "Found site-packages directory {} using sys.path".format(
                                basepath
                            )
                        )
                        break

                if not basepath:
                    for path in sys.path:
                        if path.endswith("dist-packages"):
                            basepath = path
                            logger.debug(
                                "Found dist-packages directory {} using sys.path".format(
                                    basepath
                                )
                            )
                            break

        if not basepath:
            raise IOError("Could not find site-packages directory")

        return super(SitePackagesDir, cls).__new__(cls, basepath)


class SiteCustomizeFile(str):
    """sets the value of the string to the sitecustomize.py file, and adds handy
    helper functions to manipulate it"""
    @property
    def body(self):
        if not self.exists():
            return ""

        with open(self, mode="r") as fp:
            return fp.read()

    def __new__(cls):
        filepath = ""
        if "sitecustomize" in sys.modules:
            filepath = inspect.getsourcefile(sys.modules["sitecustomize"])
            # !!! I have doubts this if block is needed
            if filepath and not filepath.endswith(".py"):
                filepath = ""
                for path in sys.path:
                    p = os.path.join(path, "sitecustomize.py")
                    if os.path.isfile(p):
                        filepath = p
                        break

        if not filepath:
            basepath = SitePackagesDir()
            filepath = os.path.join(basepath, "sitecustomize.py")

        instance = super(SiteCustomizeFile, cls).__new__(cls, filepath)
        return instance

    def inject(self):
        """inject code into sitecustomize.py that will inject pout into the builtins
        so it will be available globally"""
        if self.is_injected():
            return False

        with open(self, mode="a+") as fp:
            fp.seek(0)
            fp.write("\n".join([
                "",
                "try:",
                "    import pout",
                "except ImportError:",
                "    pass",
                "else:",
                "    pout.inject()",
                "",
            ]))

        return True

    def exists(self):
        return os.path.isfile(self)

    def is_injected(self):
        body = self.body
        return "import pout" in body


def main_inject(args):
    """
    mapped to pout.inject on the command line, makes it easy to make pout global
    without having to actually import it in your python environment

    .. since:: 2018-08-13

    :param args: Namespace, the parsed CLI arguments passed into the application
    :returns: int, the return code of the CLI
    """
    ret = 0

    try:
        filepath = SiteCustomizeFile()
        if filepath.is_injected():
            logger.info("Pout has already been injected into {}".format(filepath))

        else:
            if filepath.inject():
                logger.info("Injected pout into {}".format(filepath))
            else:
                logger.info("Failed to inject pout into {}".format(filepath))

    except IOError as e:
        ret = 1
        logger.info(str(e))

    return ret


def main_info(args):
    """Just prints out info about the pout installation

    .. since:: 2018-08-20

    :param args: Namespace, the parsed CLI arguments passed into the application
    :returns: int, the return code of the CLI
    """
    if args.site_packages:
        logger.info(SitePackagesDir())

    else:
        logger.info("Python executable: {}".format(sys.executable))
        logger.info("Python version: {}".format(platform.python_version()))
        logger.info("Python site-packages: {}".format(SitePackagesDir()))
        logger.info("Python sitecustomize: {}".format(SiteCustomizeFile()))
        # https://stackoverflow.com/questions/4152963/get-the-name-of-current-script-with-python
        #logger.info("Pout executable: {}".format(subprocess.check_output(["which", "pout"])))
        logger.info("Pout executable: {}".format(os.path.abspath(os.path.expanduser(str(sys.argv[0])))))
        logger.info("Pout version: {}".format(pout.__version__))

        filepath = SiteCustomizeFile()
        logger.info("Pout injected: {}".format(filepath.is_injected()))


def main():
    #parser = argparse.ArgumentParser(description='Pout CLI', conflict_handler="resolve")
    parser = argparse.ArgumentParser(description='Pout CLI')
    parser.add_argument("--version", "-V", action='version', version="%(prog)s {}".format(pout.__version__))
    parser.add_argument("--debug", "-d", action="store_true", help="More verbose logging")

    # some parsers can take an input string, this is the common argument for them
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--debug", "-d", action="store_true", help="More verbose output")

    input_parser = argparse.ArgumentParser(add_help=False)
    input_parser.add_argument('input', nargs="?", default=None, help="the input file, value, or pipe")

    subparsers = parser.add_subparsers(dest="command", help="a sub command")
    subparsers.required = True # https://bugs.python.org/issue9253#msg186387

    # $ pout inject
    desc = "Inject pout into python builtins so it doesn't need to be imported"
    subparser = subparsers.add_parser(
        "inject",
        parents=[common_parser],
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
        parents=[common_parser, input_parser],
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
        parents=[common_parser, input_parser],
        help=desc,
        description=desc,
        #add_help=False
        conflict_handler="resolve",
    )
    subparser.set_defaults(func=main_json)

    # $ pout info
    desc = "Print pout and python information"
    subparser = subparsers.add_parser(
        "info",
        parents=[common_parser],
        help=desc,
        description=desc,
        #add_help=False
        conflict_handler="resolve",
    )
    subparser.add_argument(
        "--site-packages", "-s",
        dest="site_packages",
        action="store_true",
        help="just print the site-packages directory and nothing else",
    )
    subparser.set_defaults(func=main_info)

    args = parser.parse_args()

    # mess with logging
    global level
    if args.debug:
        level = logging.DEBUG
    logger.setLevel(level)

    code = args.func(args)
    sys.exit(code)


if __name__ == "__main__":
    main()

