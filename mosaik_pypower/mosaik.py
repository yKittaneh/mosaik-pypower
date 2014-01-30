"""
This module implements the mosaik API for `PYPOWER
<https://pypi.python.org/pypi/PYPOWER/4.0.1>`_.

"""
from __future__ import division
import logging
import os
import mosaik_api

from mosaik_pypower import model


logger = logging.getLogger('cerberus.mosaik')


class PyPower(mosaik_api.Simulation):
    """

    """
    sim_name = 'PyPower'
    model_name = 'PowerGrid'

    def __init__(self):
        self._step_size = None

        # The incoming feed-in/load may be +/- or -/+. If this is set to true
        # incoming loads are positive and we have to swap it to -.
        # Internally, PYPOWER uses + for loads and - for feed-in.
        # Note, that we only change the input (set_data()).
        self._feedin_positive = True

        # The line params that we read are for 1 of 3 wires within a cable,
        # but the loads and feed-in is meant for the complete cable, so we
        # have to divide all loads and feed-in by 3.
        self._magic_factor = 3  # Divide all incoming loads by this factor

        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)
        self._ppc = None  # The pypower case
        self._data_cache = {}  # Cache for load flow outputs

    def init(self, step_size, sim_params, model_config):
        self._step_size = step_size

        if len(model_config) != 1:
            raise ValueError('Need exactly one model config, got %s' %
                             len(model_config))
        cfg_id, model_name, num_instances, params = model_config[0]

        if model_name != self.model_name:
            raise ValueError('Got unkown model name: %s' % model_name)
        if num_instances != 1:
            raise ValueError('Only one instance of PowerGrid allowed.')
        if not os.path.isfile(params['file']):
            raise ValueError('File "%s" does not exist!' % params['file'])

        self._ppc, self._entities = model.load_case(params['file'])

        entities = {}
        for eid, attrs in self._entities.items():
            entities[eid] = attrs['etype']
            if attrs['etype'] in ['Transformer', 'Branch']:
                for related in attrs['related']:
                    self._relations.append((eid, related))

        return {cfg_id: [entities]}

    def get_relations(self):
        return self._relations

    def get_static_data(self):
        data = {eid: attrs['static']
                for eid, attrs in self._entities.items()}
        return data

    def set_data(self, data):
        model.reset_inputs(self._ppc)
        for eid, attrs in data.items():
            idx = self._entities[eid]['idx']
            etype = self._entities[eid]['etype']
            for name, values in attrs.items():
                # values is a list of p/q values, sum them up to a single value
                attrs[name] = sum(float(v) for v in values)
                attrs[name] /= self._magic_factor
                if self._feedin_positive:
                    attrs[name] *= -1

            model.set_inputs(self._ppc, etype, idx, attrs)

    def step(self, time):
        res = model.perform_powerflow(self._ppc)
        self._cache = model.update_cache(res, self._entities)

    def get_data(self, model_name, etype, attributes):
        if model_name != self.model_name:
            raise ValueError('Invalid model "%s"' % model_name)

        if not etype in self._cache:
            # No entities of type "etype" available
            return {}

        if not attributes:
            # Return all attributes
            return self._cache[etype]
        else:
            # Filter data dict of each entity by the *attributes* list.
            return {eid: {attr: data[attr] for attr in attributes}
                    for eid, data in self._cache[etype].items()}


def main():
    mosaik_api.start_simulation(PyPower(), 'PyPower')


if __name__ == '__main__':
    main()
