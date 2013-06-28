import os.path

import numpy as np
import pytest

from mosaik_pypower import model


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
        [0., 0., 0., 999., -999., 1., 1., 1.,999., 0., 0., 0., 0., 0., 0., 0.,
         0., 0., 0., 0., 0.],
    ]))
    
    branchdata = np.array([
        [0., 1., 8.64375e-05, 3.2e-03, 0.00000000e+00, 40.  , 40.  , 40.,   1., 0., 1., -360, 360],
        [1., 2., 1.56250e-03, 1.4e-03, 1.88495559e+02, 19.98, 19.98, 19.98, 0., 0., 1., -360, 360],
        [1., 3., 9.37500e-04, 8.4e-04, 1.13097336e+02, 19.98, 19.98, 19.98, 0., 0., 1., -360, 360],
        [2., 4., 6.25000e-04, 5.6e-04, 7.53982237e+01, 19.98, 19.98, 19.98, 0., 0., 1., -360, 360],
        [3., 4., 9.37500e-05, 8.4e-05, 1.13097336e+01, 19.98, 19.98, 19.98, 0., 0., 1., -360, 360],
    ])
    
    assert np.allclose(ppc['branch'], branchdata, rtol=1e-05, atol=1e-08) 

    assert emap == {
        'Grid': {'etype': 'PQBus', 'idx': 0, 'static': {'vl': 110.0}},
        'Bus0': {'etype': 'PQBus', 'idx': 1, 'static': {'vl': 20.0}},
        'Bus1': {'etype': 'PQBus', 'idx': 2, 'static': {'vl': 20.0}},
        'Bus2': {'etype': 'PQBus', 'idx': 3, 'static': {'vl': 20.0}},
        'Bus3': {'etype': 'PQBus', 'idx': 4, 'static': {'vl': 20.0}},
        'Trafo1': {'etype': 'Transformer', 'idx': 0, 'static': {
            's_max': 40.0, 'prim_bus': 'Grid', 'sec_bus': 'Bus0'}},
        'B_0': {'etype': 'Branch', 'idx': 1, 'static': {
            's_max': 19.98, 'length': 5.0}},
        'B_1': {'etype': 'Branch', 'idx': 2, 'static': {
            's_max': 19.98, 'length': 3.0}},
        'B_2': {'etype': 'Branch', 'idx': 3, 'static': {
            's_max': 19.98, 'length': 2.0}},
        'B_3': {'etype': 'Branch', 'idx': 4, 'static': {
            's_max': 19.98, 'length': 0.3}},
    }



if __name__ == '__main__':
    test_uniqe_key_dict()
    test_load_case()

