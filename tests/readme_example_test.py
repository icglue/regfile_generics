from .fixtures import FixtureSimpleRegfile


def test_readme_example(sessionsimpleregfile: FixtureSimpleRegfile):
    regfile, rfdev = sessionsimpleregfile

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
        assert False  # pragma: nocover
