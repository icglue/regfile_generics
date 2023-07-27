"""Regfile generics"""

from .regfile import Regfile, RegfileMemAccess, RegisterEntry
from .regfile_device import (
    RegfileDev,
    RegfileDevSimple,
    RegfileDevSimpleDebug,
    RegfileDevSubword,
    RegfileDevSubwordDebug,
    StringCmdRegfileDevSimple,
    StringCmdRegfileDevSubword,
)
