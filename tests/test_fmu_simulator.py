import os
from pathlib import Path

import pytest

from moo_sim_interface.simulator_api import run_simulations


@pytest.fixture
def base_path() -> Path:
    """Get the current folder of the test"""
    return Path(__file__).parent


skip_docker = pytest.mark.skipif(
    os.getenv('SKIP_DOCKER_TESTS') == 'true',
    reason="Skipping tests that should only run via ci in Docker"
)


@skip_docker
def test_fmu_simulator_1_year_example_system_10parallel_simulations(base_path: Path, monkeypatch: pytest.MonkeyPatch):
    target_indices = [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6), (0, 7), (0, 8), (0, 9), (1, 0), (1, 1),
                      (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8), (1, 9), (2, 0), (2, 1), (2, 2), (2, 3),
                      (2, 4), (2, 5), (2, 6), (2, 7), (2, 8), (2, 9), (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
                      (3, 6), (3, 7), (3, 8), (3, 9), (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
                      (4, 8), (4, 9), (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8), (5, 9),
                      (6, 0), (6, 1), (6, 2), (6, 3), (6, 4), (6, 5), (6, 6), (6, 7), (6, 8), (6, 9), (7, 0), (7, 1),
                      (7, 2), (7, 3), (7, 4), (7, 5), (7, 6), (7, 7), (7, 8), (7, 9), (8, 0), (8, 1), (8, 2), (8, 3),
                      (8, 4), (8, 5), (8, 6), (8, 7), (8, 8), (8, 9), (9, 0), (9, 1), (9, 2), (9, 3), (9, 4), (9, 5),
                      (9, 6), (9, 7), (9, 8), (9, 9)]

    monkeypatch.chdir(base_path / "..")

    config = 'sim_examples/pv_ess_heat_house.yml'

    overwrite = {'post_simulation_options': {'save_results_options': 'None'}}
    res = run_simulations(sim_config_file=config, overwrite_config=[overwrite], return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 100  # 100 simulations

    for i in range(100):
        assert len(res[i]) == 2  # a tuple with 2 elements
        assert res[i][0] == target_indices[i]  # the index tuple of the simulation, that was performed
        assert len(res[0][1]) == 2  # retrieving two variables from the simulation
        assert isinstance(res[0][1][0], float)  # getting a scalar value
        assert isinstance(res[0][1][1], float)  # getting a scalar value


@skip_docker
def test_fmu_simulator_1_year_example_system(base_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(base_path / "..")

    config = 'sim_examples/pv_ess_heat_house.yml'

    overwrite_csv = {'post_simulation_options': {'save_results_options': 'None'}}
    overwrite_parallel = {'n_chunks': 1}
    overwrite_values = {'simulation_setup': {'input_configuration': {'parameter_values': [[100], [10]]}}}
    overwrite_mesh = {'simulation_setup': {'input_configuration': {'pairwise': False}}}
    overwrite_res_trans = {'simulation_setup': {'output_configuration': {'result_transformation': 'None'}}}
    res = run_simulations(sim_config_file=config, overwrite_config=[overwrite_csv, overwrite_parallel, overwrite_values,
                                                                    overwrite_mesh, overwrite_res_trans],
                          return_results=True)

    # res should be a list of tuples, containing two lists with results
    assert res is not None
    assert len(res) == 1  # 1 simulation
    assert len(res[0]) == 2  # a tuple with 2 elements
    assert res[0][0] == (0,)  # the index tuple of the simulation, that was performed
    assert len(res[0][1]) == 2  # retrieving two variables from the simulation
    assert len(res[0][1][0]) == 87599  # getting all values
    assert len(res[0][1][1]) == 87599  # getting all values
