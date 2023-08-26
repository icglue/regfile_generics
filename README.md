# regfile\_generics

[![BSD License][bsdlicense-button]][bsdlicense]
[![PyPI][pypi-button]][pypi]
[![Build Status][build-button]][build]
[![Coverage Status][codecov-button]][codecov]
[![Code style: black][black-button]][black]

[bsdlicense-button]: https://img.shields.io/github/license/icglue/regfile_generics
[bsdlicense]: https://opensource.org/license/bsd-2-clause/
[pypi-button]: https://img.shields.io/pypi/v/regfile_generics
[pypi]: https://pypi.org/project/regfile-generics/
[build-button]: https://github.com/icglue/regfile_generics/workflows/CI/badge.svg?event=push
[build]: https://github.com/icglue/regfile_generics/actions?query=workflow%3ACI+event%3Apush
[codecov-button]: https://codecov.io/gh/icglue/regfile_generics/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/icglue/regfile_generics/tree/master
[black-button]: https://img.shields.io/badge/code%20style-black-000000.svg
[black]: https://github.com/psf/black

## Installation

### From PyPI

```bash
python3 -m pip install --upgrade regfile-generics
```

### From source

```bash
git clone https://github.com/icglue/regfile_generics
cd regfile_generics
python3 -m pip install .
```

## Usage

## Setup Regfile and Regfile Device for Access

See [tests/fixtures.py](https://github.com/icglue/regfile_generics/blob/master/tests/fixtures.py) how to create a regfile by deriving from the Regfile class.
Implement read/write functions and pass them (or overwrite while deriving) to an adequate [RegfileDevice](https://github.com/icglue/regfile_generics/blob/master/src/regfile_generics/regfile_device.py) class.

## Accessing Registers

```python
# dict like:
regfile["reg1_high"] = {"cfg": 0x0AA, "cfg_trigger": 0x0, "cfg_trigger_mode": 0x0}
# or single field (might issue read-modify-write)
regfile["reg1_high"]["cfg"] = 0xB

# uvm like (register have a _r suffix, field a _f suffix to avoid collisions):
regfile.reg1_high_r.cfg_f.set(2)
regfile.reg1_high_r.update()

# write_update
regfile["reg1_high"].write_update(cfg=0xA, cfg_trigger_mode=1)

# read (can be int or dict or string context)
print(regfile["reg1_high"])
assert (
    str(regfile["reg1_high"])
    == "Register reg1_high: {'cfg': 0xa, 'cfg_trigger': 0x0, 'cfg_trigger_mode': 0x1} = 0x1000a"
)
assert regfile["reg1_high"] == 0x1000A
assert dict(regfile["reg1_high"]) == {"cfg": 10, "cfg_trigger": 0, "cfg_trigger_mode": 1}

# read entire entry to a variable, so that no further read/write request will be issued
rh1 = regfile["reg1_high"].read_entry()
print(f"cfg: {rh1['cfg']}")
print(f"trigger: {rh1['cfg_trigger']}")
print(f"mode: {rh1['cfg_trigger_mode']}")

# bool access
regfile["reg1_high"] = 0
if regfile["reg1_high"]:
    assert False
```
