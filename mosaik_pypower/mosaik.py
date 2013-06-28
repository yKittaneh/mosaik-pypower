"""
This module implements the mosaik API for Cerberus.

"""
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
        self._count = 0  # Number of analyses performed
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

        try:
            self._ppc, self._entities = model.load_case(params['file'])
        except (ValueError, KeyError) as err:
            raise RuntimeError(*err.args)

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
        for eid, attrs in data.items():
            idx = self._entities[eid]['idx']
            etype = self._entities[eid]['etype']
            aggregated = {}
            for name, values in attrs.items():
                aggregated[name] = sum([float(v) for v in values])
            model.set_inputs(self._ppc, etype, idx, aggregated)        

    def step(self):
        self._count += 1
        res = model.perform_powerflow(self._ppc)
        self._cache = model.update_cache(res[0], self._entities)
        return self._count * self._step_size

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
                    for eid, data in self._data_cache[etype].items()}

def main():
    mosaik_api.start_simulation(PyPower(), 'PyPower')


if __name__ == '__main__':
    main()
