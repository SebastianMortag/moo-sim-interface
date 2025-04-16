import argparse
from typing import Union

from moo_sim_interface.simulation_environment_apis import (
    dymola_simulator,
    open_modelica_simulator,
)
from moo_sim_interface.simulation_environment_apis.fmu_simulator import (
    run_fmu_simulation,
)
from moo_sim_interface.utils.yaml_config_parser import parse_sim_config_file


def sim_env_apis_wrapper(return_results: bool = False, **args) -> Union[None, list]:
    simulation_environment = args.get('simulation_environment').lower()
    if simulation_environment == 'dymola':
        results = dymola_simulator.run_simulation(**args, return_results=return_results)
    elif simulation_environment == 'openmodelica':
        results = open_modelica_simulator.run_simulation(
            **args, return_results=return_results
        )
    elif simulation_environment == 'fmu':
        results = run_fmu_simulation(return_results=return_results, **args)
    else:
        raise ValueError(f'Unknown Simulation Environment: {simulation_environment}')

    if return_results:
        return results


def main():
    parser = argparse.ArgumentParser('run_sim')
    parser.add_argument('-f',
                        metavar='config_filename',
                        help='Provide the filename of your .yml simulation configuration file in the "configs" dir '
                             'or an absolute path (optional)',
                        type=str)
    launch_args = parser.parse_args()
    if launch_args.f is not None:
        sim_args = parse_sim_config_file(launch_args.f)
    else:
        print('No config file provided, using default config file from the current working directory.')
        sim_args = parse_sim_config_file()
    sim_env_apis_wrapper(**sim_args)


def run_simulations(
        sim_config_file: str = None,
        overwrite_config: list[dict] = None,
        return_results: bool = True,
) -> Union[None, list]:
    if sim_config_file is None:
        print('No config file provided, using default config file from the current working directory.')
        sim_args = parse_sim_config_file(overwrite_config=overwrite_config)
    else:
        sim_args = parse_sim_config_file(sim_config_file, overwrite_config=overwrite_config)

    return sim_env_apis_wrapper(**sim_args, return_results=return_results)


if __name__ == '__main__':
    main()
