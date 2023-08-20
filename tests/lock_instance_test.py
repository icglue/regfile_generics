"""Regfile access tests"""

import pytest

from .fixtures import FixtureSubwordRegfile


def test_regfile_attribute_exception(sessionsubwordregfile: FixtureSubwordRegfile):
    regfile, rfdev = sessionsubwordregfile
    with pytest.raises(Exception):
        regfile.reg1_high_r = 0xDEAD


def test_regfile_entry_attribute_exception(sessionsubwordregfile: FixtureSubwordRegfile):
    regfile, rfdev = sessionsubwordregfile
    entry = regfile["reg1_high"].get_reg(0x1)
    with pytest.raises(Exception):
        entry.cfg_f = 0xDEAD
    with pytest.raises(Exception):
        regfile.reg1_high_r.cfg_f = 0xDEAD
