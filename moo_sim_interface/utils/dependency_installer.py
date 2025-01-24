# this script can help to automatically install either Dymola or OpenModelica Python packages

import os
import pathlib
import sys


def install_dymola_python_egg(dymola_path):
    dymola_python_egg_path = os.path.join(dymola_path, 'Modelica', 'Library', 'python_interface', 'dymola.egg')
    while not pathlib.Path(dymola_python_egg_path).exists():
        print(f'Python interface not found at {dymola_python_egg_path}!')
        simulator_path = input('Provide the path to the Dymola installation folder: ')
        dymola_python_egg_path = os.path.join(simulator_path, 'Modelica', 'Library', 'python_interface', 'dymola.egg')

    sys.path.insert(0, dymola_python_egg_path)


def install_openmodelica_package(modelica_path):
    omc_python_interface_path = os.path.join(modelica_path, 'share', 'omc', 'scripts', 'PythonInterface')
    python_path = sys.executable

    command = f'cd {omc_python_interface_path} && {python_path} -m pip install -U .'  # install the OMPython package
    os.system(command)
