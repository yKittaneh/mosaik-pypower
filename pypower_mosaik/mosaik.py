"""
This module implements the mosaik API for Cerberus.

"""
import logging

import mosaik_api


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
        return {}

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
