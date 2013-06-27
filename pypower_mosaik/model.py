"""
This module contains the model types for PYPOWER (:class:`Bus`,
:class:`Branch`, and :class:`Generator`).

"""
import json

import numpy
import pypower


def load_case(path):
    raw_case = json.load(open(path))
    bus_map, buses = _get_buses(raw_case)
    gen_map, generators = _get_generators(raw_case)
    branch_map, branches = _get_branches(raw_case)
    ppc = {
        'baseMVA': raw_case['base_mva'],
        'bus': buses,
        'gen': generators,
        'branch': branches,
    }
    eid_map = _create_eid_map(bus_map, gen_map, branch_map)

    return ppc, eid_map


def _get_buses(raw_case):
    bus_map = []
    buses = []
    for i, (bus_id, bus_type, base_kv) in enumerate(raw_case['bus']):
        bus_map.append((bus_id, i))
        buses.append((i, getattr(pypower.idx_bus, bus_type),
                      0, 0, 0, 0, 1,   1, 0, base_kv, 1,   1.1, 0.9))
        #             Pd Qd Gs Bs area Vm Va baseKV   zone Vmax Vmin

    return bus_map, numpy.array(buses)


def _get_generators(raw_case):
    gen_map = []
    gens = []
    for i, (gen_id, bus_id) in enumerate(raw_case['gen']):
        gen_map.append((gen_id, i))
        gens.append((bus_id, 0, 0,
