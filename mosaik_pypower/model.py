"""
This module contains the model types for PYPOWER (:class:`Bus`,
:class:`Branch`, and :class:`Generator`).

"""
from __future__ import division
import json
import math

from pypower import idx_bus, idx_brch, idx_gen
from pypower.api import ppoption, runpf
import numpy


# Indices for the entries of the JSON file
(
    BUS_NAME,
    BUS_TYPE,
    BUS_BASE_KV,
) = range(3)

(
    TRF_NAME,
    TRF_FROM_BUS,
    TRF_TO_BUS,
    TRF_SR,
    TRF_V1,
    TRF_P1,
    TRF_IMAX_P,
    TRF_IMAX_S,
) = range(8)

(
    BRANCH_NAME,
    BRANCH_FROM_BUS,
    BRANCH_TO_BUS,
    BRANCH_L,
    BRANCH_R,
    BRANCH_X,
    BRANCH_C,
    BRACHN_IMAX,
) = range(8)


BUS_PQ_FACTOR = 1000 ** 2  # from MW to W
REFBUS_PQ_FACTOR = 1000 ** 2  # from MW to W
BRANCH_PQ_FACTOR = 1000 ** 2  # from MW to W


class UniqueKeyDict(dict):
    """A :class:`dict` that won't let you insert the same key twice."""
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('Key "%s" already exists in dict.' % key)
        super(UniqueKeyDict, self).__setitem__(key, value)


def load_case(path, magic_factor=1):
    """Load the case from *path* and create a PYPOWER case and an entiy map.

    """
    raw_case = json.load(open(path))
    entity_map = UniqueKeyDict()
    buses, gens = _get_buses(raw_case, entity_map)
    branches = _get_branches(raw_case, entity_map, magic_factor)
    ppc = {
        'baseMVA': raw_case['base_mva'],
        'bus': buses,
        'gen': gens,
        'branch': branches,
    }

    return ppc, entity_map


def reset_inputs(case):
    """Set the (re)active power demand for all buses to zero."""
    for bus in case['bus']:
        bus[idx_bus.PD] = 0
        bus[idx_bus.QD] = 0


def set_inputs(case, etype, idx, data):
    if etype == 'PQBus':
        case['bus'][idx][idx_bus.PD] = data['P'] / BUS_PQ_FACTOR
        if 'Q' in data:
            # Some models may not provide a Q
            case['bus'][idx][idx_bus.QD] = data['Q'] / BUS_PQ_FACTOR
    else:
        raise ValueError('etype %s unknown' % etype)


def perform_powerflow(case):
    ppo = ppoption(OUT_ALL=0, VERBOSE=0)
    res = runpf(case, ppo)
    return res[0]


def update_cache(case, entity_map):
    cache = {}
    for eid, attrs in entity_map.items():
        etype = attrs['etype']
        idx = attrs['idx']
        data = {}

        if case['success']:
            if etype == 'RefBus':  # is internally a bus
                data['P'] = case['gen'][idx][idx_gen.PG] * REFBUS_PQ_FACTOR
                data['Q'] = case['gen'][idx][idx_gen.QG] * REFBUS_PQ_FACTOR
            elif etype == 'PQBus':
                data['P'] = case['bus'][idx][idx_bus.PD] * BUS_PQ_FACTOR
                data['Q'] = case['bus'][idx][idx_bus.QD] * BUS_PQ_FACTOR
                base_kv = case['bus'][idx][idx_bus.BASE_KV]
                data['Vm'] = case['bus'][idx][idx_bus.VM] * base_kv * 1000
                data['Va'] = case['bus'][idx][idx_bus.VA]
            elif etype == 'Branch' or etype == 'Transformer':
                data['P_from'] = case['branch'][idx][idx_brch.PF] * BRANCH_PQ_FACTOR  # NOQA
                data['Q_from'] = case['branch'][idx][idx_brch.QF] * BRANCH_PQ_FACTOR  # NOQA
                data['P_to'] = case['branch'][idx][idx_brch.PT] * BRANCH_PQ_FACTOR  # NOQA
                data['Q_to'] = case['branch'][idx][idx_brch.QT] * BRANCH_PQ_FACTOR  # NOQA
        else:
            # Failed to converge.
            if etype == 'RefBus':
                data['P'] = float('nan')
                data['Q'] = float('nan')
            elif etype == 'PQBus':
                data['P'] = float('nan')
                data['Q'] = float('nan')
                data['Vm'] = float('nan')
                data['Va'] = float('nan')
            elif etype == 'Branch' or etype == 'Transformer':
                data['P_from'] = float('nan')
                data['Q_from'] = float('nan')
                data['P_to'] = float('nan')
                data['Q_to'] = float('nan')

        cache[eid] = data
    return cache


def _get_buses(raw_case, entity_map):
    """Create the PP bus and generator lists and update the *entity_map* with
    all buses.

    """
    buses = []
    gens = []
    for i, (bus_id, bus_type, base_kv) in enumerate(raw_case['bus']):
        # Create PYPOWER bus:
        #             id bus_type                    Pd Qd Gs Bs area Vm Va
        #             baseKV   zone Vmax Vmin
        buses.append((i, getattr(idx_bus, bus_type), 0, 0, 0, 0, 1,   1, 0,
                      base_kv, 1,   1.1, 0.9))
        if bus_type == 'REF':
            # Create generator for reference buses:
            # bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1, Pc2,
            # Qc1min, Qc1max, Qc2min, Qc2max, ramp_agc, ramp_10, ramp_30,
            # ramp_q, apf
            gens.append((i, 0.0, 0.0, 999.0, -999.0, 1.0, raw_case['base_mva'],
                         1, 999.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

            entity_map[bus_id] = {'etype': 'RefBus', 'idx': i, 'static': {
                'vl': base_kv,
            }}

        else:
            entity_map[bus_id] = {'etype': 'PQBus', 'idx': i, 'static': {
                'vl': base_kv,
            }}

    return numpy.array(buses), numpy.array(gens)


def _get_branches(raw_case, entity_map, magic_factor=1):
    """Parse the transformers and branches, return the list of branches for
    PP and update the entity_map.

    """
    branches = []
    base_mva = raw_case['base_mva']
    buses = raw_case['bus']

    # Load transformers
    for i, (tid, from_bus, to_bus, Sr, v1, P1, Imax_p, Imax_s) in enumerate(
            raw_case['trafo']):
        if not from_bus in entity_map or not to_bus in entity_map:
            raise ValueError('Bus "%s" or "%s" not found.' %
                             (from_bus, to_bus))

        idx = len(branches)
        from_bus_idx = entity_map[from_bus]['idx']
        to_bus_idx = entity_map[to_bus]['idx']
        from_bus = buses[from_bus_idx]  # Get bus from JSON
        to_bus = buses[to_bus_idx]  # Get bus from JSON

        # Update entity map with etype and static data
        entity_map[tid] = {'etype': 'Transformer', 'idx': idx, 'static': {
            's_max': Sr,  # 'prim_bus': from_bus[0], 'sec_bus': to_bus[0],
            'u_p': from_bus[BUS_BASE_KV],
            'u_s': to_bus[BUS_BASE_KV],
            'i_max_p': Imax_p,
            'i_max_s': Imax_s,
        }, 'related': [from_bus[0], to_bus[0]]}

        branch = _make_transformer(from_bus_idx, to_bus_idx, Sr,
                                   from_bus[BUS_BASE_KV], to_bus[BUS_BASE_KV],
                                   v1, P1, base_mva)
        branches.append(branch)

    #Load other branches
    omega = 2 * math.pi * 50  # s^-1
    for i, (bid, from_bus, to_bus, l, r, x, c, Imax) in enumerate(
            raw_case['branch']):
        if from_bus not in entity_map:
            raise ValueError('From "%s" not found for branch "%s"' %
                             (from_bus, bid))
        if to_bus not in entity_map:
            raise ValueError('To "%s" not found for branch "%s"' %
                             (to_bus, bid))

        idx = len(branches)
        from_bus_idx = entity_map[from_bus]['idx']
        to_bus_idx = entity_map[to_bus]['idx']
        from_bus = buses[from_bus_idx]  # Get bus from JSON
        to_bus = buses[to_bus_idx]  # Get bus from JSON

        # Calculate some branch parameters
        base_kv = from_bus[BUS_BASE_KV]  # kV
        Smax = base_kv * Imax / 1000  # MVA
        base_z = base_kv ** 2 / base_mva  # Ohm
        c *= magic_factor
        b = (omega * c / (10 ** 9))  # b in Ohm^-1, c is in nF

        # Update entiy map
        entity_map[bid] = {'etype': 'Branch', 'idx': idx, 'static': {
            's_max': Smax,
            'i_max': Imax,
            'length': l,
            'r_per_km': r,
            'x_per_km': x,
            'c_per_km': c,
        }, 'related': [from_bus[0], to_bus[0]]}

        # Create branch
        # fbus, tbus, r, x,
        # b, rateA, rateB, rateC,ratio, angle, status, angmin, angmax
        branch = (from_bus_idx, to_bus_idx, r * l / base_z, x * l / base_z,
                  b * l * base_z, Smax, Smax, Smax, 0, 0, 1, -360, 360)
        branches.append(branch)

    return numpy.array(branches)


def _make_transformer(from_bus, to_bus, Sr, Vp, Vs, v1, P1, base_mva):
    """Helper to create a transformer-branch for PP.

    v1 aka u_k, P1 aka P_k

    """
    # Calculate resistances
    # See: Adolf J. Schwab: Elektroenergiesysteme, pp. 385, 3rd edition, 2012
    #X_k = (u_k * (U_p ** 2)) / (100 * S)
    X01 = (v1 * (Vp ** 2)) / (100 * Sr)  # Ohm

    #R_k = (P_k * (X_k ** 2)) / ((u_k * U_p / 100) ** 2)
    R01 = (P1 * (X01 ** 2)) / ((v1 * Vp / 100) ** 2)  # Ohm
    base_z = Vp ** 2 / base_mva

    # Create branch
    # fbus, tbus, r, x, b, rateA, rateB, rateC,
    # ratio, angle, status, angmin, angmax
    branch = (from_bus, to_bus, R01 / base_z, X01 / base_z, 0, Sr, Sr, Sr,
              1, 0, 1, -360, 360)
    return branch
