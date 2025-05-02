import os
import pathlib
import types
from typing import Callable

import numpy as np
import yaml

from moo_sim_interface.utils.yaml_config_validator import validate_simulation_configuration, \
    validate_optimization_configuration
from moo_sim_interface.utils.yaml_loader import CustomSafeLoader


def prepare_simulation_environment(args: dict):
    """
    Prepares the simulation environment by extracting the necessary parameters from the simulation configuration.
    :param args: the parsed simulation configuration as a dictionary
    :return: a tuple containing the extracted parameters
    """
    model_filename = args.get('model_file')
    model_path = pathlib.Path(model_filename)
    if not model_path.is_absolute():
        if model_filename.endswith('.fmu'):
            model_path = pathlib.Path(os.getcwd()) / 'fmus' / model_filename
        else:
            model_path = pathlib.Path(os.getcwd()) / model_filename
    input_parameter_names = args.get('simulation_setup').get('input_configuration').get('parameter_names')
    input_parameter_values = args.get('simulation_setup').get('input_configuration').get('parameter_values')
    output_parameter_names = args.get('simulation_setup').get('output_configuration').get('parameter_names')
    result_transformation = construct_result_transformation(
        args.get('simulation_setup').get('output_configuration').get('result_transformation'))
    time_modulo = get_time_modulo(args.get('fmu_settings').get('print_single_simulation_progress'))
    sync_execution = args.get('fmu_settings').get('sync')
    num_chunks = args.get('n_chunks')
    create_mesh = args.get('simulation_setup').get('input_configuration').get('pairwise')

    input_parameter_values = [input_list if isinstance(input_list, list) else parse_input_range(input_list) for
                              input_list in input_parameter_values]

    if create_mesh:
        input_values = np.array(np.meshgrid(*input_parameter_values, indexing='ij'), dtype=np.float64)
    else:
        input_values = np.array(input_parameter_values, dtype=np.float64)

    custom_build_dir = args.get('custom_build_dir')
    if custom_build_dir is None:
        if args.get('model_name') is None:
            model_name = model_path.stem
        else:
            model_name = args.get('model_name')
        custom_build_dir = os.path.join(os.getcwd(), model_name)
    elif custom_build_dir == 'None':
        custom_build_dir = None
    else:
        custom_build_path = pathlib.Path(custom_build_dir)
        if not custom_build_path.is_absolute():
            custom_build_dir = os.path.join(os.getcwd(), custom_build_dir)
        else:
            custom_build_dir = custom_build_path.as_posix()

    return (model_filename, model_path, input_values, input_parameter_names, num_chunks, output_parameter_names,
            sync_execution, time_modulo, result_transformation, custom_build_dir)


def prepare_optimization_environment(args: dict):
    # check if kip function is callable or string
    # if string, check for ':' and parse it as file path and method name, or use main as method name
    # TODO: implement this
    pass


def parse_input_range(input_range: str) -> list:
    input_range_values = input_range.split(':')
    try:
        start = int(input_range_values[0])
        step = int(input_range_values[1])
        stop = int(input_range_values[2]) + 1
        return list(range(start, stop, step))
    except ValueError:
        start = float(input_range_values[0])
        step = float(input_range_values[1])
        stop = float(input_range_values[2]) + step
        return np.arange(start=start, stop=stop, step=step).tolist()


def construct_result_transformation(result_transformation) -> Callable:
    if isinstance(result_transformation, list):
        transformations = [construct_single_result_transformation(transformation) for transformation in
                           result_transformation]
        return lambda x: [transformations[i](x[i], 0) for i in range(len(transformations))]
    elif isinstance(result_transformation, types.CodeType):
        return lambda x: eval(result_transformation, {}, {'np': np, 'x': x})
    else:
        return construct_single_result_transformation(result_transformation)


def construct_single_result_transformation(result_transformation: str) -> Callable:
    axis = 1
    if result_transformation == 'take_last':
        return lambda x: np.apply_along_axis(lambda y: y[-1], axis, x).tolist()
    elif result_transformation == '1-take_last':
        return lambda x: np.apply_along_axis(lambda y: 1 - y[-1], axis, x).tolist()
    elif result_transformation == 'average':
        return lambda x: np.average(x, axis=axis)
    elif result_transformation == 'mean':
        return lambda x: np.mean(x, axis=axis)
    elif result_transformation == 'median':
        return lambda x: np.median(x, axis=axis)
    elif result_transformation == 'min':
        return lambda x: np.min(x, axis=axis)
    elif result_transformation == 'max':
        return lambda x: np.max(x, axis=axis)
    elif result_transformation == 'sum':
        return lambda x: np.sum(x, axis=axis)
    elif result_transformation == 'std':
        return lambda x: np.std(x, axis=axis)
    elif result_transformation == 'var':
        return lambda x: np.var(x, axis=axis)
    else:
        return lambda x: x


def get_time_modulo(print_single_simulation_progress: str):
    if print_single_simulation_progress == 's':
        return 1
    elif print_single_simulation_progress == 'm':
        return 60
    elif print_single_simulation_progress == 'h':
        return 60 * 60
    elif print_single_simulation_progress == 'd':
        return 24 * 60 * 60
    else:
        return float('inf')


def merge_dicts(config: dict, injection: dict):
    # traverse the dicts until a non-dict is met, that is the value to be replaced
    for key, value in injection.items():
        if key in config:
            if isinstance(value, dict):
                merge_dicts(config[key], value)
            else:
                config[key] = value


def _parse_config_file(config_file_path: str, overwrite_config: list[dict] = None) -> dict:
    config_file = pathlib.Path(config_file_path)
    if not config_file.is_absolute():
        config_file = pathlib.Path(os.getcwd()) / 'configs' / config_file_path

    with open(config_file, 'r') as file:
        # use a custom yaml loader, that parses "x:y:z" as start:step:stop range instead of the default day:hour:minute
        config = yaml.load(file, Loader=CustomSafeLoader)

        if overwrite_config is not None:
            for injection in overwrite_config:
                merge_dicts(config, injection)
        return config


def parse_sim_config_file(config_file_path: str = 'generic/simulation_config.yml',
                          overwrite_config: list[dict] = None) -> dict:
    simulation_config = _parse_config_file(config_file_path, overwrite_config)

    if validate_simulation_configuration(simulation_config):
        return simulation_config
    else:
        raise ValueError('Invalid simulation configuration file!')


def parse_moo_config_file(config_file_path: str = 'generic/optimization_config.yml',
                          overwrite_config: list[dict] = None) -> dict:
    optimization_config = _parse_config_file(config_file_path, overwrite_config)

    if validate_optimization_configuration(optimization_config):
        return optimization_config
    else:
        raise ValueError('Invalid optimization configuration file!')
