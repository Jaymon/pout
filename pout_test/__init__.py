# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import imp
import logging

from testdata import TestCase
import testdata

from pout.path import SitePackagesDir
from pout.compat import builtins
from pout import environ


s = SitePackagesDir()
#t = imp.find_module("pout", [s])
pout2 = imp.load_module("pout2", *imp.find_module("pout", [s]))
# for k in sys.modules.keys():
#     if "pout" in k:
#         print(k)

if hasattr(builtins, "pout"):
    del builtins.pout
builtins.pout2 = pout2


