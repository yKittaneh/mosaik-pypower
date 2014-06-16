import os.path

from mosaik_pypower import mosaik


kV = 1000
MW = 1000 ** 2
mf = 1  # Magic factor, see mosaik_pypower.mosaik.PyPower.__init__
pos_loads = -1  # Loads positive, see mosaik_pypower.mosaik.PyPower.__init__


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
    sim._magic_factor = mf
    grid_file = os.path.join(os.path.dirname(__file__), 'data',
                             'test_case_b.old.json')
    meta = sim.init(0, 60, pos_loads=(pos_loads > 0))
    assert list(sorted(meta['models'].keys())) == [
        'Branch', 'Grid', 'PQBus', 'RefBus', 'Transformer']

    entities = sim.create(1, 'Grid', grid_file)
    entities[0]['children'].sort(key=lambda e: e['eid'])
    assert entities == [{
        'eid': 'grid_0', 'type': 'Grid', 'rel': [], 'children': [
            {'eid': 'B_0', 'type': 'Branch', 'rel': ['Bus0', 'Bus1']},
            {'eid': 'B_1', 'type': 'Branch', 'rel': ['Bus0', 'Bus2']},
            {'eid': 'B_2', 'type': 'Branch', 'rel': ['Bus1', 'Bus3']},
            {'eid': 'B_3', 'type': 'Branch', 'rel': ['Bus2', 'Bus3']},
            {'eid': 'Bus0', 'type': 'PQBus', 'rel': []},
            {'eid': 'Bus1', 'type': 'PQBus', 'rel': []},
            {'eid': 'Bus2', 'type': 'PQBus', 'rel': []},
            {'eid': 'Bus3', 'type': 'PQBus', 'rel': []},
            {'eid': 'Grid', 'type': 'RefBus', 'rel': []},
            {'eid': 'Trafo1', 'type': 'Transformer', 'rel': ['Grid', 'Bus0']},
        ],
    }]

    data = {
        'Bus0': {'P': [1.76], 'Q': [.95]},
        'Bus1': {'P': [.8, -.2], 'Q': [.2, 0]},
        'Bus2': {'P': [-1.98], 'Q': [-.28]},
        'Bus3': {'P': [.85], 'Q': [.53]},
    }
    # Correct input data by converting to MW, appling the magic factor and
    # changing the sign:
    for d in data.values():
        for k, v in d.items():
            d[k] = [x * MW * mf for x in v]
            if k == 'P':
                d[k] = [x * pos_loads for x in d[k]]

    next_step = sim.step(0, data)
    assert next_step == 60

    data = sim.get_data({
        'Grid': ['P', 'Q', 'Vl'],
        'Bus0': ['P', 'Q', 'Vm', 'Va'],
        'Bus1': ['P', 'Q', 'Vm', 'Va'],
        'Bus2': ['P', 'Q', 'Vm', 'Va'],
        'Bus3': ['P', 'Q', 'Vm', 'Va'],
    })
    assert all_close(data, {
        'Bus0': {
            'Vm': 19.999 * kV,
            'Va': -0.22,
            'P': 1.76 * MW * pos_loads,
            'Q': 0.95 * MW,
        },
        'Bus1': {
            'Vm': 20. * kV,
            'Va': -0.21,
            'P': .6 * MW * pos_loads,
            'Q': .2 * MW,
        },
        'Bus2': {
            'Vm': 20.013 * kV,
            'Va': -0.19,
            'P': -1.98 * MW * pos_loads,
            'Q': -0.28 * MW,
        },
        'Bus3': {
            'Vm': 20.009 * kV,
            'Va': -0.19,
            'P': .85 * MW * pos_loads,
            'Q': .53 * MW,
        },
        'Grid': {
            'P': 1.230925 * MW * pos_loads,
            'Q': 0.441486 * MW,
            'Vl': 110,
        },
    }, ndigits=0)
