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
power_factor = 3  # Divide all incoming loads by this factor
sqrt_3 = math.sqrt(3)
omega = 2 * math.pi * 50  # s^-1

# Indices for the entries of the JSON file
BUS_NAME = 0
BUS_TYPE = 1
BUS_BASE_KV = 2

BUS_PQ_FACTOR = power_factor * 1e6  # from MW to W
BRANCH_PQ_FACTOR = power_factor * 1e6  # from MW to W


def load_case(path, grid_idx):
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
    buses = _get_buses(loader, raw_case, entity_map, grid_idx)
    branches = _get_branches(loader, raw_case, entity_map, grid_idx)
    base_mva = loader.base_mva(raw_case, buses)

    ppc = _make_ppc(base_mva, buses, branches)
    return ppc, entity_map


def reset_inputs(case):
    """Set the (re)active power demand for all buses to zero."""
    for bus in case['bus']:
        bus[idx_bus.PD] = 0
        bus[idx_bus.QD] = 0


def set_inputs(case, etype, idx, data, static):
    if etype == 'PQBus':
        case['bus'][idx][idx_bus.PD] = data['P'] / BUS_PQ_FACTOR
        if 'Q' in data:
            # Some models may not provide a Q
            case['bus'][idx][idx_bus.QD] = data['Q'] / BUS_PQ_FACTOR
    elif etype in ('PQBus', 'Transformer'):
        if 'tap_turn' in data and etype == 'Transformer':
            tap = 1 / static['taps'][data['tap_turn']]
            case['branch'][idx][idx_brch.TAP] = tap
        if 'online' in data:
            case['branch'][idx][idx_brch.BR_STATUS] = int(data['online'])
    else:
        raise ValueError('etype %s unknown' % etype)


def perform_powerflow(case):
    ppo = ppoption(OUT_ALL=0, VERBOSE=0)
    res = runpf(case, ppo)
    return res[0]


def get_cache_entries(cases, entity_map):
    cache = {}
    for eid, attrs in entity_map.items():
        case = case_for_eid(eid, cases)
        etype = attrs['etype']
        idx = attrs['idx']
        data = {}

        if case['success']:
            if etype == 'RefBus':
                gen = case['gen'][idx]
                bus = case['bus'][idx]
                data['P'] = gen[idx_gen.PG] * BUS_PQ_FACTOR
                data['Q'] = gen[idx_gen.QG] * BUS_PQ_FACTOR
                data['Vm'] = bus[idx_bus.VM] * attrs['static']['Vl']
                data['Va'] = bus[idx_bus.VA]
            elif etype == 'PQBus':
                bus = case['bus'][idx]
                data['P'] = bus[idx_bus.PD] * BUS_PQ_FACTOR
                data['Q'] = bus[idx_bus.QD] * BUS_PQ_FACTOR
                data['Vm'] = bus[idx_bus.VM] * attrs['static']['Vl']
                data['Va'] = bus[idx_bus.VA]
            elif etype in ('Branch', 'Transformer'):
                branch = case['branch'][idx]

                # Compute complex current for branches
                if etype == 'Branch':
                    fbus = case['bus'][branch[idx_brch.F_BUS]]
                    tbus = case['bus'][branch[idx_brch.T_BUS]]
                    fbus_v = fbus[idx_bus.VM]
                    tbus_v = tbus[idx_bus.VM]
                    base_kv = fbus[idx_bus.BASE_KV]

                    # Use side with higher voltage to calculate I
                    if fbus_v >= tbus_v:
                        ir = branch[idx_brch.PF] / fbus_v
                        ii = branch[idx_brch.QF] / tbus_v
                    else:
                        ir = branch[idx_brch.PT] / tbus_v
                        ii = branch[idx_brch.QT] / tbus_v

                    # ir/ii are in [MVA]; [MVA] * 1000 / [kV] = [A]
                    data['I_real'] = ir * 1000 / base_kv
                    data['I_imag'] = ii * 1000 / base_kv

                data['P_from'] = branch[idx_brch.PF] * BRANCH_PQ_FACTOR
                data['Q_from'] = branch[idx_brch.QF] * BRANCH_PQ_FACTOR
                data['P_to'] = branch[idx_brch.PT] * BRANCH_PQ_FACTOR
                data['Q_to'] = branch[idx_brch.QT] * BRANCH_PQ_FACTOR
        else:
            # Failed to converge.
            if etype in ('RefBus', 'PQBus'):
                data['P'] = float('nan')
                data['Q'] = float('nan')
                data['Vm'] = float('nan')
                data['Va'] = float('nan')
            elif etype in ('Branch', 'Transformer'):
                data['P_from'] = float('nan')
                data['Q_from'] = float('nan')
                data['P_to'] = float('nan')
                data['Q_to'] = float('nan')

        cache[eid] = data
    return cache


def make_eid(name, grid_idx):
    return '%s/%s' % (grid_idx, name)


def case_for_eid(eid, case):
    idx = eid.split('/')[0]
    return case[int(idx)]


def _get_buses(loader, raw_case, entity_map, grid_idx):
    buses = []
    for idx, (bid, btype, base_kv) in enumerate(loader.buses(raw_case)):
        eid = make_eid(bid, grid_idx)
        buses.append((idx, btype, base_kv))
        etype = 'RefBus' if btype == 'REF' else 'PQBus'
        entity_map[eid] = {
            'etype': etype,
            'idx': idx,
            'static': {
                'Vl': base_kv * 1000,  # From [kV] to [V]
            },
        }
    return buses


def _get_branches(loader, raw_case, entity_map, grid_idx):
    branches = []
    for idx, branch in enumerate(loader.branches(raw_case, entity_map)):
        is_trafo, bid, fbus, tbus, length, bdata, online, tap_turn = branch
        eid = make_eid(bid, grid_idx)
        fbus = make_eid(fbus, grid_idx)
        tbus = make_eid(tbus, grid_idx)

        assert fbus in entity_map, fbus
        assert tbus in entity_map, fbus

        f_idx = entity_map[fbus]['idx']
        t_idx = entity_map[tbus]['idx']

        if is_trafo:
            s_max, p_loss, r, x, taps = bdata
            b = 0
            tap = 1.0 / taps[tap_turn]

            # Update entity map with etype and static data
            entity_map[eid] = {'etype': 'Transformer', 'idx': idx, 'static': {
                'S_r': s_max * 1e6,  # From [MVA] to [VA]
                'P_loss': p_loss * 1000,  # From [kW] to [W]
                'U_p': entity_map[fbus]['static']['Vl'],
                'U_s': entity_map[tbus]['static']['Vl'],
                'taps': taps,
                'tap_turn': tap_turn,
                'online': bool(online),
            }, 'related': [fbus, tbus]}

        else:
            r, x, c, i_max = bdata
            c /= 1e9  # From [nF] to [F]
            b = (omega * power_factor * c)  # b [Ohm^-1], c [F]
            base_v = entity_map[fbus]['static']['Vl'] # [V]
            s_max = base_v * i_max  # [VA]
            tap = 0
            entity_map[eid] = {'etype': 'Branch', 'idx': idx, 'static': {
                'S_max': s_max,
                'I_max': i_max,
                'length': length,
                'R_per_km': r,
                'X_per_km': x,
                'C_per_km': c,
                'online': bool(online),
            }, 'related': [fbus, tbus]}
            s_max /= 1e6  # From [VA] to [MVA]

        branches.append((f_idx, t_idx, length, r, x, b, s_max, online, tap))
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
    for f, t, l, r, x, b, s_max, online, tap in branch_data:
        base_kv = buses[int(f)][idx_bus.BASE_KV]  # kV
        base_z = base_kv ** 2 / base_mva  # Ohm
        branches.append((f, t, r * l / base_z, x * l / base_z, b * l * base_z,
                         s_max, s_max, s_max, tap, 0, online, -360, 360))

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
                # FIXME: Using "0" as grid index is an ugly hack but I'm going
                #        remove the old format soon anyway ...
                Us = entity_map['0/%s' % tbus]['static']['Vl'] / 1000  # kV
                Xk = (Uk * (Us ** 2)) / (100 * Sr)  # Ohm
                Rk = (Pk * (Xk ** 2)) / ((Uk * Us / 100) ** 2)  # Ohm

                info = (Sr, 0, Rk, Xk, {0: 1.0})
                yield (True, tid, fbus, tbus, 1, info, 1, 0)

            for bid, fbus, tbus, l, r, x, c, i_max in raw_case['branch']:
                info = (r, x, c, i_max)
                yield (False, bid, fbus, tbus, l, info, 1, 0)

        else:
            # New format
            for tid, fbus, tbus, ttype, online, tap in raw_case['trafo']:
                trafo = rdb.transformers[ttype]
                yield (True, tid, fbus, tbus, 1, trafo, int(online), tap)

            for bid, fbus, tbus, btype, l, online in raw_case['branch']:
                line = rdb.lines[btype]
                yield (False, bid, fbus, tbus, l, line, int(online), 0)

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
            if str(sheet.cell_value(i, 0)).startswith('#'):
                continue

            bus_id, bus_type, base_kv = sheet.row_values(i)[:3]
            if type(bus_id) is float:
                bus_id = str(int(bus_id))
            yield (bus_id, bus_type, base_kv)

    def branches(wb, entity_map):
        sheet = wb.sheet_by_index(1)
        for i in range(1, sheet.nrows):
            if str(sheet.cell_value(i, 0)).startswith('#'):
                continue

            bid, fbus, tbus, btype, l, online, tap = sheet.row_values(i)[:7]
            if type(bid) is float:
                bid = str(int(bid))
            try:
                info = rdb.transformers[btype]
                is_trafo = True
            except KeyError:
                info = rdb.lines[btype]
                is_trafo = False
            yield (is_trafo, bid, fbus, tbus, l, info, online, 0)

    def base_mva(raw_case, buses):
        return rdb.base_mva.get(buses[0][BUS_BASE_KV], 1)
