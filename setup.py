from setuptools import setup, find_packages

long_description = """
moo-sim-interface
====

moo-sim-interface is a Python package for the simulation of Modelica-based models, either as FMUs `Functional Mock-up
Units <https://fmi-standard.org/>` or using the OpenModelica or Dymola Python APIs. It allows for easily configurable
simulation setup, execution and evaluation via a generic text-based interface. Its main purpose is parallelization of
simulations and parameter sweeps. Furthermore, it provides a generic interface for Multi-Objective-Optimization.
"""

install_requires = ['fmpy', 'dask[bag]', 'numpy', 'PyYAML', 'plotly', 'matplotlib', 'requests']

extras_require = {
    'develop': ['pytest', 'pytest-cov', 'flake8', 'pre-commit'],
    'optimization': ['paref', 'pymoo'],
    # 'dymola': ['dymola'],
    # 'openmodelica': ['OMPython'],

}

setup(name='moo_sim_interface',
      version='0.4.0',
      description='A generic interface for Modelica/FMU simulation and optimization',
      long_description=long_description,
      long_description_content_type='text/markdown',
      author='Sebastian Mortag',
      author_email='mortag@hm.edu',
      url='https://github.com/SebastianMortag/moo-sim-interface',
      license='MIT',
      packages=find_packages(),
      python_requires='>=3.10',
      install_requires=install_requires,
      entry_points={'console_scripts': ['run_sim=moo_sim_interface.simulator_api:main']})
