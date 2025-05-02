import os

import numpy as np
import pytest
import shutil

from moo_sim_interface.simulator_api import run_simulations

skip_docker = pytest.mark.skipif(
    os.getenv('SKIP_DOCKER_TESTS') == 'true',
    reason="Skipping tests that should only run via ci in Docker"
)


@skip_docker
def test_open_modelica_simulator_500steps_simulation():
    config = 'openmodelica_test.yml'

    res = run_simulations(sim_config_file=config, return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 1  # one simulation
    assert len(res[0]) == 2  # a tuple with 2 elements
    assert res[0][0] == (0,)  # the index tuple of the simulation, that was performed
    assert len(res[0][1]) == 2  # retrieving two variables from the simulation
    assert len(res[0][1][0]) == 502  # 502 results for a simulation with 500 steps
    assert len(res[0][1][1]) == 502  # 502 results for a simulation with 500 steps


@skip_docker
def test_open_modelica_simulator_0point006stepsize_simulation():
    config = 'openmodelica_test.yml'

    overwrite = [{'simulation_setup': {'num_of_steps': 0.0,
                                       'step_size': 0.006}}]
    res = run_simulations(sim_config_file=config, overwrite_config=overwrite, return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 1  # one simulation
    assert len(res[0]) == 2  # a tuple with 2 elements
    assert res[0][0] == (0,)  # the index tuple of the simulation, that was performed
    assert len(res[0][1]) == 2  # retrieving two variables from the simulation
    assert len(res[0][1][0]) == 502  # 502 results for a simulation with 500 steps
    assert len(res[0][1][1]) == 502  # 502 results for a simulation with 500 steps


@skip_docker
def test_open_modelica_simulator_5parallel_100simulations():
    config = 'openmodelica_test.yml'

    num_simulations = 100
    damper_range = np.linspace(0.1, 0.5, num_simulations).tolist()  # from 0.1 to 0.5 with 100 steps
    overwrite = [{'simulation_setup': {'input_configuration': {'parameter_values': [damper_range]}}},
                 {'n_chunks': 4}]
    res = run_simulations(sim_config_file=config, overwrite_config=overwrite, return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == num_simulations  # 100 simulations
    for i in range(num_simulations):
        assert len(res[i]) == 2  # a tuple with 2 elements
        assert res[i][0] == (i,)  # the index tuple of the simulation, that was performed
        assert len(res[i][1]) == 2  # retrieving two variables from the simulation
        assert len(res[i][1][0]) == 502  # 502 results for a simulation with 500 steps
        assert len(res[i][1][1]) == 502  # 502 results for a simulation with 500 steps


@skip_docker
def test_open_modelica_simulator_custom_build_dir():
    config = 'openmodelica_test.yml'

    custom_build_dir = os.path.join(os.getcwd(), 'custom_build')
    overwrite = [{'custom_build_dir': custom_build_dir}]
    res = run_simulations(sim_config_file=config, overwrite_config=overwrite, return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 1

    # there should be a custom build directory with a _res.mat file inside
    assert os.path.exists(custom_build_dir)
    assert os.path.exists(
        os.path.join(custom_build_dir, 'Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum_res.mat'))

    shutil.rmtree(custom_build_dir)


@skip_docker
def test_open_modelica_simulator_empty_custom_build_dir():
    config = 'openmodelica_test.yml'

    model_name = 'Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum'
    custom_build_dir = os.path.join(os.getcwd(), model_name)
    overwrite = [{'custom_build_dir': None}]
    res = run_simulations(sim_config_file=config, overwrite_config=overwrite, return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 1

    # there should be a custom build directory named after the model name with a _res.mat file inside
    assert os.path.exists(custom_build_dir)
    assert os.path.exists(
        os.path.join(custom_build_dir, model_name + '_res.mat'))
