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
    'type': 'time-based',
    'models': {
        'Grid': {
            'public': True,
            'params': [ # todo: still need these params?
                'gridfile',  # Name of the file containing the grid topology.
                'sheetnames',  # Mapping of Excel sheet names, optional.
            ],
            'attrs': [],
        },
        'RefBus': {
            'public': False,
            'params': [],
            'attrs': [
                'P',   # Active power [W]
                'Q',   # Reactive power [VAr]
                'Vl',  # Nominal bus voltage [V]
                'Vm',  # Voltage magnitude [V]
                'Va',  # Voltage angle [deg]
            ],
        },
        'PQBus': {
            'public': False,
            'params': [],
            'attrs': [
                'P',  # Active power [W]
                'Q',  # Reactive power [VAr]
                'Vl',  # Nominal bus voltage [V]
                'Vm',  # Voltage magnitude [V]
                'Va',  # Voltage angle [deg]
                'net_metering_power',
                'container_need',
                'battery_action',
            ],
        },
        'Transformer': {
            'public': False,
            'params': [],
            'attrs': [
                'P_from',  # Active power at "from" side [W]
                'Q_from',  # Reactive power at "from" side [VAr]
                'P_to',  # Active power at "to" side [W]
                'Q_to',  # Reactive power at "to" side [VAr]
                'S_r',  # Rated apparent power [VA]
                'I_max_p',  # Maximum current on primary side [A]
                'I_max_s',  # Maximum current on secondary side [A]
                'P_loss',  # Active power loss [W]
                'U_p',  # Nominal primary voltage [V]
                'U_s',  # Nominal secondary voltage [V]
                'taps',  # Dict. of possible tap turns and their values
                'tap_turn',  # Currently active tap turn
            ],
        },
        'Branch': {
            'public': False,
            'params': [],
            'attrs': [
                'P_from',  # Active power at "from" side [W]
                'Q_from',  # Reactive power at "from" side [VAr]
                'P_to',  # Active power at "to" side [W]
                'Q_to',  # Reactive power at "to" side [VAr]
                'I_real',  # Branch current (real part) [A]
                'I_imag',  # Branch current (imaginary part) [A]
                'S_max',  # Maximum apparent power [VA]
                'I_max',  # Maximum current [A]
                'length',  # Line length [km]
                'R_per_km',  # Resistance per unit length [Ω/km]
                'X_per_km',  # Reactance per unit length [Ω/km]
                'C_per_km',  # Capactity per unit length [F/km]
                'online',  # Boolean flag (True|False)
            ],
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

        self._entities = {}
        self._relations = []  # List of pair-wise related entities (IDs)
        self._ppcs = []  # The pypower cases
        self._cache = {}  # Cache for load flow outputs

        self.container_need = 0
        self.pv_power = 0
        self.battery_power = 0
        self.battery_max_capacity = 50000
        self.battery_action = None
        self.net_metering_power = 0

    def init(self, sid, time_resolution, step_size, pos_loads=True,
             converge_exception=False):
        logger.debug('Power flow will be computed every %d seconds.' %
                     step_size)
        signs = ('positive', 'negative')
        logger.debug('Loads will be %s numbers, feed-in %s numbers.' %
                     signs if pos_loads else tuple(reversed(signs)))

        self.step_size = step_size
        self.pos_loads = 1 if pos_loads else -1
        self._converge_exception = converge_exception

        return self.meta

    def create(self, num, modelname, gridfile, sheetnames=None):
        if modelname != 'Grid':
            raise ValueError('Unknown model: "%s"' % modelname)
        if not os.path.isfile(gridfile):
            raise ValueError('File "%s" does not exist!' % gridfile)

        if not sheetnames:
            sheetnames = {}

        grids = []
        for i in range(num):
            grid_idx = len(self._ppcs)
            ppc, entities = model.load_case(gridfile, grid_idx, sheetnames)
            self._ppcs.append(ppc)

            children = []
            for eid, attrs in sorted(entities.items()):
                assert eid not in self._entities
                self._entities[eid] = attrs

                # We'll only add relations from branches to nodes (and not from
                # nodes to branches) because this is sufficient for mosaik to
                # build the entity graph.
                relations = []
                if attrs['etype'] in ['Transformer', 'Branch']:
                    relations = attrs['related']

                children.append({
                    'eid': eid,
                    'type': attrs['etype'],
                    'rel': relations,
                })

            grids.append({
                'eid': model.make_eid('grid', grid_idx),
                'type': 'Grid',
                'rel': [],
                'children': children,
            })

        return grids

    def step(self, time, inputs, max_advance):
        for ppc in self._ppcs:
            model.reset_inputs(ppc)

        for eid, attrs in inputs.items():
            ppc = model.case_for_eid(eid, self._ppcs)
            idx = self._entities[eid]['idx']
            etype = self._entities[eid]['etype']
            static = self._entities[eid]['static']
            for name, values in attrs.items():
                # values is a dict of p/q values, sum them up
                attrs[name] = sum(float(v) for v in values.values())
                if name == 'P' and eid == '0-node_a1':
                    attrs[name] *= self.pos_loads
                    if values['CSV-0.PV_0'] is None or values['BatterySimulator-0.batteryNode'] is None:
                        raise RuntimeError('[P] input value expected from battery and PV nodes.')

                    self.pv_power = abs(values['CSV-0.PV_0'])
                    self.battery_power = values['BatterySimulator-0.batteryNode']

                elif name == 'container_need' and eid == '0-node_a1':
                    if values['ComputeNodeSimulator-0.computeNode'] is None:
                        raise RuntimeError('[container_need] input value expected from compute node.')
                    self.container_need = values['ComputeNodeSimulator-0.computeNode']

                else:
                    print('Unexpected attribute requested {}'.format(attrs.items()))
                    raise RuntimeError('Unexpected attribute requested {}'.format(attrs.items()))

            model.set_inputs(ppc, etype, idx, attrs, static)

        self.handle_power_input()

        res = []
        for ppc in self._ppcs:
            res.append(model.perform_powerflow(ppc))
            if self._converge_exception and not res[-1]['success']:
                raise RuntimeError(
                    'Loadflow did not converge for eid "%s" at time %i!' %
                    (eid, time))
        self._cache = model.get_cache_entries(res, self._entities)

        return time + self.step_size

    def get_data(self, outputs):
        data = {}
        for eid, attrs in outputs.items():
            for attr in attrs:
                if attr == 'battery_action':
                    val = self.battery_action
                    if val is not None:
                        print('self.battery_action = {}'.format(self.battery_action))
                    self.battery_action = None
                elif attr == 'net_metering_power':
                    val = self.net_metering_power
                    if val > 0:
                        print('self.net_metering_power = {}'.format(self.net_metering_power))
                    self.net_metering_power = 0
                else:
                    try:
                        val = self._cache[eid][attr]
                        if attr == 'P':
                            val *= self.pos_loads
                    except KeyError:
                        val = self._entities[eid]['static'][attr]
                data.setdefault(eid, {})[attr] = val

        return data

    def handle_power_input(self):

        # 1- check if there is pv, use all pv or as much needed, if we have extra then charge battery, if we still have extra then net-metering
        # 2- if pv is not enough then check battery, use all or as much needed
        # 3- if battery and pv are not enough then take the rest from grid
        #
        # if self.pv_power + self.battery_power >= self.container_need:
        #   then take all pv
        #   if we have extra pv:
        #       then charge battery with rest
        #   if pv is enough exactly to cover container need: then do nothing
        #   if pv is not enough:
        #       then if battery is enough to cover for ....
        #

        if self.pv_power == 0 and self.battery_power == 0:
            # no pv and no battery power, need to take all from grid
            #print('no pv and no battery power, need to take all from grid')
            self.pv_power = 0
            # todo: need to do something here to take from the grid?

        else:
            if self.pv_power > 0:
                #print('we have pv power')
                if self.pv_power >= self.container_need:
                    #print('pv power is larger than or equal to container node need')
                    pv_extra_power = self.pv_power - self.container_need
                    # todo: give power to container, do something? I guess do nothing
                    if pv_extra_power == 0:
                        #print('pv power and container need are equal, no pv extra power, do nothing')
                        self.battery_action = 'noAction'

                    if pv_extra_power > 0:
                       # print('still have extra pv power, checking battery')
                        battery_full_charge_need = self.battery_max_capacity - self.battery_power
                        if battery_full_charge_need > 0:
                            #print('battery not full [current charge = {}], going to charge it'.format(self.battery_power))
                            if battery_full_charge_need >= pv_extra_power:
                                #print('using all pv extra power [{}] to charge battery'.format(pv_extra_power))
                                self.battery_action = 'charge:' + str(pv_extra_power)
                            else:
                                #print('we have more pv extra power than the battery needs, using some of the pv extra power [{}] to charge battery and the rest will be net-metered'.format(battery_full_charge_need))
                                self.battery_action = 'charge:' + str(battery_full_charge_need)
                                pv_extra_power = pv_extra_power - battery_full_charge_need
                                #print('using rest of pv extra power [{}] for net-metering'.format(pv_extra_power))
                                self.net_metering_power += pv_extra_power
                else:  # pv_extra_power < self.container_need
                    #rint('pv extra power less than container need, we need to use battery to cover, checking battery')
                    if self.battery_power > 0:
                        #print('battery has [{}] power, will use some or all for the container'.format(self.battery_power))
                        battery_extra_power = self.battery_power - self.container_need
                        if battery_extra_power >= 0:
                            #print('battery has sufficient power to cover container need [{}]'.format(self.container_need))
                            self.battery_action = 'discharge:' + str(self.container_need)
                        else:
                            #print('battery power does not cover container need [{}], will take it all and cover the rest from the grid'.format(self.container_need))
                            self.battery_action = 'discharge:' + str(self.battery_power)
                            # todo: take power from the grid (equal to abs(battery_extra_power)), do something? do nothing
                    #else: # self.battery_power = 0
                        #print('battery is empty, will use grid power')
                        # todo: take power from the grid (equal to self.container_need), do something? same as the todo above, maybe extract function?

            else:  # no pv_power # todo: this block is the same as the one above, extract method
                #print('no pv_power, will check battery')
                if self.battery_power > 0:
                    #print('battery has [{}] power, will use some or all for the container'.format(self.battery_power))
                    battery_extra_power = self.battery_power - self.container_need
                    if battery_extra_power >= 0:
                        #print('battery has sufficient power to cover container need [{}]'.format(self.container_need))
                        self.battery_action = 'discharge:' + str(self.container_need)
                    else:
                        #print('battery power does not cover container need [{}], will take it all and cover the rest from the grid'.format(self.container_need))
                        self.battery_action = 'discharge:' + str(self.battery_power)
                        # todo: take power from the grid (equal to abs(battery_extra_power)), do something?
                #else:
                    #print('battery is empty, will use grid power')
                    # todo: take power from the grid (equal to self.container_need), do something? same as the todo above, maybe extract function?


def get_control_node(entities):
    for item in entities.items():
        if item[0] == '0-node_a1':
            return item
    else:
        raise ValueError('Grid node 0-node_a1 not found')


def main():
    mosaik_api.start_simulation(PyPower(), 'The mosaik-PYPOWER adapter')
