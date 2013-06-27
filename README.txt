pypower-mosaik
==============

This package contains the Adapter to connect *PYPOWER* to *mosaik*.


Installation
------------

Just execute ``pip install .``. If you run into any problems, try to install
the tested dependency configuration via ``pip intall -r requirements.txt``.

If you also want to run the tests, run ``pip install -r
requirements-dev.txt`` and ``py.test`` to execute the test suite.


Input File Format
-----------------

The adapter uses a simple JSON based format for input files::

    {
        "base_mva": <global_base_mva>,
        "bus": [
            ["<bus_id>", "<bus_type>", base_kv],
        ...
        ],
        "gen": [
            ["<gen_id>", "<connect_to_bus_id>"],
            ...
        ],
        "trafo": {
            ["<trafo_id>", ???],
            ...
        },
        "branch": {
            ["<branch_id>", "<from_bus_id>", "<to_bus_id>", <length_km>,
             <R'_ohm/km>, <X'_ohm/km>, <C'_nF/km>, <S_max_MVA>],
            ...
        }
    }


where:

- *<bus_id>*, *<ben_id>*, *<trafo_id>*, *<branch_id>* need to be unique names
- *<bus_type>* may be *"PQ"*, *"PV"* or *"REF"*
- There may only be one *REF* bus and it must be the first in the list
