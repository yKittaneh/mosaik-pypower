from setuptools import setup, find_packages

import mosaik_pypower


setup(
    name='mosaik-pypower',
    version=mosaik_pypower.__version__,
    author='Stefan Scherfke',
    author_email='stefan.scherfke@offis.de',
    description='An adapter to use PYPOWER with mosaik.',
    long_description=open('README.txt').read(),
    url='',
    download_url='',
    license='',
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'mosaik-pypower = mosaik_pypower.mosaik:main',
        ],
    },
    install_requires=[
        'PYPOWER',
        'mosaik-api',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: Other/Proprietary License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Scientific/Engineering',
    ],
)
