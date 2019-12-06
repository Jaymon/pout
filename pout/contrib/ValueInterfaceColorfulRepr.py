__all__ = ("ValueInterfaceColorfulRepr",)

from ..interface import ValueInterface
from ..value import Value, Inspect

from hashlib import md5
from struct import Struct
from RichConsole import RGBColor # https://gitlab.com/KOLANICH/RichConsole.py is needed

p = Struct("I")

hash = md5

def str2rgb(s, tweak=b""):
    d = hash(s.encode("utf-8"))
    d = hash(d.digest())
    d.update(tweak)
    rgb = d.digest()[:3]
    return RGBColor(None, *rgb)


my_value_specific = type(Value.default_value_specific)(Value.default_value_specific)


class ObjectValueColorfulRepr(my_value_specific["ObjectValue"]):
    tweak = b""
    def string_value(self):
        val = self.val
        vt = Inspect(val)
        cls = vt.cls
        if cls:
            src_file = self._get_src_file(cls, default="")
        else:
            src_file = ""
        full_name = self._get_name(val, src_file=src_file)
        color = str2rgb(full_name, self.tweak)
        bgColor = color.invert()
        bgColor.bg = True
        return str(bgColor(color(repr(val))))


my_value_specific["ObjectValue"] = ObjectValueColorfulRepr


class ValueInterfaceColorfulRepr(ValueInterface):
    class value_class(Value):
        default_value_specific = my_value_specific
