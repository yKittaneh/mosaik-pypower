# -*- coding: utf-8 -*-
import os.path

import numpy as np
import pytest

from mosaik_pypower import mosaik

#         Grid                      
#           +                        
# Transformer20kV(REF)              
#           +              B_0            
#          Bus0–––––––----------––– Bus1
#           |                        |
#           |B_1                     |B_2
#           |                        |
#           |              B_3       |
#          Bus2 ––––––––––––––––––– Bus3
#GRID_FILE = os.path.join(os.path.dirname(__file__), 'data', 'test_case_b.json')
#
#
#def test_mosaik_nozmq():
#    sim = mosaik.PyPower()
#    init = sim.init(60, {}, [(0,  # cfg_id
#                       'PowerGrid',  # model name
#                       1,  # Num instances
#                       {'file': GRID_FILE},
#                       )]
#                    )
#    
#    assert init == {0: 
#        [{'Bus2': 'PQBus', 
#          'Bus3': 'PQBus', 
#          'Bus0': 'PQBus', 
#          'Bus1': 'PQBus', 
#          'Grid': 'Grid', 
#          'Trafo1': 'Transformer', 
#          'B_0': 'Branch', 
#          'B_1': 'Branch', 
#          'B_2': 'Branch', 
#          'B_3': 'Branch'}]}
#
#    assert sim.get_relations() == [('B_1',  'Bus0'), 
#                                   ('B_1',  'Bus2'), 
#                                   ('B_0', 'Bus0'), 
#                                   ('B_0', 'Bus1'), 
#                                   ('Trafo1', 'Grid'), 
#                                   ('Trafo1', 'Bus0'), 
#                                   ('B_2', 'Bus1'), 
#                                   ('B_2', 'Bus3'),
#                                   ('B_3', 'Bus2'), 
#                                   ('B_3', 'Bus3')]
#
#    assert sim.get_static_data() == {'Bus2': {'vl': 20.0}, 
#                                     'Bus3': {'vl': 20.0}, 
#                                     'Bus0': {'vl': 20.0}, 
#                                     'Bus1': {'vl': 20.0}, 
#                                     'Grid': {'vl': 110.0}, 
#                                     'Trafo1': {'s_max': 40.0}, 
#                                     'B_0': {'s_max': 19.98, 'length': 5.0}, 
#                                     'B_1': {'s_max': 19.98, 'length': 3.0}, 
#                                     'B_2': {'s_max': 19.98, 'length': 2.0}, 
#                                     'B_3': {'s_max': 19.98, 'length': 0.3}}
#
#    #Values from https://bitbucket.org/ssc/cim2busbranch/src/contrib/pp_test.py
#    MW = 1000*1000 
#    data = {'Bus1': {'p': [0.8, 0.2], 'q': [0.2, 0.0]},
#            'Bus2': {'p': [1.98], 'q': [0.28]},
#            'Bus3': {'p': [0.85], 'q': [0.53]},
#            }
#    sim.set_data(data)
#
#    sim.step()
#    
#    data = sim.get_data('PowerGrid', 'PQBus', None)
#    print (data)
#    
#    data = sim.get_data('PowerGrid', 'Grid', None)
#    print (data)
#    
#    data = sim.get_data('PowerGrid', 'Branch', None)
#    print (data)
#    
#    data = sim.get_data('PowerGrid', 'Transformer', None)
#    print (data)
#    #todo assert data ==


GRID_FILE = os.path.join(os.path.dirname(__file__), 'data', 'MS_data_CIGRE_Szenarien.json')

from xlsxwriter.workbook import Workbook

import math
def get_pq(P, cosphi):
    S = [p / c for p, c in zip(P, cosphi)]
    Q = []
    for s, p in zip(S, P):
        Q.append(math.sqrt((s ** 2) - (p ** 2)))
        
    return {'p':[p*1000000 for p in P], 'q':[q*1000000 for q in Q]}

def test_mosaik_nozmq():
    sim = mosaik.PyPower()
    init = sim.init(60, {}, [(0,  # cfg_id
                       'PowerGrid',  # model name
                       1,  # Num instances
                       {'file': GRID_FILE},
                       )]
                    )
    
    assert init == {0: 
        [{'MS_K2': 'PQBus', 
          'MS_K3': 'PQBus', 
          'MS_K4': 'PQBus', 
          'MS_K5': 'PQBus', 
          'MS_K6': 'PQBus',
          'MS_K7': 'PQBus',
          'MS_K8': 'PQBus',
          'MS_K9': 'PQBus',
          'MS_K10': 'PQBus',
          'MS_K11': 'PQBus',
          'MS_K12': 'PQBus',
          'Grid': 'Grid', 
          'Trafo_MS_T1': 'Transformer', 
          'B_MS_L1': 'Branch', 
          'B_MS_L2': 'Branch',
          'B_MS_L3': 'Branch',
          'B_MS_L4': 'Branch',
          'B_MS_L5': 'Branch',
          'B_MS_L7': 'Branch',
          'B_MS_L8': 'Branch',
          'B_MS_L9': 'Branch',
          'B_MS_L10': 'Branch',
          'B_MS_L11': 'Branch',
#          'B_MS_L13': 'Branch',
#          'B_MS_L14': 'Branch',
          }]}

    expected =  [('B_MS_L1', 'MS_K2'),
               ('B_MS_L1', 'MS_K3'),
               ('B_MS_L2', 'MS_K3'),
               ('B_MS_L2', 'MS_K4'),
               ('B_MS_L3', 'MS_K4'),
               ('B_MS_L3', 'MS_K5'),
               ('B_MS_L4', 'MS_K5'),
               ('B_MS_L4', 'MS_K6'),
               ('B_MS_L5', 'MS_K6'),
               ('B_MS_L5', 'MS_K7'),
               ('B_MS_L7', 'MS_K8'),
               ('B_MS_L7', 'MS_K9'),
               ('B_MS_L8', 'MS_K9'),
               ('B_MS_L8', 'MS_K4'),
               ('B_MS_L9', 'MS_K9'),
               ('B_MS_L9', 'MS_K10'),
               ('B_MS_L10', 'MS_K10'),
               ('B_MS_L10', 'MS_K11'),
               ('B_MS_L11', 'MS_K11'),
               ('B_MS_L11', 'MS_K12'),
#               ('B_MS_L13', 'MS_K2'),
#               ('B_MS_L13', 'MS_K3'),
#               ('B_MS_L14', 'MS_K3'),
#               ('B_MS_L14', 'MS_K4'),
               ('Trafo_MS_T1', 'Grid'),
               ('Trafo_MS_T1', 'MS_K2'),
               ]
    
    got = sim.get_relations()
    assert len(expected) == len(got)
    for tuple in got:
        assert tuple in expected

    static = sim.get_static_data()
    #assert static['B_MS_L13'] == {'s_max':7.24, 'length':8.26}

    #Values from E:\_Public\Gruppe SO\Themenfelder\Modellierung und Simulation\Netzberechnung\Workshop Evaluation von Netzberechnungen\pp_mv_case.py
    #        Bus('MS_K2',  base_kv, 5.0, .95),
    #        Bus('MS_K3',  base_kv),
    #        Bus('MS_K4',  base_kv, [1.5, .35],  [.95, 1.0]),
    #        Bus('MS_K5',  base_kv, -8.0, 0.95),
    #        Bus('MS_K6',  base_kv, 1.2, 1.0),
    #        Bus('MS_K7',  base_kv, .9, .95),
    #        Bus('MS_K8',  base_kv, -.46, .95),
    #        Bus('MS_K9',  base_kv, [3.5, -.75], [1.0, .95]),
    #        Bus('MS_K10', base_kv),
    #        Bus('MS_K11', base_kv, 2.0, .95),
    #        Bus('MS_K12', base_kv, 1.6, .95),
    data = {'MS_K2': get_pq([5.0],  [.95]),
            'MS_K4': get_pq([1.5, 0.35], [.95, 1.0]),
            'MS_K5': get_pq([-8.0], [.95]),
            'MS_K6': get_pq([1.2], [1.0]),
            'MS_K7': get_pq([.9], [.95]),
            'MS_K8': get_pq([-.46], [.95]),
            'MS_K9': get_pq([3.5, -.75], [1.0, .95]),
            'MS_K11': get_pq([2.0], [.95]),
            'MS_K12': get_pq([1.6], [.95]),
            }
    sim.set_data(data)

    #Resulting case:
    #(u'Grid', '0.000, 0.000, 0.000, 0.000, 1.000, 1.000, 0.000, 110.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K2', '5.000, 1.643, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K3', '0.000, 0.000, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K4', '1.850, 0.493, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K5', '-8.000, 2.629,0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K6', '1.200, 0.000, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K7', '0.900, 0.296, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K8', '-0.460, 0.151,0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K9', '2.750, 0.247, 0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K10', '0.000, 0.000,0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, '
    #(u'MS_K11', '2.000, 0.657,0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    #(u'MS_K12', '1.600, 0.526,0.000, 0.000, 1.000, 1.000, 0.000, 20.000, 1.000, 1.100, 0.900, ')
    
    #('TRAFO', '0.001, 0.032, 0.000, 999.000, 999.000, 999.000, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L1', '0.033, 0.025, 0.026, 7.240, 7.240, 7.240, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L2', '0.110, 0.091, 0.001, 5.500, 5.500, 5.500, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L3', '0.015, 0.013, 0.000, 5.500, 5.500, 5.500, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L4', '0.027, 0.023, 0.000, 5.500, 5.500, 5.500, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L5', '0.053, 0.044, 0.001, 5.500, 5.500, 5.500, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L7', '0.016, 0.008, 0.007, 5.740, 5.740, 5.740, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L8', '0.005, 0.003, 0.002, 5.740, 5.740, 5.740, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L9', '0.003, 0.002, 0.001, 5.740, 5.740, 5.740, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L10', '0.007, 0.003, 0.003, 5.740, 5.740, 5.740, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    #(u'B_MS_L11', '0.016, 0.008, 0.007, 5.740, 5.740, 5.740, 0.000, 0.000, 1.000, -360.000, 360.000, ')
    
    sim.step()
    
    
    filename = 'msgrid.xlsx'
    wb = Workbook(filename)
    bold = wb.add_format({'bold': 1})
    two_dec = wb.add_format({'num_format': '0.00'})
    three_dec = wb.add_format({'num_format': '0.000'})
    
    # Write bus data
    ws_bus = wb.add_worksheet('Buses')
    ## Headings
    headings = [
        'Name',
        'V mag. [kV]',
        u'V ang. [°]',
        'P [MW]',
        'Q [MVar]',
    ]
    for i, heading in enumerate(headings):
        ws_bus.write(0, i, heading, bold)

    ## Write bus data
    busdata = sim.get_data('PowerGrid', 'PQBus', None)
    attrs = [
        ('name', None, None),
        ('vm', three_dec, 1000),
        ('va', three_dec, 1),
        ('p_out', two_dec, 1000000),
        ('q_out', two_dec, 1000000),
    ]
    
    griddata = sim.get_data('PowerGrid', 'Grid', None)
    
    ws_bus.write(1, 0, 'Grid', None)
    ws_bus.write(1, 1, '-', None)
    ws_bus.write(1, 2, '-', None)
    ws_bus.write(1, 3, griddata['Grid']['p']/1000000, three_dec)
    ws_bus.write(1, 4, griddata['Grid']['q']/1000000, three_dec)
    
    for i, (bus, data) in enumerate(sorted(busdata.items())):
        data['name'] = bus
        for j, (attr, fmt, scale) in enumerate(attrs):
            val = data[attr]
            if scale:
                val = val /scale
            ws_bus.write(i + 2, j, val, fmt)
    
    # Write branch data
    ws_branch = wb.add_worksheet('Branches')
    ## Headings
    headings = [
        'Name',
        'P from [MW]',
        'Q from [MVar]',
        'P to [MW]',
        'Q to [MVar]',
    ]
    for i, heading in enumerate(headings):
        ws_branch.write(0, i, heading, bold)

    ## Write branch data
    attrs = [
        ('name', None, None),
        ('p_from', two_dec, 1000000),
        ('q_from', two_dec, 1000000),
        ('p_to', two_dec, 1000000),
        ('q_to', two_dec, 1000000),
    ]
    branchdata = sim.get_data('PowerGrid', 'Branch', None)
    transformerdata = sim.get_data('PowerGrid', 'Transformer', None)
    branchdata.update(transformerdata)
    for i, (branch, data) in enumerate(sorted(branchdata.items())):
        data['name'] = branch
        for j, (attr, fmt, scale) in enumerate(attrs):
            val = data[attr]
            if scale:
                val = val /scale
            ws_branch.write(i + 1, j, val, fmt)

    wb.close()
    
   


if __name__ == '__main__':
    test_mosaik_nozmq()