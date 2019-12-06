#!/usr/bin/env python3
from setuptools import setup, find_packages
import re
from pathlib import Path

thisDir = Path(__file__).parent.absolute()

def getVersion():
    return re.search(r"^__version__\s*=\s*[\'\"]([^\'\"]+)", (thisDir / "pout" / "__init__.py").read_text(encoding="utf-8"), flags=re.I | re.M).group(1)

if __name__ == "__main__":
    setup(version = getVersion())
