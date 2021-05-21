import pytest
import os.path
from math import isnan

from mosaik_pypower import mosaik


kV = 1000
MW = 1000 ** 2
pos_loads = -1  # Loads positive, see mosaik_pypower.mosaik.PyPower.__init__

grid_file = os.path.join(os.path.dirname(__file__), 'data', 'test_case_b.json')


def get_input_data(converge=True):
    if converge:
        P_Bus0 = 1.76
    else:
        P_Bus0 = 10000.
    input_data = {
        '0-Bus0': {'P': [P_Bus0], 'Q': [.95]},
        '0-Bus1': {'P': [.8, -.2], 'Q': [.2, 0]},
        '0-Bus2': {'P': [-1.98], 'Q': [-.28]},
        '0-Bus3': {'P': [.85], 'Q': [.53]},
    }

    # Correct input data by converting to MW and changing the sign:
    for d in input_data.values():
        for k, v in d.items():
            # Convert values to W and the list to a dict:
            d[k] = {i: x * MW for i, x in enumerate(v)}
            if k == 'P':
                d[k] = {key: val * pos_loads for key, val in d[k].items()}
                
    return input_data


def all_close(data, expected, ndigits=2):
    """Compare two nested dicts and check if their values rounded to *ndigits*
    after the decimal point are equal.

    """
    assert data.keys() == expected.keys()
    for eid, attrs in data.items():
        for attr, val in attrs.items():
            assert round(val, ndigits) == round(expected[eid][attr], ndigits)

    return True


# Case from https://bitbucket.org/ssc/cim2busbranch/src/tip/contrib/pp_test.py
#
#         Grid
#           +
# Transformer20kV(REF)
#           +              B_0
#          Bus0 ------------------- Bus1
#           |                        |
#           |B_1                     |B_2
#           |                        |
#           |              B_3       |
#          Bus2 ------------------- Bus3
#
def test_mosaik():
    """Test the API implementation without the network stack."""
    sim = mosaik.PyPower()
    meta = sim.init(0, 1., 60, pos_loads=(pos_loads > 0))
    assert list(sorted(meta['models'].keys())) == [
        'Branch', 'Grid', 'PQBus', 'RefBus', 'Transformer']

    entities = sim.create(1, 'Grid', grid_file)
    entities[0]['children'].sort(key=lambda e: e['eid'])
    assert entities == [{
        'eid': '0-grid', 'type': 'Grid', 'rel': [], 'children': [
            {'eid': '0-B_0', 'type': 'Branch', 'rel': ['0-Bus0', '0-Bus1']},
            {'eid': '0-B_1', 'type': 'Branch', 'rel': ['0-Bus0', '0-Bus2']},
            {'eid': '0-B_2', 'type': 'Branch', 'rel': ['0-Bus1', '0-Bus3']},
            {'eid': '0-B_3', 'type': 'Branch', 'rel': ['0-Bus2', '0-Bus3']},
            {'eid': '0-Bus0', 'type': 'PQBus', 'rel': []},
            {'eid': '0-Bus1', 'type': 'PQBus', 'rel': []},
            {'eid': '0-Bus2', 'type': 'PQBus', 'rel': []},
            {'eid': '0-Bus3', 'type': 'PQBus', 'rel': []},
            {'eid': '0-Grid', 'type': 'RefBus', 'rel': []},
            {'eid': '0-Trafo1', 'type': 'Transformer', 'rel': ['0-Grid',
                                                               '0-Bus0']},
        ],
    }]

    input_data = get_input_data()

    next_step = sim.step(0, input_data, 60)
    assert next_step == 60

    data = sim.get_data({
        '0-Grid': ['P', 'Q', 'Vl'],
        '0-Bus0': ['P', 'Q', 'Vm', 'Va'],
        '0-Bus1': ['P', 'Q', 'Vm', 'Va'],
        '0-Bus2': ['P', 'Q', 'Vm', 'Va'],
        '0-Bus3': ['P', 'Q', 'Vm', 'Va'],
    })
    assert all_close(data, {
        '0-Bus0': {
            'Vm': 19.999 * kV,
            'Va': -0.22,
            'P': 1.76 * MW * pos_loads,
            'Q': 0.95 * MW,
        },
        '0-Bus1': {
            'Vm': 20. * kV,
            'Va': -0.21,
            'P': .6 * MW * pos_loads,
            'Q': .2 * MW,
        },
        '0-Bus2': {
            'Vm': 20.013 * kV,
            'Va': -0.19,
            'P': -1.98 * MW * pos_loads,
            'Q': -0.28 * MW,
        },
        '0-Bus3': {
            'Vm': 20.009 * kV,
            'Va': -0.19,
            'P': .85 * MW * pos_loads,
            'Q': .53 * MW,
        },
        '0-Grid': {
            'P': 1.230925 * MW * pos_loads,
            'Q': 0.441486 * MW,
            'Vl': 110000,
        },
    }, ndigits=0)


def test_multiple_grids():
    sim = mosaik.PyPower()
    sim.init(0, 1., 60, pos_loads=(pos_loads > 0))

    entities_a = sim.create(2, 'Grid', grid_file)
    entities_b = sim.create(1, 'Grid', grid_file)

    assert len(entities_a) == 2
    assert len(entities_b) == 1
    assert entities_a[0]['eid'] == '0-grid'
    assert entities_a[1]['eid'] == '1-grid'
    assert entities_b[0]['eid'] == '2-grid'

    input_data = get_input_data()

    sim.step(0, input_data, 60)

    data = sim.get_data({
        '0-Grid': ['P', 'Q'],
        '0-Bus0': ['P', 'Q'],
        '1-Grid': ['P', 'Q'],
        '1-Bus0': ['P', 'Q'],
        '2-Grid': ['P', 'Q'],
        '2-Bus0': ['P', 'Q'],
    })
    assert all_close(data, {
        '0-Grid': {'Q': 441486,  'P': -1230925},
        '1-Grid': {'Q': -959406, 'P': -276},
        '2-Grid': {'Q': -959406, 'P': -276},
        '0-Bus0': {'Q': 950000, 'P': -1760000},
        '1-Bus0': {'Q': 0,      'P': 0},
        '2-Bus0': {'Q': 0,      'P': 0},
    }, ndigits=0)


@pytest.mark.parametrize(
    "converge_exception",
    [
     False,
     pytest.param(True, marks=pytest.mark.xfail(raises=RuntimeError)),
     ],
)
def test_converge_setting(converge_exception):
    simulator = mosaik.PyPower()
    meta = simulator.init(0, 1., 60, pos_loads=(pos_loads > 0),
                          converge_exception=converge_exception)
    entities = simulator.create(1, 'Grid', grid_file)
    
    input_data = get_input_data(converge=False)
    
    next_step = simulator.step(0, input_data, 60)
    
    data = simulator.get_data({
        '0-Grid': ['P'],
    })
    assert isnan(data['0-Grid']['P'])
