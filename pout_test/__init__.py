# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys

from testdata import TestCase
import testdata


# remove any global pout (this is to overcome me putting pout in sites.py
# NOTE -- this has to go before any pout imports otherwise pout imports
# TODO -- this doesn't seem to work in the actual tests but does work in the
# pout module
if 'pout' in sys.modules:
    sys.modules['pout2'] = sys.modules['pout']
    sys.modules['pout2'].__name__ = "pout2"
    del sys.modules['pout']

    # allow the global pout to be used as pout2 without importing
    try:
        if sys.version_info[0] < 3:
            import __builtin__ as builtins
        else:
            import builtins

        if hasattr(builtins, "pout"):
            del builtins.pout
        builtins.pout2 = sys.modules['pout2']

    except ImportError as e:
        pass


from pout.compat import builtins

