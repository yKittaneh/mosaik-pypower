"""
This module contains the model types for PYPOWER (:class:`Bus`,
:class:`Branch`, and :class:`Generator`).

"""
from __future__ import division
import json
import math
import os.path

from pypower import idx_bus, idx_brch, idx_gen
from pypower.api import ppoption, runpf
import numpy
import xlrd

from mosaik_pypower import resource_db as rdb


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


def load_case(path):
    """Load the case from *path* and create a PYPOWER case and an entity map.
    """
    loaders = {
        '.json': JSON,
        '.xlsx': Excel,
    }
    try:
        ext = os.path.splitext(path)[-1]
        loader = loaders[ext]
    except KeyError:
        raise ValueError("Don't know how to open '%s'" % path)

    entity_map = UniqueKeyDict()

    raw_case = loader.open(path)
    buses = _get_buses(loader, raw_case, entity_map)
    branches = _get_branches(loader, raw_case, entity_map)
    base_mva = loader.base_mva(raw_case, buses)

    ppc = _make_ppc(base_mva, buses, branches)
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
                data['Vm'] = case['bus'][idx][idx_bus.VM] * attrs['static']['Vl'] * 1000  # NOQA
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


def _get_buses(loader, raw_case, entity_map):
    buses = []
    for idx, (bid, btype, base_kv) in enumerate(loader.buses(raw_case)):
        buses.append((idx, btype, base_kv))
        etype = 'RefBus' if btype == 'REF' else 'PQBus'
        entity_map[bid] = {
            'etype': etype,
            'idx': idx,
            'static': {
                'Vl': base_kv,
            },
        }
    return buses


def _get_branches(loader, raw_case, entity_map):
    branches = []
    for idx, (is_trafo, bid, fbus, tbus, length, bdata, tap_turn) in enumerate(
            loader.branches(raw_case, entity_map)):
        assert fbus in entity_map, fbus
        assert tbus in entity_map, fbus

        f_idx = entity_map[fbus]['idx']
        t_idx = entity_map[tbus]['idx']

        if is_trafo:
            s_max, p_loss, r, x, taps = bdata
            b = 0
            tap = 1.0 / taps[tap_turn]

            # Update entity map with etype and static data
            entity_map[bid] = {'etype': 'Transformer', 'idx': idx, 'static': {
                'S_r': s_max,
                'P_loss': p_loss,
                'U_p': entity_map[fbus]['static']['Vl'],
                'U_s': entity_map[tbus]['static']['Vl'],
                'taps': taps,
                'tap_turn': tap_turn,
            }, 'related': [fbus, tbus]}

        else:
            r, x, c, i_max = bdata
            b = (omega * power_factor * c / (10 ** 9))  # b [Ohm^-1], c [nF]
            base_kv = entity_map[fbus]['static']['Vl']  # kV
            s_max = base_kv * i_max / 1000  # MVA
            tap = 0
            entity_map[bid] = {'etype': 'Branch', 'idx': idx, 'static': {
                'S_max': s_max,
                'I_max': i_max,
                'length': length,
                'R_per_km': r,
                'X_per_km': x,
                'C_per_km': c,
            }, 'related': [fbus, tbus]}

        branches.append((f_idx, t_idx, length, r, x, b, s_max, tap))
    return branches


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
    for f, t, l, r, x, b, s_max, tap in branch_data:
        base_kv = buses[int(f)][idx_bus.BASE_KV]  # kV
        base_z = base_kv ** 2 / base_mva  # Ohm
        branches.append((f, t, r * l / base_z, x * l / base_z, b * l * base_z,
                         s_max, s_max, s_max, tap, 0, 1, -360, 360))

    return {
        'baseMVA': base_mva,
        'bus': numpy.array(buses, dtype=float),
        'gen': numpy.array(gens, dtype=float),
        'branch': numpy.array(branches, dtype=float),
    }


class UniqueKeyDict(dict):
    """A :class:`dict` that won't let you insert the same key twice."""
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('Key "%s" already exists in dict.' % key)
        super(UniqueKeyDict, self).__setitem__(key, value)


class JSON:
    """Namespace that provides functions for loading cases in the JSON format.
    """
    def open(path):
        return json.load(open(path))

    def buses(raw_case):
        for bus_id, bus_type, base_kv in raw_case['bus']:
            yield (bus_id, bus_type, base_kv)

    def branches(raw_case, entity_map):
        if 'base_mva' in raw_case:
            # Old format
            for tid, fbus, tbus, Sr, Uk, Pk, _, _ in raw_case['trafo']:
                # Calculate resistances; See: Adolf J. Schwab:
                # Elektroenergiesysteme, pp. 385, 3rd edition, 2012
                Us = entity_map[tbus]['static']['Vl']  # kV
                Xk = (Uk * (Us ** 2)) / (100 * Sr)  # Ohm
                Rk = (Pk * (Xk ** 2)) / ((Uk * Us / 100) ** 2)  # Ohm

                yield (True, tid, fbus, tbus, 1, (Sr, 0, Rk, Xk, {0: 1.0}), 0)

            for bid, fbus, tbus, l, r, x, c, i_max in raw_case['branch']:
                yield (False, bid, fbus, tbus, l, (r, x, c, i_max), 0)

        else:
            # New format
            for tid, fbus, tbus, ttype, online, tap in raw_case['trafo']:
                trafo = rdb.transformers[ttype]
                yield (True, tid, fbus, tbus, 1, trafo, tap)

            for bid, fbus, tbus, btype, l, online in raw_case['branch']:
                line = rdb.lines[btype]
                yield (False, bid, fbus, tbus, l, line, 0)

    def base_mva(raw_case, buses):
        if 'base_mva' in raw_case:
            base_mva = raw_case['base_mva']
        else:
            base_mva = rdb.base_mva.get(buses[0][BUS_BASE_KV])
        return base_mva


class Excel:
    """Namespace that provides functions for loading cases in the JSON format.
    """
    def open(path):
        return xlrd.open_workbook(path, on_demand=True)

    def buses(wb):
        sheet = wb.sheet_by_index(0)
        for i in range(1, sheet.nrows):
            if sheet.cell_value(i, 0).startswith('#'):
                continue

            yield sheet.row_values(i)[:3]

    def branches(wb, entity_map):
        sheet = wb.sheet_by_index(1)
        for i in range(1, sheet.nrows):
            if sheet.cell_value(i, 0).startswith('#'):
                continue

            bid, fbus, tbus, btype, l, online, tap = sheet.row_values(i)[:7]
            try:
                trafo = rdb.transformers[btype]
                yield (True, bid, fbus, tbus, 1, trafo, tap)

            except KeyError:
                # Calculate some branch parameters
                line = rdb.lines[btype]
                yield (False, bid, fbus, tbus, l, line, 0)

    def base_mva(raw_case, buses):
        return rdb.base_mva.get(buses[0][BUS_BASE_KV], 1)
