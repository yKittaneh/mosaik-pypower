"""
This module implements the mosaik API for Cerberus.

"""
import logging

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
        self._count = None  # Number of analyses performed
        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)
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
            ppc, eid_map = model.load_case(params['file'])

        except (ValueError, KeyError):
            raise RuntimeError('Error during initialization: %s' % error) \
                from None
        self._entities.update(nodes)
        self._entities.update(models)

        entities = {}
        for node, attrs in nodes.items():
            entities[node] = 'Node'
        for mod, attrs in models.items():
            entities[mod] = attrs['type']
            for pin, connected in attrs['pins']:
                self._relations.append((connected, mod))

        return {cfg_id: [entities]}

    def get_relations(self):
        return self._relations

    def get_static_data(self):
        return {}

    def set_data(self, data):
        pass

    def step(self):
        self._count += 1
        return self._count * self._step_size

    def get_data(self, model_name, etype, attributes):
        return {}


def main():
    mosaik_api.start_simulation(PyPower(), 'PyPower')


if __name__ == '__main__':
    main()
