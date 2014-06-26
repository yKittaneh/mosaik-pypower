from setuptools import setup, find_packages

import mosaik_pypower


setup(
    name='mosaik-pypower',
    version=mosaik_pypower.__version__,
    author='Stefan Scherfke',
    author_email='stefan.scherfke@offis.de',
    description='An adapter to use PYPOWER with mosaik.',
    long_description=(open('README.txt').read() + '\n\n' +
                      open('CHANGES.txt').read() + '\n\n' +
                      open('AUTHORS.txt').read()),
    url='https://bitbucket.org/mosaik/mosaik-pypower',
    install_requires=[
        'PYPOWER>=4.1',
        'mosaik-api>=2.0a3',
        'numpy>=1.6',
        'scipy>=0.9',
        'xlrd>=0.9.2',
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'mosaik-pypower = mosaik_pypower.mosaik:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Topic :: Scientific/Engineering',
    ],
)
