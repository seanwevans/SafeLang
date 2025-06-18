import safelang.runtime as rt


def test_sat_add_normal():
    value, saturated = rt.sat_add(10, 20, 8, signed=True)
    assert value == 30
    assert not saturated


def test_sat_add_saturates_max():
    value, saturated = rt.sat_add(120, 20, 8, signed=True)
    assert value == 127
    assert saturated


def test_sat_sub_normal():
    value, saturated = rt.sat_sub(20, 10, 8, signed=True)
    assert value == 10
    assert not saturated


def test_sat_sub_saturates_min():
    value, saturated = rt.sat_sub(-120, 20, 8, signed=True)
    assert value == -128
    assert saturated


def test_sat_mul_normal():
    value, saturated = rt.sat_mul(5, 4, 8, signed=True)
    assert value == 20
    assert not saturated


def test_sat_mul_saturates_max():
    value, saturated = rt.sat_mul(20, 20, 8, signed=True)
    assert value == 127
    assert saturated


def test_sat_mul_saturates_min():
    value, saturated = rt.sat_mul(-20, 20, 8, signed=True)
    assert value == -128
    assert saturated


def test_sat_add_unsigned_normal():
    value, saturated = rt.sat_add(10, 20, 8, signed=False)
    assert value == 30
    assert not saturated


def test_sat_add_unsigned_saturates_max():
    value, saturated = rt.sat_add(250, 20, 8, signed=False)
    assert value == 255
    assert saturated


def test_sat_sub_unsigned_normal():
    value, saturated = rt.sat_sub(20, 10, 8, signed=False)
    assert value == 10
    assert not saturated


def test_sat_sub_unsigned_saturates_min():
    value, saturated = rt.sat_sub(10, 20, 8, signed=False)
    assert value == 0
    assert saturated


def test_sat_mul_unsigned_normal():
    value, saturated = rt.sat_mul(5, 4, 8, signed=False)
    assert value == 20
    assert not saturated


def test_sat_mul_unsigned_saturates_max():
    value, saturated = rt.sat_mul(20, 20, 8, signed=False)
    assert value == 255
    assert saturated


def test_sat_mul_unsigned_saturates_min():
    value, saturated = rt.sat_mul(-20, 20, 8, signed=False)
    assert value == 0
    assert saturated


def test_no_saturating_overflow_export():
    assert not hasattr(rt, "SaturatingOverflow")
