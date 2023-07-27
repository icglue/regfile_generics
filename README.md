# regfile\_generics

[![BSD License][bsdlicense-button]][bsdlicense]
[![Build Status][build-button]][build]
[![Coverage Status][codecov-button]][codecov]
[![Code style: black][black-button]][black]

[bsdlicense-button]: https://img.shields.io/github/license/icglue/regfile_generics
[bsdlicense]: https://opensource.org/license/bsd-2-clause/
[build-button]: https://github.com/icglue/regfile_generics/workflows/CI/badge.svg?event=push
[build]: https://github.com/icglue/regfile_generics/actions?query=workflow%3ACI+event%3Apush
[codecov-button]: https://codecov.io/gh/icglue/regfile_generics/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/icglue/regfile_generics/tree/master
[black-button]: https://img.shields.io/badge/code%20style-black-000000.svg
[black]: https://github.com/psf/black

## Installation

### From PyPI

```bash
python3 -m pip install --upgrade regfile_generics
```

### From source

```bash
git clone https://github.com/icglue/regfile_generics
cd regfile_generics
python3 -m pip install .
```

## Usage

## Setup Regfile and Regfile Device for Access

See [tests/fixtures.py](tests/fixtures.py) how to create a regfile by deriving from the Regfile class.
Implement read/write functions and pass them (or overwrite while deriving) to an adequate [RegfileDevice](src/regfile_generics/regfile_device.py) class.

## Accessing Registers

```python
    # dict like:
    regfile["reg1_high"] = {"cfg": 0x0AA, "cfg_trigger": 0x0, "cfg_trigger_mode": 0x0}
    # or single field (might issue read-modify-write)
    regfile["reg1_high"]["cfg"] = 0xB

    # uvm like:
    regfile.reg2_r.config_f.set(2)
    regfile.reg2_r.update()

    # write_update
    regfile["reg_addr40_r"].write_update(start=1, enable_feature0=0, enable_feature1=0)

    # read (can be int or dict or string context)
    assert entry["cfg"] == 0x22
    print(entry["cfg"])

    # read entire entry to an variable, so that no further read request will be issued
```
