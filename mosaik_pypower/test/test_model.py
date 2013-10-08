import os.path

from pypower import idx_bus
import numpy as np
import pytest

from mosaik_pypower import model


@pytest.fixture
def ppc_eidmap():
    filename = os.path.join(os.path.dirname(__file__), 'data',
                            'test_case_b.json')
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


def test_load_case():
    filename = os.path.join(os.path.dirname(__file__), 'data',
                            'test_case_b.json')
    ppc, emap = model.load_case(filename)

    assert len(ppc) == 4
    assert ppc['baseMVA'] == 1
    assert np.all(ppc['bus'] == np.array([
        [0., 3., 0., 0., 0., 0., 1., 1., 0., 110., 1., 1.1, 0.9],
        [1., 1., 0., 0., 0., 0., 1., 1., 0.,  20., 1., 1.1, 0.9],
        [2., 1., 0., 0., 0., 0., 1., 1., 0.,  20., 1., 1.1, 0.9],
        [3., 1., 0., 0., 0., 0., 1., 1., 0.,  20., 1., 1.1, 0.9],
        [4., 1., 0., 0., 0., 0., 1., 1., 0.,  20., 1., 1.1, 0.9],
    ]))
    assert np.all(ppc['gen'] == np.array([
        [0., 0., 0., 999., -999., 1., 1., 1., 999., 0., 0., 0., 0., 0., 0., 0.,
         0., 0., 0., 0., 0.],
    ]))

    branchdata = np.array([
        [0., 1., 8.64375e-05, 3.2e-03, 0.00000000e+00, 40.000, 40.000, 40.000, 1., 0., 1., -360, 360],  # NOQA
        [1., 2., 1.56250e-03, 1.4e-03, 1.88495559e-01, 199.98, 199.98, 199.98, 0., 0., 1., -360, 360],  # NOQA
        [1., 3., 9.37500e-04, 8.4e-04, 1.13097336e-01, 199.98, 199.98, 199.98, 0., 0., 1., -360, 360],  # NOQA
        [2., 4., 6.25000e-04, 5.6e-04, 7.53982237e-02, 199.98, 199.98, 199.98, 0., 0., 1., -360, 360],  # NOQA
        [3., 4., 9.37500e-05, 8.4e-05, 1.13097336e-02, 199.98, 199.98, 199.98, 0., 0., 1., -360, 360],  # NOQA
    ])

    assert np.allclose(ppc['branch'], branchdata)

    assert emap == {
        'Grid': {'etype': 'Grid', 'idx': 0, 'static': {'vl': 110.0}},
        'Bus0': {'etype': 'PQBus', 'idx': 1, 'static': {'vl': 20.0}},
        'Bus1': {'etype': 'PQBus', 'idx': 2, 'static': {'vl': 20.0}},
        'Bus2': {'etype': 'PQBus', 'idx': 3, 'static': {'vl': 20.0}},
        'Bus3': {'etype': 'PQBus', 'idx': 4, 'static': {'vl': 20.0}},
        'Trafo1': {'etype': 'Transformer', 'idx': 0, 'static': {
            #'s_max': 40.0, 'prim_bus': 'Grid', 'sec_bus': 'Bus0'}},
            's_max': 40.0}, 'related': ['Grid', 'Bus0']},
        'B_0': {'etype': 'Branch', 'idx': 1, 'static': {
            's_max': 199.98, 'length': 5.0}, 'related': ['Bus0', 'Bus1']},
        'B_1': {'etype': 'Branch', 'idx': 2, 'static': {
            's_max': 199.98, 'length': 3.0}, 'related': ['Bus0', 'Bus2']},
        'B_2': {'etype': 'Branch', 'idx': 3, 'static': {
            's_max': 199.98, 'length': 2.0}, 'related': ['Bus1', 'Bus3']},
        'B_3': {'etype': 'Branch', 'idx': 4, 'static': {
            's_max': 199.98, 'length': 0.3}, 'related': ['Bus2', 'Bus3']},
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
        {'p': 1000000, 'q': 2000000},
        {'p': 3000000, 'q': 4000000},
        {'p': 5000000, 'q': 6000000},
        {'p': 7000000, 'q': 8000000},
    ]
    for i, data in enumerate(inputs):
        model.set_inputs(ppc, 'PQBus', i, data)
        assert ppc['bus'][i][idx_bus.PD] == data['p'] / 1000000
        assert ppc['bus'][i][idx_bus.QD] == data['q'] / 1000000


def test_set_inputs_wrong_etype(ppc):
    pytest.raises(ValueError, model.set_inputs, ppc, 'foo', 0, None)


def test_perform_powerflow(ppc):
    inputs = [
        {'p':        0, 'q':       0},  # grid
        {'p':  1760000, 'q':  950000},  # bus_0
        {'p':   600000, 'q':  200000},
        {'p': -1980000, 'q': -280000},
        {'p':   850000, 'q':  530000},
    ]
    for i, data in enumerate(inputs):
        model.set_inputs(ppc, 'PQBus', i, data)

    res = model.perform_powerflow(ppc)

    assert res['success'] == 1
    assert np.allclose(res['bus'], np.array([
        [0., 3.,  0.00,  0.00, 0., 0., 1., 1.,         0.,         110., 1., 1.1, 0.9],  # NOQA
        [1., 1.,  1.76,  0.95, 0., 0., 1., 0.99662699, -0.22137215, 20., 1., 1.1, 0.9],  # NOQA
        [2., 1.,  0.60,  0.20, 0., 0., 1., 0.99649041, -0.21344243, 20., 1., 1.1, 0.9],  # NOQA
        [3., 1., -1.98, -0.28, 0., 0., 1., 0.99702599, -0.18888503, 20., 1., 1.1, 0.9],  # NOQA
        [4., 1.,  0.85,  0.53, 0., 0., 1., 0.99685093, -0.19337765, 20., 1., 1.1, 0.9],  # NOQA
    ]))
    assert np.allclose(res['gen'], np.array([
        [0., 1.23095899, 1.02314077, 999., -999., 1., 1., 1., 999., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.],  # NOQA
    ]))

    assert np.allclose(res['branch'][:, -4:], np.array([
        [ 1.23095899e+00,  1.02314077e+00, -1.23073753e+00, -1.01494213e+00],  # NOQA
        [ 4.60560298e-03, -1.51921572e-03, -4.59222777e-03, -1.85669252e-01],  # NOQA
        [-5.33868076e-01,  6.64613411e-02,  5.34151283e-01, -1.78588235e-01],  # NOQA
        [-5.95407772e-01, -1.43307479e-02,  5.95631241e-01, -6.03660347e-02],  # NOQA
        [ 1.44584872e+00,  4.58588235e-01, -1.44563124e+00, -4.69633965e-01],  # NOQA
    ]))

    return res


def test_update_chache(ppc_eidmap):
    ppc, emap = ppc_eidmap

    res = test_perform_powerflow(ppc)
    cache = model.update_cache(res, emap)

    for etype, entities in cache.items():
        for eid, data in entities.items():
            for attr, val in data.items():
                data[attr] = round(val, 1)

    print(cache)
    assert cache == {
        'Grid': {
            u'Grid': {'q': 1023140.8, 'p': 1230959.0},
        },
        'Transformer': {
            u'Trafo1': {'p_to': -1230737.5, 'p_from': 1230959.0, 'q_from': 1023140.8, 'q_to': -1014942.1},  # NOQA
        },
        'PQBus': {
            u'Bus2': {'vm': 19940.5, 'va': -0.2, 'p_out': -1980000.0, 'q_out': -280000.0},  # NOQA
            u'Bus3': {'vm': 19937.0, 'va': -0.2, 'p_out':   850000.0, 'q_out':  530000.0},  # NOQA
            u'Bus0': {'vm': 19932.5, 'va': -0.2, 'p_out':  1760000.0, 'q_out':  950000.0},  # NOQA
            u'Bus1': {'vm': 19929.8, 'va': -0.2, 'p_out':   600000.0, 'q_out':  200000.0},  # NOQA
        },
        'Branch': {
            u'B_0': {'p_to':    -4592.2, 'p_from':    4605.6, 'q_from':  -1519.2, 'q_to': -185669.3},  # NOQA
            u'B_1': {'p_to':   534151.3, 'p_from': -533868.1, 'q_from':  66461.3, 'q_to': -178588.2},  # NOQA
            u'B_2': {'p_to':   595631.2, 'p_from': -595407.8, 'q_from': -14330.7, 'q_to':  -60366.0},  # NOQA
            u'B_3': {'p_to': -1445631.2, 'p_from': 1445848.7, 'q_from': 458588.2, 'q_to': -469634.0},  # NOQA
        },
    }
