import argparse
from typing import Union

from moo_sim_interface.multi_objective_optimization_apis import paref_optimizer, pymoo_optimizer
from moo_sim_interface.utils.yaml_config_parser import parse_moo_config_file


def moo_env_apis_wrapper(return_results: bool = False, **args) -> Union[None, list]:
    optimizer_environment = args.get('package').lower()
    if optimizer_environment == 'paref':
        results = paref_optimizer.run_optimization(return_results=return_results, **args)
    elif optimizer_environment == 'pymoo':
        results = pymoo_optimizer.run_optimization(return_results=return_results, **args)
    else:
        raise ValueError(f'Unknown Optimization Environment: {optimizer_environment}')

    if return_results:
        return results


def main():
    parser = argparse.ArgumentParser('run_moo')
    parser.add_argument('-f',
                        metavar='config_filename',
                        help='Provide the filename of your .yml optimization configuration file in the "configs" dir '
                             'or an absolute path (optional)',
                        type=str)
    launch_args = parser.parse_args()
    if launch_args.f is not None:
        moo_args = parse_moo_config_file(launch_args.f)
    else:
        print('No config file provided, using default config file from the current working directory.')
        moo_args = parse_moo_config_file()
    moo_env_apis_wrapper(**moo_args)


def run_optimizations(
        moo_config_file: str = None,
        overwrite_config: list[dict] = None,
        return_results: bool = True,
) -> list:
    if moo_config_file is None:
        print('No config file provided, using default config file from the current working directory.')
        moo_args = parse_moo_config_file(overwrite_config=overwrite_config)
    else:
        moo_args = parse_moo_config_file(moo_config_file, overwrite_config=overwrite_config)

    return moo_env_apis_wrapper(return_results=return_results, **moo_args)


if __name__ == '__main__':
    main()
