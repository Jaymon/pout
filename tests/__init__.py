# -*- coding: utf-8 -*-
import sys
#import imp
import importlib
import logging

from testdata import TestCase, SkipTest
import testdata

from pout.path import SitePackagesDir
from pout.compat import builtins
from pout import environ


try:
    # https://stackoverflow.com/a/50028745/5006
    pout2 = importlib.machinery.PathFinder().find_spec(
        "pout",
        [SitePackagesDir()]
    )

except ImportError:
    pout2 = None
# for k in sys.modules.keys():
#     if "pout" in k:
#         print(k)

if hasattr(builtins, "pout"):
    del builtins.pout

if pout2:
    builtins.pout2 = pout2


class TestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        environ.SHOW_COLOR = False

