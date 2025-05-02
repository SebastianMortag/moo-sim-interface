import math
import numbers
import pathlib
import re
import sys
import types


def validate_simulation_configuration(simulation_config: dict) -> bool:
    if not isinstance(simulation_config.get('experimental_mode_on'), bool):
        raise ValueError('Invalid experimental_mode_on option, choose either True or False!')
    if simulation_config.get('experimental_mode_on'):
        if check_experimental_options(simulation_config):
            return True

    check_general_options(simulation_config)
    check_simulation_setup(simulation_config.get('simulation_setup'))
    check_post_simulation_options(simulation_config.get('post_simulation_options'))
    check_fmu_settings(simulation_config.get('fmu_settings'))
    return True


def validate_optimization_configuration(optimization_config: dict) -> bool:
    return True


def check_experimental_options(simulation_config: dict) -> bool:
    experimental_options = simulation_config.get('experimental_options')
    simulation_config['simulation_setup']['safe_mode_type'] = experimental_options.get('safe_mode_type')
    simulation_config['simulation_setup']['alt_config_file'] = experimental_options.get('alternative_config_file')
    simulation_config['post_simulation_options']['plot_results'] = experimental_options.get('plot_results')
    simulation_config['post_simulation_options']['plot_results_lib'] = experimental_options.get('plot_results_lib')

    if experimental_options.get('skip_configuration_check'):
        return True

    if not isinstance(experimental_options.get('plot_results'), bool):
        raise ValueError('Invalid plot_results option, choose either True or False!')
    if experimental_options.get('plot_results') and len(simulation_config.get('simulation_setup').get(
            'output_configuration').get('parameter_names')) != 2:
        raise ValueError('Invalid output option, choose exactly two output parameters when plotting!')
    if experimental_options.get('plot_results') and experimental_options.get('plot_results_lib') not in ['matplotlib',
                                                                                                         'plotly']:
        raise ValueError('Invalid plot_results_lib, choose either matplotlib or plotly!')

    if experimental_options.get('custom_result_transformation') != 'None':
        if not experimental_options.get('custom_result_transformation').startswith('np.'):
            raise ValueError('Invalid custom_result_transformation, must start with "np." to call a numpy function!')
        try:
            mycode = compile(experimental_options.get('custom_result_transformation'), '<string>', 'eval')
            simulation_config['simulation_setup']['output_configuration']['result_transformation'] = mycode
        except SyntaxError:
            raise ValueError('Invalid custom_result_transformation, could not compile expression!')

    if experimental_options.get('safe_mode_type') not in [0, 1, 2, 3, 4]:
        raise ValueError('Invalid safe_mode_type, choose either 0, 1, 2, 3 or 4!')
    if experimental_options.get('safe_mode_type') == 4 and experimental_options.get(
            'alternative_config_file') == 'None':
        raise ValueError('Invalid alternative_config_file, choose an alternative configuration for safe mode type: 4!')
    return False


def check_general_options(general_options: dict):
    if general_options.get('model_file') is None:
        raise ValueError('model_file is not set in the simulation configuration!')
    if not isinstance(general_options.get('model_file'), str):
        raise ValueError('Invalid model_file, must be a string!')
    if not (general_options.get('model_file').endswith('.fmu') or general_options.get('model_file').endswith('.mo')):
        raise ValueError('Invalid filename! model_file must end with .mo or .fmu!')

    # Add list of valid solvers for each simulator
    if general_options.get('solver') is not None:
        if not isinstance(general_options.get('solver'), str):
            raise ValueError('Invalid solver, must be a string!')

    if not general_options.get('model_file').endswith('.fmu'):
        if general_options.get('model_name') is None:
            raise ValueError('model_name is not set in the simulation configuration!')

        if general_options.get('simulator_path') is None:
            # on Windows, the path must be set to the bin directory of the OpenModelica installation:
            if sys.platform == 'win32':
                raise ValueError('simulator_path is not set in the simulation configuration! Please point to the '
                                 'simulator installation directory!')
            elif sys.platform == 'linux':
                print('Warning: simulator_path is not set. Trying to infer the simulator directory...')
        else:
            if not pathlib.Path(general_options.get('simulator_path')).is_dir():
                raise ValueError('Invalid simulator_path, must be a directory!')

    if not isinstance(general_options.get('pre_sim_scripts'), list):
        raise ValueError('Invalid pre_sim_scripts, must be a list!')
    for script in general_options.get('pre_sim_scripts'):
        if not pathlib.Path(script).is_file():
            raise ValueError('Invalid pre_sim_scripts, must be a list of valid files!')

    if not isinstance(general_options.get('post_sim_scripts'), list):
        raise ValueError('Invalid post_sim_scripts, must be a list!')
    for script in general_options.get('post_sim_scripts'):
        if not pathlib.Path(script).is_file():
            raise ValueError('Invalid post_sim_scripts, must be a list of valid files!')

    if general_options.get('custom_build_dir') is not None and general_options.get('custom_build_dir') != 'None':
        if not isinstance(general_options.get('custom_build_dir'), str):
            raise ValueError('Invalid custom_build_dir, must be empty, None or a directory!')

    if general_options.get('n_chunks') is None or not isinstance(general_options.get('n_chunks'), int):
        raise ValueError('Invalid n_chunks, choose an integer value!')

    if not isinstance(general_options.get('sim_flags'), list):
        raise ValueError('Invalid sim_flags, must be a list!')
    for flag in general_options.get('sim_flags'):
        if not isinstance(flag, str):
            raise ValueError('Invalid sim_flags, must be a list of strings from '
                             'https://openmodelica.org/doc/OpenModelicaUsersGuide/latest/simulationflags.html')


def check_simulation_setup(simulation_setup: dict):
    if (not isinstance(simulation_setup.get('step_size'), numbers.Real) or
            simulation_setup.get('step_size') == 0.0):
        simulation_setup['step_size'] = None
    if (not isinstance(simulation_setup.get('num_of_steps'), numbers.Real) or
            simulation_setup.get('num_of_steps') == 0.0):
        simulation_setup['num_of_steps'] = None

    if (simulation_setup.get('step_size') is not None and simulation_setup.get('num_of_steps') is not None or
            (simulation_setup.get('step_size') is None and simulation_setup.get('num_of_steps') is None)):
        raise ValueError('Choose either step_size OR num_of_steps for the simulation!')

    if len(simulation_setup.get('input_configuration').get('parameter_names')) != len(
            simulation_setup.get('input_configuration').get('parameter_values')):
        raise ValueError('Number of input parameter names and parameter values must be equal!')

    if not isinstance(simulation_setup.get('input_configuration').get('pairwise'), bool):
        raise ValueError('pairwise must be a boolean value!')

    if not simulation_setup.get('input_configuration').get('pairwise'):
        if len({len(values) if isinstance(values, list) else get_num_of_values_from_input_range(values) for values in
                simulation_setup.get('input_configuration').get('parameter_values')}) > 1:
            raise ValueError('Number of input parameter values must be equal for every parameter if pairwise is False!')

    if not simulation_setup.get('output_configuration').get('parameter_names'):
        raise ValueError('No output parameter names specified!')

    if isinstance(simulation_setup.get('output_configuration').get('result_transformation'), list):
        if len(simulation_setup.get('output_configuration').get('parameter_names')) != len(
                simulation_setup.get('output_configuration').get('result_transformation')):
            raise ValueError('Number of output parameter names and result transformations must be equal!')
        for opt in simulation_setup.get('output_configuration').get('result_transformation'):
            if opt not in ['take_last', '1-take_last', 'mean', 'average', 'median', 'min', 'max', 'sum', 'std', 'var',
                           'None']:
                raise ValueError(
                    'Invalid result_transformation, choose either take_last, 1-take_last, mean, average, median, min, '
                    'max, sum, std, var or None!')
    elif isinstance(simulation_setup.get('output_configuration').get('result_transformation'), types.CodeType):
        pass
    else:
        if (simulation_setup.get('output_configuration').get('result_transformation') not in
                ['take_last', '1-take_last', 'mean', 'average', 'median', 'min', 'max', 'sum', 'std', 'var', 'None']):
            raise ValueError(
                'Invalid result_transformation, choose either take_last, 1-take_last, mean, average, median, min, '
                'max, sum, std, var or None!')


def check_post_simulation_options(post_simulation_options: dict):
    if post_simulation_options.get('save_results_options') is not None:
        if post_simulation_options.get('save_results_options') not in ['csv', 'txt', 'None']:
            raise ValueError('Invalid save options, choose either csv or txt or None!')

    if not isinstance(post_simulation_options.get('print_results'), bool):
        raise ValueError('Invalid print results option, choose either True or False!')


def check_fmu_settings(fmu_settings: dict):
    if not isinstance(fmu_settings.get('show_progressbar'), bool):
        raise ValueError('Invalid show progressbar option, choose either True or False!')

    if fmu_settings.get('print_single_simulation_progress') not in ['s', 'm', 'h', 'd', 'None']:
        raise ValueError('Invalid print_single_simulation_progress, choose either s, m, h, d or None!')

    if not isinstance(fmu_settings.get('save_all_simulation_parameters'), bool):
        raise ValueError('Invalid save all simulation parameters option, choose either True or False!')

    if fmu_settings.get('parameters_regex_filter') != 'None':
        try:
            re.compile(fmu_settings.get('parameters_regex_filter'))
        except re.error:
            raise ValueError('Invalid parameters_regex_filter, could not compile regex!')

    if fmu_settings.get('filter_mode') not in ['include', 'exclude']:
        raise ValueError('Invalid filter mode, choose either include or exclude!')


def get_num_of_values_from_input_range(input_range: str) -> int:
    values = [float(v) for v in input_range.split(':')]
    return math.floor(round((values[2] - values[0]) / values[1], 10)) + 1
