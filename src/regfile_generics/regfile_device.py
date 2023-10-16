# Copyright (C) 2020-2023 Andreas Dixius, Felix Neumärker
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""Generic Devices on which a regfile can operate."""

from __future__ import annotations

import logging
import os
import random
import struct
import sys
import traceback
import warnings
from typing import TYPE_CHECKING, Callable, cast

if TYPE_CHECKING:  # pragma: nocover
    from typing import Optional

    from .regfile import RegfileEntry


class RegfileDev:
    """Regfile Device class that handels the access of a Regfile

    :param callback: dict with rfdev_read/rfdev_write/blockread/blockwrite
                   pointing to a register read/write function
    :param bytes_per_word: bytes per word a single register access can handle (default 4)
    :param logger: logger instance
    :param prefix: prefix for (debug) logging with the logger instance

    .. deprecated:: 0.2.0

      :key blockread: reference to a blockread function, use callback dict instead
      :key blockwrite: reference to a blockwrite function, use callback dict instead"""

    def __init__(
        self,
        callback: Optional[dict[str, Callable]] = None,
        bytes_per_word: int = 4,
        logger: Optional[logging.Logger] = None,
        prefix: str = "",
        **kwargs,
    ):
        super().__init__()
        self._bytes_per_word = bytes_per_word
        self.logger = logger
        self._prefix = prefix
        self.callback = callback if callback else {}

        for blockop in ("blockread", "blockwrite"):
            if blockop in kwargs:  # pragma: nocover
                warnings.warn(
                    f"RegfileDev init - kwarg {blockop} has been deprecated use the callback dict instead.",
                    UserWarning,
                    stacklevel=2,
                )
                self.callback[blockop] = kwargs[blockop]

        if not isinstance(self.callback, dict):
            raise TypeError("Argument 'callback' has to dict with name, callback function.")

        if not set(self.callback) <= self._allowed_callbacks():
            raise AttributeError(f"Only {self._allowed_callbacks} are allowed as callback functions.")

        for func in self._allowed_callbacks() - set(self.callback):
            if not hasattr(self, func):
                raise TypeError(f"Function {func} has to be implemented or passed as callback function.")

    def _allowed_callbacks(self) -> set[str]:
        """Returns allowed keys to be passed as inside the callback argument while class initialization"""
        return {"rfdev_read", "rfdev_write"}

    @property
    def n_word_bytes(self) -> int:
        """Returs the number of bytes per word the device handles on one operation."""
        return self._bytes_per_word

    def blockread(self, start_addr: int, size: int) -> list[int]:
        """Initiate a blockread used for

        :param start_addr: start address of read data
        :param size: number of words to be read"""
        if "blockread" in self.callback:
            return self.callback["blockread"](start_addr, size)

        return [self.rfdev_read(start_addr + i * self.n_word_bytes) for i in range(size)]

    def blockwrite(self, start_addr: int, values: tuple[int, ...]) -> None:
        """Initiate a blockwrite used for memory access
        :param start_addr: start address of write data
        :param value: word list to be written"""

        if "blockwrite" in self.callback:
            self.callback["blockwrite"](start_addr, values)
            return

        mask = (1 << (8 * self.n_word_bytes)) - 1
        write_mask = mask
        for i, value in enumerate(values):
            self.rfdev_write(start_addr + i * self.n_word_bytes, value, mask, write_mask)

    def rfdev_read(self, addr: int) -> int:
        """Read method calling `rfdev_read` of callback dict passed upon init
        - could be overridden, when deriving a new RegfileDev"""
        value = self.callback["rfdev_read"](addr)
        if self.logger:
            self.logger.debug(
                "RegfileDevice: Read address 0x%x -- value: 0x%x",
                addr,
                value,
            )
        return value

    def read(self, baseaddr: int, entry: RegfileEntry) -> int:
        """Read a register entry relative to a base address

        :param baseaddr: Base address of the Register File
        :param entry: A register entry
        """
        value = self.rfdev_read(baseaddr + entry.addr)
        if self.logger and self.logger.isEnabledFor(logging.INFO):
            self.logger.info(
                "%sReading %s: %s",
                self._prefix,
                entry.regfile.name,
                entry.get_reg(value),
            )
        return value

    def rfdev_write(self, addr: int, value: int, mask: int, write_mask: int) -> None:
        """Read method could be overridden when deriving a new RegfileDev
        default implementation is to call the function passed while initialization,
        through the value of the "rfdev_write"-key of the callback dictionary.

        :param addr: Absolute Address to be accessed for write
        :param value: Value to be written
        :param mask: Mask for the write operation to the register
        :param write_mask: Mask of writeable bits inside the register
          (e.g. to determine if read-modify-write is necessary)
        """

        if self.logger:
            self.logger.debug(
                "RegfileDevice: Read address 0x%x -- value: 0x%x (mask: 0x%x, write_mask: 0x%x)",
                addr,
                value,
                mask,
                write_mask,
            )
        self.callback["rfdev_write"](addr, value, mask, write_mask)

    def write(self, baseaddr: int, entry: RegfileEntry, value: int, mask: int) -> None:
        """Read a register entry relative to a base address

        :param baseaddr: Base address of the Register File
        :param entry: A register entry
        :param value: register value
        :param mask:  mask for the operation
        """
        addr = baseaddr + entry.addr

        if self.logger and self.logger.isEnabledFor(logging.INFO):
            update_fields = [
                f"'{name}': 0x{field.get_field(value):x}" for name, field in entry.items() if field.get_mask() & mask
            ]
            self.logger.info(
                "%sWriting %s: Register %s = 0x%x & 0x%x --> {%s}",
                self._prefix,
                entry.regfile.name,
                entry.name,
                value,
                mask,
                ", ".join(update_fields),
            )
        self.rfdev_write(addr, value, mask, entry.write_mask)

    def readwrite_block(self, start_addr, values, write):  # pragma: nocover
        """.. deprecated:: 0.2.0

        Use :func:`blockread` or :func:`blockwrite` instead."""

        warnings.warn(
            "Function `readwrite_block()` is deprecated and will be removed in future versions.",
            UserWarning,
            stacklevel=2,
        )
        if not write:
            read_value = self.blockread(start_addr, len(values))
            for i in range(len(values)):  # pylint: disable=consider-using-enumerate
                # Modifications are be done by reference
                values[i] = read_value[i]
        else:
            self.blockwrite(start_addr, values)


class RegfileDevSimple(RegfileDev):
    """RegfileDev that operates on words only (implements read-modify-write if necessary)

    Derived from :class:`.RegfileDev`

    Allowed callback entries:

        :key rfdev_read: read function (signature :func:`.RegfileDev.rfdev_read`)
        :key rfdev_write_simple: write function which has the same signature like :func:`rfdev_write_simple`
    """

    def _allowed_callbacks(self) -> set[str]:
        return {"rfdev_read", "rfdev_write_simple"}

    def rfdev_write_simple(self, addr: int, value: int) -> None:
        """Simple write operation - calls back `rfdev_write_simple` if passed to constructor.

        :param addr: absolute address for write operation
        :param value: value to write
        """

        if self.logger:
            self.logger.debug(
                "RegfileDevice: Read address 0x%x -- value: 0x%x",
                addr,
                value,
            )
        self.callback["rfdev_write_simple"](addr, value)

    def rfdev_write(self, addr: int, value: int, mask: int, write_mask: int) -> None:
        """:class:`.RegfileDev` rfdev_write implementations
        - executes the read-modify-write if necessary

        :param addr: absolute Address to be accessed for write
        :param value: value to be written
        :param mask: mask for the write operation to the register
        :param write_mask: mask of writeable bits inside the register"""

        keep_mask = ~mask & write_mask

        if keep_mask == 0:
            self.rfdev_write_simple(addr, value)
        else:
            # read, modify, write
            rmw_value = self.rfdev_read(addr)

            rmw_value &= ~mask
            rmw_value |= value & mask

            self.rfdev_write_simple(addr, rmw_value)


def regfile_dev_debug_getbits(interactive: bool, default_value: int, promptprefix: str) -> int:
    """Function to get bits for RegfileDebug* classes"""
    value = default_value
    if not interactive:
        print(f"{promptprefix} value: 0x{default_value:x}")
    else:  # pragma: nocover
        lasttrace: Optional[traceback.FrameSummary] = None
        regfile_generics_package_path = os.path.dirname(__file__)

        for stacktrace in traceback.extract_stack():
            if stacktrace[0].startswith(regfile_generics_package_path):
                if lasttrace is not None:
                    print(f"{lasttrace[0]}:{lasttrace[1]}: {lasttrace[3]}", file=sys.stderr)
                break
            lasttrace = stacktrace

        while True:
            if input_value := input(f"{promptprefix} value (0x{default_value:x}): "):
                try:
                    value = int(input_value, 0)
                    break
                except ValueError:
                    print(f"Invalid value {value}.")

    return value


class RegfileDevSimpleDebug(RegfileDevSimple):
    """Debug implementation of :class:`.RegfileDevSimple`

    :param interactive: if set to ``True`` the regfile device will request a user input upon read.
    """

    def __init__(self, interactive: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.mem: dict[int, int] = {}
        self.write_count = 0
        self.read_count = 0
        self.__interactive = interactive

    def rfdev_read(self, addr: int) -> int:
        """Debug read function interactive if necessary

        :param: addr address
        """

        value = regfile_dev_debug_getbits(
            self.__interactive,
            self.getvalue(addr),
            f"{self._prefix}REGFILE-READING from addr 0x{addr:x}",
        )
        self.mem[addr] = value

        self.read_count += 1

        if self.logger:
            self.logger.debug(
                "RegfileDevice: Read address 0x%x -- value: 0x%x",
                addr,
                value,
            )
        return value

    def rfdev_write_simple(self, addr: int, value: int) -> None:
        """Debug write function to `mem` attribute.

        :param addr: absolute address for write operation
        :param value: value to write
        """
        print(f"{self._prefix}REGFILE-WRITING to addr 0x{addr:x} value 0x{value:x}")
        self.mem[addr] = value
        self.write_count += 1

    def getvalue(self, addr: int) -> int:
        """Get value out of the memory, randomize if necessary.

        :param addr: address to be read"""
        if addr not in self.mem:
            value = random.getrandbits(8 * self.n_word_bytes)
            if self.logger:
                self.logger.info("Generating random regfile value 0x%x", value)
            return value

        return self.mem[addr]


class RegfileDevSubword(RegfileDev):
    """RegfileDev that operates on word sizes (implements read-modify-write if this)

    Derived from :class:`.RegfileDev`

    Allowed callback entries:

        :key rfdev_read: read function (signature :func:`.RegfileDev.rfdev_read`)
        :key rfdev_write_simple: write function which has the same signature like :func:`rfdev_write_simple`
    """

    def rfdev_write(self, addr: int, value: int, mask: int, write_mask: int) -> None:
        # register bits that must not be changed
        keep_mask = ~mask & write_mask

        # initial subword mask: full word size - all bits to 1
        subword_mask = (1 << (8 * self.n_word_bytes)) - 1

        # go from full word to shorter subwords (e.g. 32, 16, 8 bits --> 4, 2, 1 bytes)
        n_subword_bytes = self.n_word_bytes
        while n_subword_bytes:
            # iterate subwords of current size (e.g. 32bits: 0; 16bits: 0, 1; 8bits: 0, 1, 2, 3)
            for i in range(self.n_word_bytes // n_subword_bytes):
                # shift wordmask to current position
                i_word_mask = subword_mask << (i * n_subword_bytes * 8)

                # no keep bit would be overwritten? && all write bits are covered?
                if ((keep_mask & i_word_mask) == 0) and ((mask & (~i_word_mask)) == 0):
                    subword_offset = i * n_subword_bytes

                    # call virtual method
                    if self.logger:
                        self.logger.debug(
                            "RegfileDevice: Subwrite address 0x%x -- {value: 0x%x, n_subword_bytes: 0x%x}",
                            addr + subword_offset,
                            value,
                            n_subword_bytes,
                        )
                    self.rfdev_write_subword(addr + subword_offset, value, n_subword_bytes)
                    # we are done here ...
                    return

            # reduce subword bytes - next half
            n_subword_bytes //= 2
            # reduce subword mask - throw away the other half
            subword_mask >>= n_subword_bytes * 8

        # no success?  - full read-modify-write
        rmw_value = self.rfdev_read(addr)

        rmw_value &= ~mask
        rmw_value |= value & mask

        # call virtual method
        self.rfdev_write_subword(addr, rmw_value, self.n_word_bytes)

    def _allowed_callbacks(self) -> set[str]:
        return {"rfdev_read", "rfdev_write_subword"}

    def rfdev_write_subword(self, addr: int, value: int, size: int) -> None:
        """Word size write operation - calls back `rfdev_write_subword` if passed to constructor.

        :param addr: absolute address for write operation (lower address bit indicate word position)
        :param value: value to write
        :param size: number of bytes to write
        """
        self.callback["rfdev_write_subword"](addr, value, size)


class RegfileDevSubwordDebug(RegfileDevSubword):
    """Debug implementation of :class:`.RegfileDevSimple`

    :param interactive: if set to ``True`` the regfile device will request a user input upon read.
    """

    def __init__(self, interactive: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.__interactive = interactive
        self.mem: dict[int, int] = {}
        self.write_count = 0
        self.read_count = 0

    def getvalue(self, addr: int) -> int:
        """Return memory value

        :param addr: address were the data will be read
        """

        word = []
        for i in range(self.n_word_bytes):
            if (addr + i) not in self.mem:
                byte_value = random.getrandbits(8)
                print(f"Generating random regfile value {byte_value}.")
                self.mem[addr + i] = byte_value

            byte_value = self.mem[addr + i]
            word.append(byte_value)

        return int.from_bytes(struct.pack(f"{self.n_word_bytes}B", *word), "little")

    def rfdev_read(self, addr: int) -> int:
        """Debug read function interactive if necessary

        :param: addr address
        """

        value = self.getvalue(addr)

        value = regfile_dev_debug_getbits(
            self.__interactive,
            value,
            f"{self._prefix}REGFILE-READING from addr 0x{addr:x}",
        )
        for i in range(self.n_word_bytes):
            self.mem[addr + i] = (value >> (8 * i)) & 0xFF

        self.read_count += 1

        if self.logger:
            self.logger.debug(
                "RegfileDevice: Read address 0x%x -- value: 0x%x",
                addr,
                value,
            )
        return value

    def rfdev_write_subword(self, addr: int, value: int, size: int) -> None:
        print(f"{self._prefix}REGFILE-WRITING to addr 0x{addr:x} value 0x{value:x} size=0x{size:x}")

        byte_values = value.to_bytes(self.n_word_bytes, "little")
        for i in range(size):
            self.mem[addr + i] = byte_values[i + addr & 0b11]
        self.write_count += 1


class StringCmdRegfileDevSimple(RegfileDevSimple):
    """Forwards regfile operations to a function call with string command,
    to do the regfile operations.

     Read:
         r<NUMBITS> <address>
             e.g. r32 0x1C

     Write:
         w<NUMBITS> <address> <value>
             e.g. w32 0x80 0xF9852A
    """

    def __init__(self, execute: Optional[Callable[[str], Optional[str]]] = None, **kwargs):
        super().__init__(**kwargs)
        self.execute = execute

    def rfdev_read(self, addr: int) -> int:
        """Debug read function implementation translates to :func:`execute()`

        :param addr: absolute address for read operation"""

        return int(cast(Callable[[str], str], self.execute)(f"r{8*self.n_word_bytes} 0x{addr:x}"), 0)

    def rfdev_write_simple(self, addr: int, value: int):
        """Debug write function implementation translates to :func:`execute()`

        :param addr: absolute address for write operation
        :param value: value to write"""

        cast(Callable[[str], None], self.execute)(f"w{8*self.n_word_bytes} 0x{addr:x} 0x{value:x}")


class StringCmdRegfileDevSubword(RegfileDevSubword):
    """Forwards regfile operations to a function call with string command,
    to do the regfile operations.

     Read:
         r<NUMBITS> <address>
             e.g. r32 0x1C

     Write:
         w<NUMBITS> <address> <value> [bsel]
             e.g. w32 0x80 0xF9852A
                  w32 0x80 0xF9852A 0x1
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.execute = kwargs["execute"]

    def rfdev_read(self, addr: int) -> int:
        return int(self.execute(f"r{8*self.n_word_bytes} 0x{addr:x}"), 0)

    def rfdev_write_subword(self, addr: int, value: int, size: int) -> None:
        subword_addrbits = self.n_word_bytes.bit_length() - 1
        bsel = ((1 << size) - 1) << (addr & subword_addrbits)
        addr_aligned = addr & ~subword_addrbits

        self.execute(f"w{8*self.n_word_bytes} 0x{addr_aligned:x} 0x{value:x} 0x{bsel:x}")
