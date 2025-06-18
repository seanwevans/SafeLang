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
