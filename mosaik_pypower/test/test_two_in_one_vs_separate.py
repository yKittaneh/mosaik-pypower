"""
Compare the results for two different setups::

    Two in one    vs.   Separate grids

      o___                o     o
      |   \               |     |
      8    8              8     8
      |    |              |     |
      o    o              o     o
     / \   |             / \    |
    o   o  o            o   o   o

The nodes below the transformers (8) should have the same voltages. The sum
of the ref. nodes in the "separate grids" case should also equal the load of
the ref. node in the "two in one" case.

"""
from os.path import dirname, join

import numpy as np

from mosaik_pypower import model


def test_two_in_one_vs_separate():
    path = join(dirname(__file__), 'data')
    cases = [model.load_case(join(path, f)) for f in ['two_in_one.json',
                                                      'two_separate_1.json',
                                                      'two_separate_2.json']]

    inputs = [
        [
            {'p': 0, 'q': 0},        # Grid
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
        ],
        [
            {'p': 0, 'q': 0},        # Grid
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
        ],
        [
            {'p': 0, 'q': 0},        # Grid
            {'p': 1000000, 'q': 0},
            {'p': 1000000, 'q': 0},
        ],
    ]
    for (ppc, _), inputs in zip(cases, inputs):
        for i, data in enumerate(inputs):
            model.set_inputs(ppc, 'PQBus', i, data)

    results = [model.perform_powerflow(ppc) for ppc, _ in cases]
    for r in results:
        assert r['success'] == 1

    # Compare PG und QG for all generators
    assert np.allclose(results[0]['gen'][:,1:3],
                       (results[1]['gen'] + results[2]['gen'])[:,1:3])
