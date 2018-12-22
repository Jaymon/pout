# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import logging
import sys
import site
import inspect

from .compat import String


logger = logging.getLogger(__name__)


class Path(String):
    """Returns a path string relative to the current working directory (if applicable)"""
    def __new__(cls, path):
        cwd = os.getcwd()
        if path.startswith(cwd):
            path = path.replace(cwd, "", 1).lstrip(os.sep)
        return super(Path, cls).__new__(cls, path)


class SitePackagesDir(String):
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


class SiteCustomizeFile(String):
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
            filepath = ModuleFile("sitecustomize")

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


class ModuleFile(String):
    """Given a module name (eg, foo) find the source file that corresponds to the 
    module, will be an empty string if modname's filepath can't be found"""
    def __new__(cls, modname):
        if isinstance(modname, String):
            mod = sys.modules[modname]
        else:
            mod = modname
            modname = mod.__name__

        try:
            # http://stackoverflow.com/questions/6761337/inspect-getfile-vs-inspect-getsourcefile
            # first try and get the actual source file
            filepath = inspect.getsourcefile(mod)
            if not filepath:
                # get the raw file since val doesn't have a source file (could be a .pyc or .so file)
                filepath = inspect.getfile(mod)

            if filepath:
                path = os.path.realpath(filepath)

            # !!! I have doubts this if block is needed
            if filepath and not filepath.endswith(".py"):
                filepath = ""
                for path in sys.path:
                    p = os.path.join(path, "{}.py".format(modname))
                    if os.path.isfile(p):
                        filepath = p
                        break

        except TypeError as e:
            filepath = ""

        return super(ModuleFile, cls).__new__(cls, filepath)


