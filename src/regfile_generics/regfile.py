# Copyright (C) 2021-2023 Andreas Dixius, Felix Neumärker
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

"""
Generic Regfile file access through names / items operator of the regfile class
"""
from __future__ import annotations

import traceback
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import ItemsView, Iterator, KeysView, ValuesView
    from typing import Callable, Optional, Union

    from .regfile_device import RegfileDev


def _regfile_warn_user(msg: str) -> None:
    """Function wrapper for warnings"""
    fstacklevel = len(traceback.extract_stack()) + 1
    for stacktrace in traceback.extract_stack():
        if __file__ == stacktrace[0]:
            break
        fstacklevel -= 1

    warnings.warn(msg, UserWarning, stacklevel=fstacklevel)


class RegisterEntry:  # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """Decompose access of a register into fields.

    If ``kwargs`` are specified, they are passed to the :func:`represent` function."""

    def __init__(self, **kwargs):
        object.__setattr__(self, "_frozen", False)

        self.addr = 0
        self.write_mask = -1
        self._fields = {}
        self.regfile = None
        self.name = "UNNAMED"
        self._reset = 0
        self.mirrored_value = 0
        self.desired_value = 0
        self._writable_fieldnames = ()
        self._userattributes = ()
        if kwargs:
            self.represent(**kwargs)

    def represent(  # pylint: disable=too-many-arguments
        self,
        addr: Optional[int] = None,
        write_mask: Optional[int] = None,
        fields: Optional[dict[str, RegisterField]] = None,
        regfile: Optional[Regfile] = None,
        name: Optional[str] = None,
        reset: Optional[int] = None,
        mirrored_value: Optional[int] = None,
        **kwargs,
    ) -> RegisterEntry:
        """Used upon initialization."""

        self._frozen = False
        setattr(self, "_frozen", False)
        if addr is not None:
            self.addr = addr
        if write_mask is not None:
            self.write_mask = write_mask
        if fields is not None:
            self._fields = fields
        if regfile is not None:
            self.regfile = regfile
        if name is not None:
            self.name = name
        if reset is not None:
            self._reset = reset
        if mirrored_value is not None:
            self.mirrored_value = mirrored_value
            self.desired_value = mirrored_value

        self._userattributes = tuple(kwargs.keys())
        for attr, value in kwargs.items():
            setattr(self, attr, value)

        self._set_writeable_fieldnames()
        self._frozen = True
        return self

    def __getitem__(self, key: str) -> int:
        """Dict-like access tor read a value from a field of the register-entry

        :param key: Name of the register-field."""

        if key in self._fields:
            return self._fields[key].get_field(self._get_value())

        raise KeyError(f"Field {key} does not exist. Available fields: {list(self._fields.keys())}")

    def __setitem__(self, key: str, value: int) -> None:
        """Dict-like access to write a value to a field.

        :param key: name of the register field
        :param value: value to be written to the field"""

        if key not in self._fields:
            raise KeyError(f"Field {key} does not exist. Available fields: {list(self.get_field_names())}")

        field = self._fields[key]
        truncval = self._fit_fieldvalue_for_write(field, value)
        self._set_value(truncval << field.lsb, field.get_mask())

    def write_update(self, *args, **kwargs):
        """Update the register.

        This function takes a dict as argument containing key/value of the fields to be written
        or kwargs with fieldnames/values

        Example:

        .. code-block::

           submodregfile["reg0"].write_update(cfg=0b0_0100)
        """
        if args:
            if len(args) == 1 and isinstance(args[0], dict):
                for field_name, field_value in args[0].items():
                    self.field(field_name).set(field_value)
            else:
                raise ValueError("write_update just takes one dict as argument.")

        for field_name, field_value in kwargs.items():
            self.field(field_name).set(field_value)

        self.update()

    def get_reg(self, value: Optional[int] = None) -> RegisterEntry:
        """Return a new RegisterEntry (shallow copy).

        :param value: Value to be hold by the new RegisterEntry,
                      if value is not the value will be taken from the original instance
        """
        if value is None:
            value = self._get_value()

        return RegisterEntry(
            addr=self.addr,
            write_mask=self.write_mask,
            fields=self._fields,
            regfile=self.regfile,
            name=self.name,
            reset=self._reset,
            mirrored_value=value,
            **{attr: getattr(self, attr) for attr in self._userattributes},
        )

    def read_entry(self) -> RegisterEntry:
        """Reads the value and returns a new RegisterEntry (alias of :func:`get_reg()`)."""
        return self.get_reg()

    def get_dict(self, value: Optional[int] = None) -> dict[str, int]:
        """Get dictionary field view of the register.

        If value is not specified a read will be executed,
        otherwise the value is decomposed to the fields

        :param value: Integer value that should be decomposed"""
        if value is None:
            value = self._get_value()
        return {name: field.get_field(value) for name, field in self.items()}

    def get_name(self) -> str:
        """Get the name of the register, if set otherwise return UNNAMED"""
        return self.name

    def get_field_names(self) -> KeysView[str]:
        """Returns a copy of the field's dictionary's list of keys (fieldnames)."""
        return self._fields.keys()

    def get_writable_fieldnames(self) -> tuple[str]:
        """Return a copied list containing all writable fieldnames"""
        return self._writable_fieldnames

    def writable_field_items(self) -> Iterator[tuple[str, RegisterEntry]]:
        """Return a iterator over all writable_fields (tuple name, RegisterEntry)"""
        for name in self._writable_fieldnames:
            yield name, self._fields[name]

    def get_reset_values(self) -> dict[str, int]:
        """Get iterator object of the tuple (fieldname, resetvalue) for writable fields only."""
        return {name: self._fields[name].get_field(self._reset) for name in self._writable_fieldnames}

    def field(self, name: str) -> RegisterField:
        """Get the field by name and add callback for UVM-like set() method of fields"""
        field = self._fields[name]
        if not hasattr(field, "_has_setfunc"):

            def setfunc(value: int) -> None:
                self.desired_value &= ~field.get_mask()
                self.desired_value |= self._fit_fieldvalue_for_write(field, value) << field.lsb

            setattr(field, "set", setfunc)
            setattr(field, "_has_setfunc", True)

        return field

    def items(self) -> ItemsView[str, RegisterField]:
        """Providing all (fieldname, field) tuples for for self-inspection."""
        return self._fields.items()

    def __iter__(self) -> Iterator[tuple[str, int]]:
        """Iterator over the (name, int) mainly for dict() conversion."""
        value = self._get_value()
        for key, field in self._fields.items():
            yield key, field.get_field(value)

    def __setattr__(self, name, value):
        """Enforce that no new attributes are set when the instance is frozen."""
        if self._frozen and name not in self.__dict__:
            raise AttributeError(f"Unable to allocate attribute {name} - Instance is frozen.")

        super().__setattr__(name, value)

    def __str__(self) -> str:
        """Read the register and format it decomposed as fields as well as integer value."""
        value = self._get_value()
        strfields = []
        for name, field in self.items():
            strfields.append(f"'{name}': 0x{field.get_field(value):x}")
        return f"Register {self.get_name()}: {{{', '.join(strfields)}}} = 0x{value:x}"

    def get_value(self, field_dict: Optional[dict] = None) -> int:
        """Return the integer view of the register.
        If field_dict is not specified a read will be executed,
        otherwise the dict is composed to get the integer value"""
        if field_dict is None:
            return self._get_value()

        if isinstance(field_dict, dict):
            value = 0
            for fieldname, fieldvalue in field_dict.items():
                field = self._fields[fieldname]
                value |= self._fit_fieldvalue(field, fieldvalue) << field.lsb
            return value
        raise TypeError(f"Unable to get_value for type {type(value)} -- {str(value)}.")

    def set_value(self, value: Union[int, dict, RegfileEntry], mask: Optional[int] = None) -> None:
        """Set the value of register. The value can be an integer a dict or
        a register object (e.g. obtained by :func:`get_reg()`).

        :param value: new value for the register
        :param mask: write mask for the register
        """
        if mask is None:
            mask = self.write_mask

        if isinstance(value, int):
            self._set_value(value, mask)
        elif isinstance(value, dict):
            writable_fieldnames = list(self.get_writable_fieldnames())
            write_value = 0
            for fieldname, fieldvalue in value.items():
                if fieldname in writable_fieldnames:
                    writable_fieldnames.remove(fieldname)
                    field = self._fields[fieldname]
                    write_value |= self._fit_fieldvalue_for_write(field, fieldvalue) << field.lsb
                elif fieldname not in self.get_field_names():
                    _regfile_warn_user(f"Ignoring non existent Field {fieldname} for write.")

            if writable_fieldnames:
                _regfile_warn_user(
                    f"Field(s) {', '.join(writable_fieldnames)} were not explicitly "
                    f"set during write of register {self.get_name()}!"
                )

            self._set_value(write_value, self.write_mask)
        elif isinstance(value, RegisterEntry):
            self._set_value(value.get_value(), self.write_mask)
        else:
            raise TypeError(f"Unable to assign type {type(value)} -- {str(value)}.")

    def __enter__(self) -> _RepresentDict:
        """The with statement allows to add fields to the register -

        with reg as add_fields_register:
            add_fields_register.represent(name="FIELDNAME", bits=(msb,lsb), reset=0x0, ...)
        """

        def add_field(key: str, **kwargs) -> None:
            bits = kwargs["bits"].split(":")
            msb = int(bits[0])
            lsb = int(bits[1]) if len(bits) == 2 else msb
            field = RegisterField(name=key, msb=msb, lsb=lsb, **kwargs)
            self._fields[key] = field
            if "reset" in kwargs:
                reset = int(kwargs["reset"], 0) << lsb

                truncreset = reset & field.get_mask()
                if truncreset != reset:
                    _regfile_warn_user(
                        f"{key}: reset value 0x{reset >> lsb:x} is truncated to 0x{truncreset >> lsb:x}."
                    )

                self._reset |= truncreset
                self.desired_value = self._reset
                self.mirrored_value = self._reset

        return _RepresentDict(add_field)

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Lock the register fields - sort-out the writable_fieldnames
        with the help of the write_mask"""
        # TODO: sanity check write mask
        self._set_writeable_fieldnames()

    def __getattr__(self, name: str):
        """Allow member access of fields - must have '_f' as suffix (<FIELDNAME>_f)."""
        if name[-2:] == "_f" and name[:-2] in self._fields:
            return self.field(name[:-2])

        raise AttributeError(
            f"Attribute {name} does not exist nor is a valid fieldname. "
            f"Available fields: {list(self._fields.keys())}"
        )

    def read(self) -> int:
        """UVM-like - Read the current value from this register."""
        return self.get_value()

    def get(self) -> int:
        """UVM-like - Return the desired value of the fields in the register."""
        return self.desired_value

    def get_mirrored_value(self) -> int:
        """UVM-like - Return the mirrored value of the fields in the register."""
        return self.mirrored_value

    def get_mirrored_dict(self) -> dict:
        """UVM-like - Variation of get_mirrored_value() return a dict instead of an int"""
        return self.get_dict(self.mirrored_value)

    def get_mirrored_reg(self) -> RegisterEntry:
        """UVM-like - Variation of get_mirrored_value() return a reg instead of an int"""
        return self.get_reg(self.mirrored_value)

    def set(self, value: int) -> None:
        """UVM-like - Set the desired value for this register."""
        self.desired_value = value

    def needs_update(self) -> bool:
        """UVM-like - Returns True if any of the fields need updating"""
        return self.desired_value != self.mirrored_value

    def update(self) -> None:
        """UVM-like - Updates the content of the register in the design
        to match the desired value."""
        self._set_value(self.desired_value, self.write_mask)

    def write(self, *args, **kwargs) -> None:
        """UVM-like - Write the specified value in this register."""
        if args and not kwargs:
            if len(args) == 1:
                self.set_value(args[0])
        elif not args and kwargs:
            self.set_value(kwargs)
        else:
            raise ValueError("write just takes one dict or kwargs as argument.")

    def reset(self) -> None:
        """UVM-like - Reset the desired/mirrored value for this register."""
        self.desired_value = self._reset
        self.mirrored_value = self._reset

    def get_reset(self) -> int:
        """UVM-like - Get the specified reset value for this register."""
        return self._reset

    def get_field_by_name(self, name: str) -> RegisterField:
        """UVM-like - Return the fields in this register."""
        return self.field(name)

    def get_offset(self):
        """UVM-like - Returns the offset of this register."""
        return self.addr

    def get_address(self):
        """UVM-like - Returns the base external physical address of this register"""
        return self.regfile.get_base_addr() + self.addr

    def __int__(self) -> int:
        """Integer conversion of register value"""
        return self.get_value()

    def __bool__(self) -> bool:
        """Boolean conversion of register value"""
        return bool(self.get_value())

    def __eq__(self, other):
        """Equal comparison with integer"""
        return int(self) == int(other)

    def __ne__(self, other):
        """Not equal comparison with integer"""
        return int(self) != int(other)

    def __lt__(self, other):
        """Less-than comparison with integer"""
        return int(self) < int(other)

    def __le__(self, other):
        """Less-than/equal comparison with integer"""
        return int(self) <= int(other)

    def __gt__(self, other):
        """Greater-than comparison with integer"""
        return int(self) > int(other)

    def __ge__(self, other):
        """Greater-than/equal comparison with integer"""
        return int(self) >= int(other)

    def _get_value(self) -> int:
        """Get value returns the mirrored value."""
        return self.mirrored_value

    def _set_value(self, value: int, mask: int) -> None:
        """Set value updates the desired and mirrored value"""
        self.desired_value = (self.desired_value & ~mask) | (value & mask)
        self.mirrored_value = self.desired_value

    def _fit_fieldvalue(self, field: RegisterField, value: int) -> int:
        """Truncate a value to fit into the field is necessary and raise a warning."""
        mask = field.get_mask()
        fieldmask = mask >> field.lsb
        truncval = value & fieldmask

        if value != truncval:
            _regfile_warn_user(f"{field.name}: value 0x{value:x} is truncated to 0x{truncval:x} (mask: 0x{fieldmask}).")
        return truncval

    def _fit_fieldvalue_for_write(self, field: RegisterField, value: int) -> int:
        """Additional to the truncation, check if field is writable."""
        mask = field.get_mask()
        if mask & self.write_mask != mask:
            _regfile_warn_user(
                f"Writing read-only field {field.name} (value: 0x{value:08x} -- "
                f"mask: 0x{mask:08x} write_mask: 0x{self.write_mask:08x})."
            )

        return self._fit_fieldvalue(field, value)

    def _set_writeable_fieldnames(self) -> None:
        """Tuple of object over all writable fieldnames"""
        self._writable_fieldnames = tuple(
            name for name, field in self._fields.items() if field.get_mask() & self.write_mask == field.get_mask()
        )

    def get_register_entry(self, value: int) -> RegisterEntry:  # pragma: nocover
        """.. deprecated:: 0.2.0

        Use :func:`get_reg` instead.

        :param value: Value to be hold by the new RegisterEntry"""
        warnings.warn(
            "Functions `get_register_entry()` is deprecated and will be removed in future versions.",
            UserWarning,
            stacklevel=2,
        )

        return self.get_reg(value)


class RegfileEntry(RegisterEntry):
    """RegfileEntry belonging to a :class:`.Regfile` which is callback on access"""

    def _get_value(self):
        value = self.regfile._read(self)  # pylint: disable=protected-access
        if self.needs_update():
            _regfile_warn_user(
                f"Register {self.get_name()}: Desired value 0x{self.desired_value:x} "
                f"has never been written via update() "
                f" --> mirrored value is 0x{self.mirrored_value:x}.\n"
                f"Reseting desired/mirrored value by readvalue 0x{value:x}"
            )

        self.desired_value = value
        self.mirrored_value = value
        return value

    def _set_value(self, value, mask):
        super()._set_value(value, mask)
        self.regfile._write(self, value, mask)  # pylint: disable=protected-access


class Regfile:
    """A Regfile handles multiple :class:`.RegfileEntry` items.

    It can be only be initialized by using context managers (with-statement).
    if name is not given the default name will be the ``<CLASSNAME>@<BASEADDR>``.

    Example:

    .. code-block::

      class SubmodRegfile(Regfile):
          def __init__(self, rfdev, base_addr):
              super().__init__(rfdev, base_addr)

              with self as regfile:
                  with regfile["reg0"].represent(addr=0x0000, write_mask=0x0000001F) as reg:
                      reg["cfg"].represent(bits="4:0", access="RW", reset="0x0", desc="Configure component")
                      reg["status"].represent(bits="31:16", access="regfile", desc="Component status")
    """

    def __init__(self, rfdev, base_addr: int = 0x0, name: Optional[str] = None):
        object.__setattr__(self, "_frozen", False)
        self._dev = rfdev
        self.__value_mask = (1 << (8 * self._dev.n_word_bytes)) - 1
        self.__base_addr = base_addr
        self._entries: dict[str, RegfileEntry] = {}
        if name:
            self._name = name
        else:
            self._name = f"{type(self).__name__}@0x{base_addr:x}"
        self._frozen = True

    def get_base_addr(self) -> int:
        """Return the base address of the register file (provided upon instantiation)."""
        return self.__base_addr

    @property
    def name(self) -> str:
        """ "Return the name of the registerfile"""
        return self._name

    def __setitem__(self, key: str, value: Union[int, dict, RegisterEntry]) -> None:
        """Access a register entry of the Regfile.

        :param key: name of the register
        :param value: value to execute a register write access

        Example:

        .. code-block::

          submodregfile['reg0'] = {'cfg': 0b1_1011}
        """

        if key not in self._entries:
            raise KeyError(f"Regfile has no entry named '{key}'.")

        self._entries[key].write(value)

    def __getitem__(self, key: str) -> RegisterEntry:
        """Access a register entry of register.

        :param key: name of the register"""

        if key not in self._entries:
            if not self._frozen:
                self._entries[key] = RegfileEntry(regfile=self, name=key)
            else:
                raise KeyError(f"Regfile has no entry named '{key}'.")
        return self._entries[key]

    def keys(self) -> KeysView[str]:
        """Get all register names of the Regfile."""
        return self._entries.keys()

    def values(self) -> ValuesView[RegfileEntry]:
        """Get all registers of the Regfile."""
        return self._entries.values()

    def items(self) -> ItemsView[str, RegisterEntry]:
        """Get all names plus the corresponding registers of the Regfile."""
        return self._entries.items()

    def __iter__(self) -> Iterator[RegfileEntry]:
        return iter(self._entries.values())

    def reset_all(self) -> None:
        """Apply initial reset value to mirrored value of all registers."""
        for regs in self._entries.values():
            regs.reset()

    def get_rfdev(self) -> RegfileDev:
        """Get the regfile device with is used upon access."""
        return self._dev

    def set_rfdev(self, dev: RegfileDev) -> None:
        """Set the regfile device with is used upon access.

        :param dev: regfile device
        """
        self._dev = dev

    def __setattr__(self, name, value):
        """Enforce that no new attributes are set when the instance is frozen."""
        if self._frozen and name not in self.__dict__:
            raise AttributeError(f"Unable to allocate attribute {name} - Instance is frozen.")
        super().__setattr__(name, value)

    def __getattr__(self, name):
        """Providing additional attribute-like access of a register.
        To avoid collisions the name has a ``_r`` suffix.

        Example:

        .. code-block::

            assert submodregfile[\"config\"] == submodregfile.config_r
        """
        if name[-2:] == "_r" and name[:-2] in self._entries:
            return self._entries[name[:-2]]
        raise AttributeError(f"Attribute {name} does not exist")

    def __enter__(self):
        """Context manager of with statement - After __enter__ adding of new entries is allowed."""
        self._frozen = False
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        """Context manager of with statement - Locks the instances again."""
        self._frozen = True

    def _read(self, entry):
        """Mainly used by register entry to obtain the value from the registerfile device."""
        return self._dev.read(self.get_base_addr(), entry)

    def _write(self, entry, value, mask):
        """Mainly used by register entry to write the value to registerfile device."""
        regvalue = value & self.__value_mask
        if value != regvalue:
            _regfile_warn_user(
                f"Value 0x{value:x} is too large to fit into "
                f"the specified word size ({self._dev.n_word_bytes}), "
                f"truncated to 0x{regvalue:x} / 0x{self.__value_mask:x}."
            )
        self._dev.write(self.get_base_addr(), entry, value, mask)


class RegfileMemAccess:
    """Handling Memory through a regfile device.

    Note that indexing is word wise, depending on :attr:`.regfile_device.RegfileDev.n_word_bytes`.

    :param rfdev: regfile device
    :param base_addr: base address of the memory

    Optional kwargs:
    :key size: the size of the memory to check of index errors
    """

    def __init__(self, rfdev: RegfileDev, base_addr: int, **kwargs):
        self._dev = rfdev
        self.__base_addr = base_addr
        self.__do_check_idx = False
        if kwargs["size"]:
            self.index_range = kwargs["size"] // self._dev.n_word_bytes
            self.__do_check_idx = True

    def __check_idx(self, index: int):
        """Check in the accessed element is within the allocated range."""
        if self.__do_check_idx:
            if index >= self.index_range:
                raise IndexError(f"Index {index} is out of bounds.")

    def __getitem__(self, index: int) -> int:
        """Read a memory element via index (word addressing)

        :param index: word address to be read"""

        self.__check_idx(index)
        return self._dev.rfdev_read(self.__base_addr + self._dev.n_word_bytes * index)

    def __setitem__(self, index: int, value: int):
        """Write a memory element via index (word addressing)

        :param index: word address to be read
        :value value: value to be written to the memory"""

        self.__check_idx(index)
        self._dev.rfdev_write(self.__base_addr + self._dev.n_word_bytes * index, value, -1, -1)

    def get_rfdev(self) -> RegfileDev:
        """Get the regfile device with is used upon access."""
        return self._dev

    def set_rfdev(self, dev) -> None:
        """Set the regfile device with is used upon access.

        :param dev: regfile device"""

        self._dev = dev

    def get_base_addr(self) -> int:
        """Return the base address of the register file (provided upon instantiation)."""
        return self.__base_addr

    def read_image(self, addr: int, size: int) -> list[int]:
        """Read Image starting on specified address.

        :param addr: start address
        :param size: size of image to be read from the memory

        :return: memory image as list"""

        from .regfile_device import RegfileDev  # pylint: disable=import-outside-toplevel

        if type(self._dev).readwrite_block is not RegfileDev.readwrite_block:  # pragma: nocover
            warnings.warn(
                f"Overriding function readwrite_block in {type(self._dev)} is deprecated"
                " and will not be support in future versions.",
                UserWarning,
            )
            image = size * [0]
            self._dev.readwrite_block(self.__base_addr + addr, image, False)
            return image

        return self._dev.blockread(self.__base_addr + addr, size)

    def write_image(self, addr: int, image: tuple[int, ...]) -> None:
        """Write Image starting on specified address.

        :param addr: start address
        :param image: image to be written to the memory"""
        # TODO: remove (deprecated)
        from .regfile_device import RegfileDev  # pylint: disable=import-outside-toplevel

        if type(self._dev).readwrite_block is not RegfileDev.readwrite_block:  # pragma: nocover
            warnings.warn(
                f"Overriding function readwrite_block in {type(self._dev)} is deprecated"
                " and will not be support in future versions.",
                UserWarning,
            )
            self._dev.readwrite_block(self.__base_addr + addr, image, True)
            return
        self._dev.blockwrite(self.__base_addr + addr, image)


class RegisterField:
    """Register Field data container

    This class justs holds name, msb, lsb and user defined informations as reset value or type.

    Mandatory kwargs:
      :key name: the name of the register field.
      :key msb: Bit position of the msb of the field within the register.
      :key lsb: Bit position of the lsb of the field within the register.

    Any information that should be store with the field such as the reset value, type, etc. is optional kwarg."""

    def __init__(self, **kwargs):
        self.name = kwargs.pop("name")
        self.msb = kwargs.pop("msb")
        self.lsb = kwargs.pop("lsb")

        for key, value in kwargs.items():
            self.__setattr__(key, value)

        self.__mask = (1 << (self.msb + 1)) - (1 << self.lsb)

    def get_field(self, value: int) -> int:
        """Get the value of the field from the register value

        :param value: Value of the register to extract the field value
        """
        return (value & self.__mask) >> self.lsb

    def get_mask(self) -> int:
        """Get the mask of the field"""
        return self.__mask

    def __str__(self) -> str:
        """Return the name of the field"""
        return f"{self.name}"

    def set(self, value: int) -> None:
        """UVM set function

        :param value: set desired value"""


class _RepresentDict:
    def __init__(self, represent_callback: Callable[..., None]):
        self._callback = represent_callback
        self._key = ""

    def __getitem__(self, key: str) -> _RepresentDict:
        """Dict-like access tor read a value from a field of the register-entry

        :param key: field name to be created
        """
        self._key = key
        return self

    def represent(self, **kwargs) -> None:
        """Represent function initiates the callback."""
        if self._key:
            self._callback(self._key, **kwargs)
        else:
            raise ValueError("No key has been accessed.")
