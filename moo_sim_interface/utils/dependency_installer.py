# this script can help to automatically install either Dymola or OpenModelica Python packages

import os
import pathlib
import sys
import requests


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

    if 'readme.md' not in os.listdir(omc_python_interface_path):
        add_missing_readme(omc_python_interface_path)

    command = f'cd {omc_python_interface_path} && {python_path} -m pip install -U .'  # install the OMPython package
    os.system(command)


def add_missing_readme(dir_path):
    url = 'https://raw.githubusercontent.com/OpenModelica/OMPython/master/README.md'
    if pathlib.Path(dir_path).exists():
        # Extract the file name from the URL
        file_name = url.split('/')[-1]

        # Full path to save the file
        save_path = os.path.join(dir_path, file_name)

        # Download the file
        response = requests.get(url)
        response.raise_for_status()  # Check if the request was successful

        # Save the file
        with open(save_path, 'wb') as file:
            file.write(response.content)
