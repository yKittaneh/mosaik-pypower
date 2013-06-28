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
GRID_FILE = os.path.join(os.path.dirname(__file__), 'data', 'test_case_b.json')


def test_mosaik_nozmq():
    sim = mosaik.PyPower()
    init = sim.init(60, {}, [(0,  # cfg_id
                       'PowerGrid',  # model name
                       1,  # Num instances
                       {'file': GRID_FILE},
                       )]
                    )
    
    assert init == {0: 
        [{'Bus2': 'PQBus', 
          'Bus3': 'PQBus', 
          'Bus0': 'PQBus', 
          'Bus1': 'PQBus', 
          'Grid': 'Grid', 
          'Trafo1': 'Transformer', 
          'B_0': 'Branch', 
          'B_1': 'Branch', 
          'B_2': 'Branch', 
          'B_3': 'Branch'}]}

    assert sim.get_relations() == [('B_1',  'Bus0'), 
                                   ('B_1',  'Bus2'), 
                                   ('B_0', 'Bus0'), 
                                   ('B_0', 'Bus1'), 
                                   ('Trafo1', 'Grid'), 
                                   ('Trafo1', 'Bus0'), 
                                   ('B_2', 'Bus1'), 
                                   ('B_2', 'Bus3'),
                                   ('B_3', 'Bus2'), 
                                   ('B_3', 'Bus3')]

    assert sim.get_static_data() == {'Bus2': {'vl': 20.0}, 
                                     'Bus3': {'vl': 20.0}, 
                                     'Bus0': {'vl': 20.0}, 
                                     'Bus1': {'vl': 20.0}, 
                                     'Grid': {'vl': 110.0}, 
                                     'Trafo1': {'s_max': 40.0}, 
                                     'B_0': {'s_max': 19.98, 'length': 5.0}, 
                                     'B_1': {'s_max': 19.98, 'length': 3.0}, 
                                     'B_2': {'s_max': 19.98, 'length': 2.0}, 
                                     'B_3': {'s_max': 19.98, 'length': 0.3}}

    #Values from https://bitbucket.org/ssc/cim2busbranch/src/contrib/pp_test.py
    MW = 1000*1000 
    data = {'Bus1': {'p': [0.8*MW, 0.2*MW], 'q': [0.2*MW, 0.0*MW]},
            'Bus2': {'p': [1.98*MW], 'q': [0.28*MW]},
            'Bus3': {'p': [0.85*MW], 'q': [0.53*MW]},
            }
    sim.set_data(data)

    sim.step()
    
    data = sim.get_data('PowerGrid', 'PQBus', None)
    print (data)
    
    data = sim.get_data('PowerGrid', 'Grid', None)
    print (data)
    
    data = sim.get_data('PowerGrid', 'Branch', None)
    print (data)
    
    data = sim.get_data('PowerGrid', 'Transformer', None)
    print (data)
    #todo assert data ==

if __name__ == '__main__':
    test_mosaik_nozmq()