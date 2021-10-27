# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
#import imp
import importlib
import logging

from testdata import TestCase
import testdata

from pout.path import SitePackagesDir
from pout.compat import builtins
from pout import environ


try:
    # https://stackoverflow.com/a/50028745/5006
    pout2 = importlib.machinery.PathFinder().find_spec("pout", [SitePackagesDir()])
    #pout2 = imp.load_module("pout2", *imp.find_module("pout", [SitePackagesDir()]))
except ImportError:
    pout2 = None
# for k in sys.modules.keys():
#     if "pout" in k:
#         print(k)

if hasattr(builtins, "pout"):
    del builtins.pout

if pout2:
    builtins.pout2 = pout2


