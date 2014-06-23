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
    ppc, emap = model.load_case(filename, 0)
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
    'test_case_b.json',
    'test_case_b.xlsx',
])
def test_load_case(filename):
    filename = os.path.join(os.path.dirname(__file__), 'data', filename)
    ppc, emap = model.load_case(filename, 0)

    assert len(ppc) == 4
    assert ppc['baseMVA'] == 10
    assert np.all(ppc['bus'] == np.array([
        [0., 3., 0., 0., 0., 0., 1., 1., 0., 110. / sqrt_3, 1., 1.04, 0.96],
        [1., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [2., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [3., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
        [4., 1., 0., 0., 0., 0., 1., 1., 0.,  20. / sqrt_3, 1., 1.04, 0.96],
    ]))
    assert np.all(ppc['gen'] == np.array([
        [0., 0., 0., 999., -999., 1., 10., 1., 999., 0., 0., 0., 0., 0., 0.,
         0., 0., 0., 0., 0., 0.],
    ]))

    branchdata = np.array([
        [0., 1., 8.67768595e-05, 3.34710744e-03, 0.00000000e+00, 40.00, 40.00, 40.00, 1., 0., 1., -360, 360],  # NOQA
        [1., 2., 6.07500000e-02, 4.46250000e-02, 1.55194677e-02,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [1., 3., 3.64500000e-02, 2.67750000e-02, 9.31168063e-03,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [2., 4., 2.43000000e-02, 1.78500000e-02, 6.20778708e-03,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
        [3., 4., 3.64500000e-03, 2.67750000e-03, 9.31168063e-04,  7.24,  7.24,  7.24, 0., 0., 1., -360, 360],  # NOQA
    ])

    assert np.allclose(ppc['branch'], branchdata)

    # The old data format does not contain a value for P_loss
    if filename.endswith('test_case_b.old.json'):
        emap['0/Trafo1']['static']['P_loss'] = 160000
        emap['0/Trafo1']['static']['taps'] = {-4: 0.92, -3: 0.94, -2: 0.96,
                                              -1: 0.98, 0: 1.0, 1: 1.02,
                                              2: 1.04, 3: 1.06, 4: 1.08}

    assert emap == {
        '0/Grid': {'etype': 'RefBus', 'idx': 0, 'static': {'Vl': 110000}},
        '0/Bus0': {'etype': 'PQBus', 'idx': 1, 'static': {'Vl': 20000}},
        '0/Bus1': {'etype': 'PQBus', 'idx': 2, 'static': {'Vl': 20000}},
        '0/Bus2': {'etype': 'PQBus', 'idx': 3, 'static': {'Vl': 20000}},
        '0/Bus3': {'etype': 'PQBus', 'idx': 4, 'static': {'Vl': 20000}},
        '0/Trafo1': {'etype': 'Transformer', 'idx': 0, 'static': {
            'S_r': 40000000,
            'P_loss': 160000,
            'U_p': 110000,
            'U_s': 20000,
            'taps': {-4: 0.92, -3: 0.94, -2: 0.96, -1: 0.98, 0: 1.0, 1: 1.02,
                     2: 1.04, 3: 1.06, 4: 1.08},
            'tap_turn': 0,
            'online': True,
        }, 'related': ['0/Grid', '0/Bus0']},
        '0/B_0': {'etype': 'Branch', 'idx': 1, 'static': {
            'S_max': 7240000,
            'I_max': 362,
            'length': 5.0,
            'R_per_km': 0.162,
            'X_per_km': 0.119,
            'C_per_km': 0.000000247,
            'online': True,
        }, 'related': ['0/Bus0', '0/Bus1']},
        '0/B_1': {'etype': 'Branch', 'idx': 2, 'static': {
            'S_max': 7240000,
            'I_max': 362,
            'length': 3.0,
            'R_per_km': 0.162,
            'X_per_km': 0.119,
            'C_per_km': 0.000000247,
            'online': True,
        }, 'related': ['0/Bus0', '0/Bus2']},
        '0/B_2': {'etype': 'Branch', 'idx': 3, 'static': {
            'S_max': 7240000,
            'I_max': 362,
            'length': 2.0,
            'R_per_km': 0.162,
            'X_per_km': 0.119,
            'C_per_km': 0.000000247,
            'online': True,
        }, 'related': ['0/Bus1', '0/Bus3']},
        '0/B_3': {'etype': 'Branch', 'idx': 4, 'static': {
            'S_max': 7240000,
            'I_max': 362,
            'length': 0.3,
            'R_per_km': 0.162,
            'X_per_km': 0.119,
            'C_per_km': 0.000000247,
            'online': True,
        }, 'related': ['0/Bus2', '0/Bus3']},
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
        model.set_inputs(ppc, 'PQBus', i, data, {})
        assert ppc['bus'][i][idx_bus.PD] == data['P'] / 3000000
        assert ppc['bus'][i][idx_bus.QD] == data['Q'] / 3000000


def test_set_inputs_wrong_etype(ppc):
    pytest.raises(ValueError, model.set_inputs, ppc, 'foo', 0, None, None)


def test_perform_powerflow(ppc):
    inputs = [
        {'P':        0, 'Q':       0},  # grid
        {'P':  1760000, 'Q':  950000},  # bus_0
        {'P':   600000, 'Q':  200000},
        {'P': -1980000, 'Q': -280000},
        {'P':   850000, 'Q':  530000},
    ]
    for i, data in enumerate(inputs):
        model.set_inputs(ppc, 'PQBus', i, data, {})

    model.set_inputs(ppc, 'Transformer', 0, {'tap_turn': 0},
                     {'taps': {0: 1.0}})

    res = model.perform_powerflow(ppc)

    assert res['success'] == 1
    # Only check P, Q, Vm, Va - P and Q are 1/3 of the input values
    assert np.allclose(res['bus'][:,[2, 3, 7, 8]], np.array([
        [ 0.,          0.,         1.,          0.        ],  # NOQA
        [ 0.58666667,  0.31666667, 0.99994719, -0.00779594],  # NOQA
        [ 0.2,         0.06666667, 1.00002039, -0.01462836],  # NOQA
        [-0.66,       -0.09333333, 1.00066785,  0.01385849],  # NOQA
        [ 0.28333333,  0.17666667, 1.00046082,  0.00892602],  # NOQA
    ]))
    # Only check P and Q, both are 1/3 of the actual values
    assert np.allclose(res['gen'][:,[1, 2]], np.array([
        [0.4103084, 0.14716191],
    ]))
    assert np.allclose(res['branch'][:, -4:], np.array([
        [ 0.41030840,  0.14716191, -0.41030675, -0.14709831],  # NOQA
        [ 0.00154046, -0.09608627, -0.00153837, -0.05910184],  # NOQA
        [-0.17790038, -0.07348209,  0.17801840, -0.01960532],  # NOQA
        [-0.19846163, -0.00756482,  0.19855867, -0.05447164],  # NOQA
        [ 0.48198161,  0.11293865, -0.48189201, -0.12219503],  # NOQA
    ]))

    return res


def test_get_cache_entries(ppc_eidmap):
    ppc, emap = ppc_eidmap

    res = test_perform_powerflow(ppc)
    cache = model.get_cache_entries([res], emap)

    for eid, data in cache.items():
        for attr, val in data.items():
            data[attr] = round(val, 1)

    assert cache == {
        '0/Grid': {'P': 1230925.2, 'Q': 441485.7, 'Va': 0.0, 'Vm': 110000},
        '0/Bus0': {'P': 1760000.0, 'Q': 950000.0, 'Va': -0.0, 'Vm': 19998.9},
        '0/Bus1': {'P': 600000.0, 'Q': 200000.0, 'Va': -0.0, 'Vm': 20000.4},
        '0/Bus2': {'P': -1980000.0, 'Q': -280000.0, 'Va': 0.0, 'Vm': 20013.4},
        '0/Bus3': {'P': 850000.0, 'Q': 530000.0, 'Va': 0.0, 'Vm': 20009.2},
        '0/Trafo1': {'P_from': 1230925.2, 'P_to': -1230920.2, 'Q_from': 441485.7, 'Q_to': -441294.9},  # NOQA
        '0/B_0': {'I_real': -0.1, 'I_imag': -5.1, 'P_from': 4621.4, 'P_to': -4615.1, 'Q_from': -288258.8, 'Q_to': -177305.5},  # NOQA
        '0/B_1': {'I_real': 15.4, 'I_imag': -1.7, 'P_from': -533701.1, 'P_to': 534055.2, 'Q_from': -220446.3, 'Q_to': -58815.9},  # NOQA
        '0/B_2': {'I_real': 17.2, 'I_imag': -4.7, 'P_from': -595384.9, 'P_to': 595676.0, 'Q_from': -22694.5, 'Q_to': -163414.9},  # NOQA
        '0/B_3': {'I_real': 41.7, 'I_imag': 9.8, 'P_from': 1445944.8, 'P_to': -1445676.0, 'Q_from': 338815.9, 'Q_to': -366585.1},  # NOQA
    }
