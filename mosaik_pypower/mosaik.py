"""
This module implements the mosaik API for `PYPOWER
<https://pypi.python.org/pypi/PYPOWER>`_.

"""
from __future__ import division
import logging
import os
import mosaik_api

from mosaik_pypower import model


logger = logging.getLogger('pypower.mosaik')

meta = {
    'models': {
        'Grid': {
            'public': True,
            'params': [
                'gridfile',  # Name of the file containing the grid topology.
            ],
            'attrs': [],
        },
        'RefBus': {
            'public': False,
            'params': [],
            'attrs': ['P', 'Q'],  # [W, VAr]
        },
        'PQBus': {
            'public': False,
            'params': [],
            'attrs': ['P', 'Q', 'Vm', 'Va'],  # [W, VAr, V, deg]
        },
        'Transformer': {
            'public': False,
            'params': [],
            'attrs': ['P_from', 'Q_from', 'P_to', 'Q_to'],  # [W, VAr] * 2
        },
        'Branch': {
            'public': False,
            'params': [],
            'attrs': ['P_from', 'Q_from', 'P_to', 'Q_to'],  # [W, VAr] * 2
        },
    },
}


class PyPower(mosaik_api.Simulator):
    def __init__(self):
        super(PyPower, self).__init__(meta)
        self.step_size = None

        # In PYPOWER loads are positive numbers and feed-in is expressed via
        # negative numbers. "init()" will that this flag to "1" in this case.
        # If incoming values for loads are negative and feed-in is positive,
        # this attribute must be set to -1.
        self.pos_loads = None

        # The line params that we read are for 1 of 3 wires within a cable,
        # but the loads and feed-in is meant for the complete cable, so we
        # have to divide all loads and feed-in by 3.
        self._magic_factor = 3  # Divide all incoming loads by this factor

        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)
        self._ppc = None  # The pypower case
        self._data_cache = {}  # Cache for load flow outputs

    def init(self, step_size, pos_loads=True):
        logger.debug('Power flow will be computed every %d seconds.' %
                     step_size)
        signs = ('positive', 'negative')
        logger.debug('Loads will be %s numbers, feed-in %s numbers.' %
                     signs if pos_loads else tuple(reversed(signs)))

        self.step_size = step_size
        self.pos_loads = 1 if pos_loads else -1

        return self.meta

    def create(self, num, modelname, gridfile):
        if num != 1 or self._entities:
            raise ValueError('Can only one grid instance.')
        if modelname != 'Grid':
            raise ValueError('Unknown model: "%s"' % modelname)
        if not os.path.isfile(gridfile):
            raise ValueError('File "%s" does not exist!' % gridfile)

        self._ppc, self._entities = model.load_case(gridfile,
                                                    self._magic_factor)

        entities = []
        for eid, attrs in sorted(self._entities.items()):
            # We'll only add relations from branches to nodes (and not from
            # nodes to branches) because this is sufficient for mosaik to
            # build the entity graph.
            relations = []
            if attrs['etype'] in ['Transformer', 'Branch']:
                relations = attrs['related']

            entities.append({
                'eid': eid,
                'type': attrs['etype'],
                'rel': relations,
            })

        return entities

    def step(self, time, inputs):
        model.reset_inputs(self._ppc)
        for eid, attrs in inputs.items():
            idx = self._entities[eid]['idx']
            etype = self._entities[eid]['etype']
            for name, values in attrs.items():
                # values is a list of p/q values, sum them up to a single value
                attrs[name] = sum(float(v) for v in values)
                if name == 'P':
                    attrs[name] *= self.pos_loads
                attrs[name] /= self._magic_factor

            model.set_inputs(self._ppc, etype, idx, attrs)

        res = model.perform_powerflow(self._ppc)
        self._cache = model.update_cache(res, self._entities)

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                val = self._cache[eid][attr]
                if attr == 'P':
                    val *= self.pos_loads
                data.setdefault(eid, {})[attr] = val

        return data


def main():
    mosaik_api.start_simulation(PyPower(), 'The mosaik-PYPOWER adapter')
