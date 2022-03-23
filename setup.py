from setuptools import setup, find_packages


setup(
    name='mosaik-pypower',
    version='0.8.1',
    author='Stefan Scherfke',
    author_email='mosaik@offis.de',
    description='An adapter to use PYPOWER with mosaik.',
    long_description=(open('README.rst').read() + '\n\n' +
                      open('CHANGES.txt').read() + '\n\n' +
                      open('AUTHORS.txt').read()),
    url='https://gitlab.com/mosaik/components/energy/mosaik-pypower',
    install_requires=[
        'PYPOWER>=4.1',
        'mosaik-api>=3.0',
        'numpy>=1.6',
        'scipy>=0.9',
        'xlrd>=0.9.2,<2',
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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Scientific/Engineering',
    ],
)
