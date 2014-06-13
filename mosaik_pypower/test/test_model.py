import math
import os.path

from pypower import idx_bus
import numpy as np
import pytest

from mosaik_pypower import model


power_factor = 3
sqrt_3 = math.sqrt(3)


@pytest.fixture
def ppc_eidmap():
    filename = os.path.join(os.path.dirname(__file__), 'data',
                            'test_case_b.old.json')
    ppc, emap = model.load_case(filename)
    return ppc, emap


@pytest.fixture
def ppc(ppc_eidmap):
    return ppc_eidmap[0]


def test_uniqe_key_dict():
    ukd = model.UniqueKeyDict()
    ukd[1] = 'spam'
    ukd[2] = 'spam'
    try:
        ukd[1] = 'eggs'
        pytest.fail('Expected a ValueError.')
    except KeyError:
        pass


@pytest.mark.parametrize('filename', [
    'test_case_b.old.json',
])
def test_load_case(filename):
    filename = os.path.join(os.path.dirname(__file__), 'data', filename)
    ppc, emap = model.load_case(filename)

    assert len(ppc) == 4
    assert ppc['baseMVA'] == 1
    assert np.all(ppc['bus'] == np.array([
        [0., 3., 0., 0., 0., 0., 1., 1., 0., 110. / sqrt_3, 1., 1.04, 0.96],
        [1., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [2., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [3., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [4., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
    ]))
    assert np.all(ppc['gen'] == np.array([
        [0., 0., 0., 999., -999., 1., 1., 1., 999., 0., 0., 0., 0., 0., 0., 0.,
         0., 0., 0., 0., 0.],
    ]))

    branchdata = np.array([
        [0., 1., 8.57231405e-06, 3.17355372e-04, 0.00000000e+00, 40.00, 40.00, 40.00, 0., 0., 1., -360, 360],  # NOQA
        [1., 2., 6.07500000e-03, 4.46250000e-03, 1.55194677e-01,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [1., 3., 3.64500000e-03, 2.67750000e-03, 9.31168063e-02,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [2., 4., 2.43000000e-03, 1.78500000e-03, 6.20778708e-02,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [3., 4., 3.64500000e-04, 2.67750000e-04, 9.31168063e-03,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
    ])

    assert np.allclose(ppc['branch'], branchdata)

    assert emap == {
        'Grid': {'etype': 'RefBus', 'idx': 0, 'static': {'vl': 110.0}},
        'Bus0': {'etype': 'PQBus', 'idx': 1, 'static': {'vl': 20.0}},
        'Bus1': {'etype': 'PQBus', 'idx': 2, 'static': {'vl': 20.0}},
        'Bus2': {'etype': 'PQBus', 'idx': 3, 'static': {'vl': 20.0}},
        'Bus3': {'etype': 'PQBus', 'idx': 4, 'static': {'vl': 20.0}},
        'Trafo1': {'etype': 'Transformer', 'idx': 0, 'static': {
            'S_max': 40.0,
            'P_loss': 0,
            'U_p': 110,
            'U_s': 20,
        }, 'related': ['Grid', 'Bus0']},
        'B_0': {'etype': 'Branch', 'idx': 1, 'static': {
            's_max': 7.24,
            'i_max': 362,
            'length': 5.0,
            'r_per_km': 0.162,
            'x_per_km': 0.119,
            'c_per_km': 247,
        }, 'related': ['Bus0', 'Bus1']},
        'B_1': {'etype': 'Branch', 'idx': 2, 'static': {
            's_max': 7.24,
            'i_max': 362,
            'length': 3.0,
            'r_per_km': 0.162,
            'x_per_km': 0.119,
            'c_per_km': 247,
        }, 'related': ['Bus0', 'Bus2']},
        'B_2': {'etype': 'Branch', 'idx': 3, 'static': {
            's_max': 7.24,
            'i_max': 362,
            'length': 2.0,
            'r_per_km': 0.162,
            'x_per_km': 0.119,
            'c_per_km': 247,
        }, 'related': ['Bus1', 'Bus3']},
        'B_3': {'etype': 'Branch', 'idx': 4, 'static': {
            's_max': 7.24,
            'i_max': 362,
            'length': 0.3,
            'r_per_km': 0.162,
            'x_per_km': 0.119,
            'c_per_km': 247,
        }, 'related': ['Bus2', 'Bus3']},
    }


def test_reset_inputs(ppc):
    for bus in ppc['bus']:
        bus[idx_bus.PD] = 1
        bus[idx_bus.QD] = 2

    model.reset_inputs(ppc)

    for bus in ppc['bus']:
        assert bus[idx_bus.PD] == 0
        assert bus[idx_bus.QD] == 0


def test_set_inputs(ppc):
    inputs = [
        {'P': 1000000, 'Q': 2000000},
        {'P': 3000000, 'Q': 4000000},
        {'P': 5000000, 'Q': 6000000},
        {'P': 7000000, 'Q': 8000000},
    ]
    for i, data in enumerate(inputs):
        model.set_inputs(ppc, 'PQBus', i, data)
        assert ppc['bus'][i][idx_bus.PD] == data['P'] / 3000000
        assert ppc['bus'][i][idx_bus.QD] == data['Q'] / 3000000


def test_set_inputs_wrong_etype(ppc):
    pytest.raises(ValueError, model.set_inputs, ppc, 'foo', 0, None)


def test_perform_powerflow(ppc):
    inputs = [
        {'P':        0, 'Q':       0},  # grid
        {'P':  1760000, 'Q':  950000},  # bus_0
        {'P':   600000, 'Q':  200000},
        {'P': -1980000, 'Q': -280000},
        {'P':   850000, 'Q':  530000},
    ]
    for i, data in enumerate(inputs):
        model.set_inputs(ppc, 'PQBus', i, data)

    res = model.perform_powerflow(ppc)

    assert res['success'] == 1
    # Only check P, Q, Vm, Va - P and Q are 1/3 of the input values
    assert np.allclose(res['bus'][:,[2, 3, 7, 8]], np.array([
        [ 0.,          0.,         1.,          0.        ],  # NOQA
        [ 0.58666667,  0.31666667, 0.99994979, -0.00738878],  # NOQA
        [ 0.2,         0.06666667, 1.00002299, -0.01422131],  # NOQA
        [-0.66,       -0.09333333, 1.00067045,  0.01426541],  # NOQA
        [ 0.28333333,  0.17666667, 1.00046342,  0.00933296],  # NOQA
    ]))
    # Only check P and Q, both are 1/3 of the actual values
    assert np.allclose(res['gen'][:,[1, 2]], np.array([
        [0.41030838, 0.14715695],
    ]))
    assert np.allclose(res['branch'][:, -4:], np.array([
        [ 0.41030838,  0.14715695, -0.41030675, -0.14709665],  # NOQA
        [ 0.00154046, -0.09608710, -0.00153837, -0.05910182],  # NOQA
        [-0.17790038, -0.07348292,  0.17801840, -0.01960497],  # NOQA
        [-0.19846163, -0.00756485,  0.19855867, -0.05447194],  # NOQA
        [ 0.48198160,  0.11293830, -0.48189201, -0.12219473],  # NOQA
    ]))

    return res


def test_update_chache(ppc_eidmap):
    ppc, emap = ppc_eidmap

    res = test_perform_powerflow(ppc)
    cache = model.update_cache(res, emap)

    for eid, data in cache.items():
        for attr, val in data.items():
            data[attr] = round(val, 1)

    assert cache == {
        'Grid': {'P': 1230925.1000000001, 'Q': 441470.79999999999},
        'Bus0': {'P': 1760000.0, 'Vm': 19999.0, 'Q': 950000.0, 'Va': -0.0},
        'Bus1': {'P': 600000.0, 'Vm': 20000.5, 'Q': 200000.0, 'Va': -0.0},
        'Bus2': {'P': -1980000.0, 'Vm': 20013.4, 'Q': -280000.0, 'Va': 0.0},
        'Bus3': {'P': 850000.0, 'Vm': 20009.3, 'Q': 530000.0, 'Va': 0.0},
        'Trafo1': {'Q_from': 441470.79999999999, 'P_from': 1230925.1000000001, 'Q_to': -441289.90000000002, 'P_to': -1230920.2},
        'B_0': {'Q_from': -288261.29999999999, 'P_from': 4621.3999999999996, 'Q_to': -177305.5, 'P_to': -4615.1000000000004},
        'B_1': {'Q_from': -220448.79999999999, 'P_from': -533701.09999999998, 'Q_to': -58814.900000000001, 'P_to': 534055.19999999995},
        'B_2': {'Q_from': -22694.5, 'P_from': -595384.90000000002, 'Q_to': -163415.79999999999, 'P_to': 595676.0},
        'B_3': {'Q_from': 338814.90000000002, 'P_from': 1445944.8, 'Q_to': -366584.20000000001, 'P_to': -1445676.0},
    }
