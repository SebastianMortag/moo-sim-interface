import os
from typing import Union

import numpy as np

from moo_sim_interface.utils.batched_iterator import BatchedIterator
from moo_sim_interface.utils.dependency_installer import install_dymola_python_egg
from moo_sim_interface.utils.post_simulation_data_processor import PostSimulationDataProcessor
from moo_sim_interface.utils.yaml_config_parser import prepare_simulation_environment

DymolaFunctionException = None


def run_simulation(return_results: bool = False, **args) -> Union[None, list]:
    global DymolaFunctionException
    try:
        from dymola.dymola_exception import DymolaFunctionException
        from dymola.dymola_interface import DymolaInterface
    except ModuleNotFoundError:
        simulator_path = args.get('simulator_path')
        install_dymola_python_egg(simulator_path)
        from dymola.dymola_exception import DymolaFunctionException
        from dymola.dymola_interface import DymolaInterface

    (model_filename, model_path, input_values, input_parameter_names, num_chunks, output_parameter_names,
     sync_execution, time_modulo, result_transformation, custom_build_dir) = prepare_simulation_environment(args)

    post_simulation_data_processor = PostSimulationDataProcessor()

    transformation_option = args.get('simulation_setup').get('output_configuration').get('result_transformation')
    # TODO: generalize trajectory saving using yaml parser
    save_trajectories = False if transformation_option == 'take_last' or transformation_option == '1-take_last' else \
        True

    sim_params = args.get('simulation_setup')
    model_name = args.get('model_name')
    pre_sim_script = args.get('pre_sim_scripts')
    post_sim_scripts = args.get('post_sim_scripts')

    print(f'Simulation of {np.size(input_values[0]) if len(input_values) > 0 else 0} parameter variation(s) on '
          f'{model_name}:')

    dymola_instance = DymolaInterface(startDymola=True)
    for script in pre_sim_script:
        dymola_instance.RunScript(script)

    dymola_instance.openModel(model_filename, changeDirectory=False)

    if custom_build_dir is not None:
        os.makedirs(custom_build_dir, exist_ok=True)
        dymola_instance.cd(custom_build_dir)

    start_time = sim_params.get('start_time')
    stop_time = sim_params.get('stop_time')
    step_size = sim_params.get('step_size')
    if step_size is None:
        step_size = (stop_time - start_time) / sim_params.get('num_of_steps')

    number_of_intervals = sim_params.get('num_of_steps')
    if number_of_intervals is None:
        number_of_intervals = int((stop_time - start_time) / step_size)
    output_interval = step_size
    method = args.get('solver')
    tolerance = sim_params.get('tolerance')
    fixed_step_size = 0.0

    indices = list(np.ndindex(input_values[0].shape if len(input_values) > 0 else (1,)))
    combined_results = []
    if num_chunks == 1:
        for i in indices:
            initial_values = [values[i] for values in input_values]  # set the start values
            result_file = '_'.join([model_name, str(i)])

            results = do_single_simulation(dymola_instance, save_trajectories, model_name, start_time,
                                           stop_time, number_of_intervals,
                                           output_interval, method, tolerance, fixed_step_size, result_file,
                                           input_parameter_names, initial_values, output_parameter_names)

            combined_results.append([(i, result_transformation(results))])
            combined_results.append([])  # placeholder for all parameters results
    else:
        for batch in BatchedIterator(indices, batch_size=num_chunks):  # work through n tasks in parallel
            initial_values = [[values[i] for values in input_values] for i in batch]  # set the start values
            result_file = '_'.join([model_name, str(batch[0]), str(batch[-1])])

            results = do_multi_simulation(dymola_instance, save_trajectories, model_name, start_time,
                                          stop_time, number_of_intervals,
                                          output_interval, method, tolerance, fixed_step_size, result_file,
                                          input_parameter_names, initial_values, output_parameter_names, [])

            for i, result in zip(batch, results):
                combined_results.append([(i, result_transformation(result))])
                combined_results.append([])  # placeholder for all parameters results

    processed_results = post_simulation_data_processor.do_post_processing(args, input_values, combined_results,
                                                                          model_name, return_results=return_results)

    for script in post_sim_scripts:
        dymola_instance.RunScript(script)

    if return_results:
        return processed_results


def do_single_simulation(dymola_instance, save_trajectories, *sim_args):
    print(f'Running simulation with values: {sim_args[-2]}')
    try:
        if save_trajectories:
            (model, start_time, stop_time, number_of_intervals, output_interval, method, tolerance, fixed_step_size,
             result_file, initial_names, initial_values, final_names) = sim_args

            output = dymola_instance.simulateMultiResultsModel(model, start_time, stop_time, number_of_intervals,
                                                               output_interval, method, tolerance, fixed_step_size,
                                                               result_file, initial_names, [initial_values], final_names
                                                               , [])
            output[1] = output[1][0]
        else:
            output = dymola_instance.simulateExtendedModel(*sim_args)
            output[1] = [[out] for out in output[1]]
    except DymolaFunctionException as de:
        print(de)
        log = dymola_instance.getLastErrorLog()
        print(log)
        output = []
    if len(output) != 2:
        print(f'Incorrect number of output parameters. Was {len(output)}, expected 2.')

    status = output[0]
    if not status:
        print('Simulation failed. Dymola Error Log:')
        log = dymola_instance.getLastErrorLog()
        print(log)

    values = output[1]
    if len(values) != len(sim_args[-1]):
        print(f'Incorrect number of result values. Was {len(values)}, expected {len(sim_args[-1])}.')
    return values


def do_multi_simulation(dymola_instance, save_trajectories, *sim_args):
    print(f'Running {len(sim_args[-3])} sweeps with '
          f'{"values: " + str(sim_args[-3]) if np.size(sim_args[-3]) < 10 else str(np.size(sim_args[-3])) + " values"}')
    try:
        if save_trajectories:
            output = dymola_instance.simulateMultiResultsModel(*sim_args)
        else:
            output = dymola_instance.simulateMultiExtendedModel(*sim_args)
            output[1] = [[[o] for o in out] for out in output[1]]

    except DymolaFunctionException as de:
        print(de)
        log = dymola_instance.getLastErrorLog()
        print(log)
        output = []

    if len(output) != 2:
        print(f'Incorrect number of output parameters. Was {len(output)}, expected 2.')

    status = output[0]
    if not status:
        print('Simulation failed. Dymola Error Log:')
        log = dymola_instance.getLastErrorLog()
        print(log)

    values = output[1]
    for value_set in values:
        if len(value_set) != len(sim_args[-2]):
            print(f'Incorrect number of result values. Was {len(value_set)}, expected {len(sim_args[-2])}.')
    return values
