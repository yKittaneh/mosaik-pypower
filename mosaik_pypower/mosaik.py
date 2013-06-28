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
        self._count = None  # Number of analyses performed
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
                self._relations.append((attrs['from_eid'], eid))  # TODO
                self._relations.append((attrs['to_eid'], eid))  # TODO

        return {cfg_id: [entities]}

    def get_relations(self):
        return self._relations

    def get_static_data(self):
        return {}

    def set_data(self, data):
        idx = self._entitis[data['eid']]['idx']
        etype = self._entites[data['eid']]['etype']
        # models.set_data(self._ppc, data_item)
        from pypower import idx_bus, idx_branch
        ppc[etype][idx][idx_branc.PQ] = data['pq']

    def step(self):
        self._count += 1
        res = models.perform_powerflow(self._ppc)
        self._chache = model.update_cache(res)
        return self._count * self._step_size

    def get_data(self, model_name, etype, attributes):
        return {}


def main():
    mosaik_api.start_simulation(PyPower(), 'PyPower')


if __name__ == '__main__':
    main()
