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
    license='',
    install_requires=[
        'PYPOWER>=4',
        'mosaik-api>=2.0a1',
        'numpy>=1.8',
        'scipy>=0.13',
    ],
    packages=find_packages(),
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'mosaik-pypower = mosaik_pypower.mosaik:main',
        ],
    },
    classifiers=[
        'Private :: Do Not Upload',  # Prevents accidental upload to PyPI
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: Other/Proprietary License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Topic :: Scientific/Engineering',
    ],
)
