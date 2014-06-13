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

# The line params that we read are for 1 of 3 wires within a cable,
# but the loads and feed-in is meant for the complete cable, so we
# have to divide all loads and feed-in by 3.
# TODO: Replace with parameter to switch between line-to-line and
# phase-to-neutral voltage.
power_factor = 3  # Divide all incoming loads by this factor
sqrt_3 = math.sqrt(3)
omega = 2 * math.pi * 50  # s^-1


# Indices for the entries of the JSON file
BUS_NAME = 0
BUS_TYPE = 1
BUS_BASE_KV = 2

BUS_PQ_FACTOR = power_factor * 1000 ** 2  # from MW to W
REFBUS_PQ_FACTOR = power_factor * 1000 ** 2  # from MW to W
BRANCH_PQ_FACTOR = power_factor * 1000 ** 2  # from MW to W


class UniqueKeyDict(dict):
    """A :class:`dict` that won't let you insert the same key twice."""
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('Key "%s" already exists in dict.' % key)
        super(UniqueKeyDict, self).__setitem__(key, value)


def load_case(path):
    """Load the case from *path* and create a PYPOWER case and an entiy map.

    """
    entity_map = UniqueKeyDict()
    if path.endswith('.json'):
        ppc_data = _load_json(path, entity_map)
    elif path.endswith('.xlsx'):
        ppc_data = _load_excel(path, entity_map)
    else:
        raise ValueError("Don't know how to open '%s'" % path)

    ppc = _make_ppc(*ppc_data)

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
                data['Vm'] = case['bus'][idx][idx_bus.VM] * attrs['static']['vl'] * 1000  # NOQA
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


def _load_json(path, entity_map):
    raw_case = json.load(open(path))

    if 'base_mva' in raw_case:
        base_mva = raw_case['base_mva']
        buses = _get_buses_old(raw_case, entity_map)
        branches = _get_branches_old(raw_case, entity_map)
    else:
        pass

    return base_mva, buses, branches


def _load_excel(path):
    # TODO: implement
    return None


def _get_buses_old(raw_case, entity_map):
    """Create the PP bus and generator lists and update the *entity_map* with
    all buses.

    """
    buses = []
    for i, (bus_id, bus_type, base_kv) in enumerate(raw_case['bus']):
        buses.append((i, bus_type, base_kv))
        etype = 'RefBus' if bus_type == 'REF' else 'PQBus'
        entity_map[bus_id] = {
            'etype': etype,
            'idx': i,
            'static': {
                'vl': base_kv,
            },
        }

    return buses


def _get_branches_old(raw_case, entity_map):
    """Parse the transformers and branches, return the list of branches for
    PP and update the entity_map.

    """
    branches = []
    buses = raw_case['bus']

    # Load transformers (Imax_p and Imax_s are no longer required)
    for i, (tid, from_bus, to_bus, Sr, Uk, Pk, Imax_p, Imax_s) in enumerate(
            raw_case['trafo']):
        if from_bus not in entity_map or to_bus not in entity_map:
            raise ValueError('Bus "%s" or "%s" not found.' %
                             (from_bus, to_bus))

        idx = len(branches)
        from_bus_idx = entity_map[from_bus]['idx']
        to_bus_idx = entity_map[to_bus]['idx']
        from_bus = buses[from_bus_idx]  # Get bus from JSON
        to_bus = buses[to_bus_idx]  # Get bus from JSON

        # Update entity map with etype and static data
        entity_map[tid] = {'etype': 'Transformer', 'idx': idx, 'static': {
            'S_max': Sr,
            'P_loss': 0.0,  # Unkown in this format
            'U_p': from_bus[BUS_BASE_KV],
            'U_s': to_bus[BUS_BASE_KV],
        }, 'related': [from_bus[0], to_bus[0]]}

        # Calculate resistances
        # See: Adolf J. Schwab: Elektroenergiesysteme, pp. 385,
        #      3rd edition, 2012
        Us = to_bus[BUS_BASE_KV]
        Xk = (Uk * (Us ** 2)) / (100 * Sr)  # Ohm
        Rk = (Pk * (Xk ** 2)) / ((Uk * Us / 100) ** 2)  # Ohm
        branches.append((from_bus_idx, to_bus_idx, 1, Rk, Xk, 0, Sr))

    # Load branches
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
        b = (omega * power_factor * c / (10 ** 9))  # b in Ohm^-1, c is in nF

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
        branches.append((from_bus_idx, to_bus_idx, l, r, x, b, Smax))

    return numpy.array(branches)


def _make_ppc(base_mva, bus_data, branch_data):
    buses = []
    gens = []
    for idx, btype, base_kv in bus_data:
        btype = getattr(idx_bus, btype)
        base_kv /= sqrt_3  # Convert from line-to-line to phase-to-neutral
        buses.append((idx, btype, 0, 0, 0, 0, 1, 1, 0, base_kv, 1, 1.04, 0.96))
        if btype == idx_bus.REF:
            assert idx == 0, 'RefBus must be the first element in the list.'
            gens.append((idx, 0.0, 0.0, 999.0, -999.0, 1.0, base_mva, 1, 999.0,
                         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    branches = []
    for f, t, l, r, x, b, s_max in branch_data:
        base_kv = buses[int(f)][idx_bus.BASE_KV]  # kV
        base_z = base_kv ** 2 / base_mva  # Ohm
        branches.append((f, t, r * l / base_z, x * l / base_z, b * l * base_z,
                         s_max, s_max, s_max, 0, 0, 1, -360, 360))

    return {
        'baseMVA': base_mva,
        'bus': numpy.array(buses, dtype=float),
        'gen': numpy.array(gens, dtype=float),
        'branch': numpy.array(branches, dtype=float),
    }
