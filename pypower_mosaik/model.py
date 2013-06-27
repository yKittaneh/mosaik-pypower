"""
This module contains the model types for PYPOWER (:class:`Bus`,
:class:`Branch`, and :class:`Generator`).

"""
import collections
import json
import math

from pypower import idx_bus
import numpy


Bus = collections.namedtuple('Bus', 'idx')
Generator = collections.namedtuple('Generator', 'idx, bus_id ')
Transformer = collections.namedtuple('Transformer', 'idx, from_bus, to_bus')
Branch = collections.namedtuple('Branch', 'idx, from_bus, to_bus')


class UniqueKeyDict(dict):
    """A :class:`dict` that won't let you insert the same key twice."""
    def __setitem__(self, key, value):
        if key in self:
            raise KeyError('Key "%s" already exists in dict.' % key)
        super(UniqueKeyDict, self).__setitem__(key, value)


def load_case(path):
    raw_case = json.load(open(path))
    entity_map = UniqueKeyDict()
    buses, gens = _get_buses(raw_case, entity_map)
    branches = _get_branches(raw_case, entity_map)
    ppc = {
        'baseMVA': raw_case['base_mva'],
        'bus': buses,
        'gen': generators,
        'branch': branches,
    }

    return ppc, eid_map


def _get_buses(raw_case, entity_map):
    buses = []
    gens = []
    for i, (bus_id, bus_type, base_kv) in enumerate(raw_case['bus']):
        entity_map[bus_id] = Bus(i)

        # Create PYPOWER bus:
        #             id bus_type
        #             Pd Qd Gs Bs area Vm Va baseKV   zone Vmax Vmin
        buses.append((i, getattr(pypower.idx_bus, bus_type),
                      0, 0, 0, 0, 1,   1, 0, base_kv, 1,   1.1, 0.9))

        if bus_type == 'REF':
            # Create generator for reference buses:
            # bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1, Pc2,
            # Qc1min, Qc1max, Qc2min, Qc2max, ramp_agc, ramp_10, ramp_30,
            # ramp_q, apf
            gens.append((i, 0.0, 0.0, 999.0, -999.0, 1.0, raw_case['base_mva'],
                         1, 999.0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0))

    return numpy.array(buses), numpy.array(gens)


def _get_branches(raw_case, entity_map, buses):
    branches = []
    trafo_map = {}
    base_mva = raw_case['base_mva']
    for i, (tid, from_bus, to_bus, Sr, v1, P1) in enumerate(raw_case['trafo']):
        if not from_bus in entiy_map or to_bus in to_bus:
            raise ValueError('Bus "%s" or "%s" not found.' %
                             (from_bus, to_bus))
        entity_map[tid] = Transformer(len(branches), from_bus, to_bus)
        from_bus = buses[entity_map[from_bus].idx]
        to_bus = buses[entity_map[to_bus].idx]
        branches.append(_make_transformer(from_bus, to_bus, Sr, v1, P1,
                                          base_mva))

    omega = 2 * math.pi * 50  # s^-1
    for i, (bid, from_bus, to_bus, l, r, x, c, Imax) in enumerate(
            raw_case('branch')):
        if not from_bus in entiy_map or to_bus in to_bus:
            raise ValueError('Bus "%s" or "%s" not found.' %
                             (from_bus, to_bus))
        entity_map[tid] = Branch(len(branches), from_bus, to_bus)
        from_bus = buses[entity_map[from_bus].idx]
        to_bus = buses[entity_map[to_bus].idx]

        # Calculate Smax and b
        base_kv = [pypower.idx_bus.BASE_KV] # kV
        base_z = base_kv ** 2 / base_mva  # Ohm
        Smax = base_kv * Imax / 1000  # MVA
        b = (omega * c / (10 ** 6))  # b in Ohm^-1, c is in muF

        # Create branch
        # fbus, tbus, r, x, b, rateA, rateB, rateC,ratio, angle, status,
        # angmin, angmax
        branch = (from_bus[idx_bus.BUS_I], to_bus[idx_bus.BUS_I], r / base_z,
                r / base_z, b * base_z, Sr, Sr, Sr, 0, 0, 1, -360, 360)
        branches.append(branch)


def _make_transformer(from_bus, to_bus, Sr, v1, P1, base_MVA):
    # Get primary and secondary voltage from connected buses
    Vp = from_bus[idx_bus.BASE_KV]
    Vs = to_bus[idx_bus.BASE_KV]

    # Calculate resistances
    # See: Adolf J. Schwab: Elektroenergiesysteme, pp. 385, 3rd edition, 2012
    X01 = (u1 * (Vp ** 2)) / (100 * Sr)  # Ohm
    R01 = (P1 * (X01 ** 2)) / ((v1 * Vp / 100) ** 2)  # Ohm
    base_z = Vp ** 2 / base_mva

    # Create branch
    # fbus, tbus, r, x, b, rateA, rateB, rateC,ratio, angle, status, angmin,
    # angmax
    branch = (from_bus[idx_bus.BUS_I], to_bus[idx_bus.BUS_I], R01 / base_z,
              X01 / base_z, 0, Sr, Sr, Sr, 1, 0, 1, -360, 360)
    return branch
