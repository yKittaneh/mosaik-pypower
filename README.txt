mosaik-pypower
==============

This package contains the Adapter to connect *PYPOWER* to *mosaik*.


Installation
------------

*mosaik-pypower* currently requires an experimental branch of PYPOWER with
Python 3 support which you have to install first::

   $ pip install git+https://github.com/sscherfke/PYPOWER.git@py2and3#egg=PYPOWER
   $ pip install mosaik-pypower

You can run the tests with::

    $ hg clone https://bitbucket.org/mosaik/mosaik-pypower
    $ cd mosaik-pypower
    $ pip install -r requirements.txt
    $ py.test


Input File Format
-----------------

The adapter uses a simple JSON based format for input files::

    {
        "base_mva": <global_base_mva>,
        "bus": [
            ["<bus_id>", "<bus_type>", <base_kv>],
        ...
        ],
        "trafo": [
            ["<trafo_id>", "<from_bus_id>", "<to_bus_id>", <Sr_MVA>, <v1_%>,
            <P1_MW>, <Imax_p_A>, <Imax_s_A>],
        ...
        ],
        "branch": [
            ["<branch_id>", "<from_bus_id>", "<to_bus_id>", <length_km>,
             <R'_ohm/km>, <X'_ohm/km>, <C'_nF/km>, <I_max_A>],
            ...
        ]
    }


where:

- *<bus_id>*, *<trafo_id>*, *<branch_id>* need to be unique names
- *<bus_type>* may be *"PQ"*, *"PV"* or *"REF"*
- There may only be one *REF* bus and it must be the first in the list

.. note:: Generators and PV buses are not yet supported.
