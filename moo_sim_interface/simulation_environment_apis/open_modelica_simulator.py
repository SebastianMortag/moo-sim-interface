import multiprocessing
import os
import shutil
from importlib.metadata import version
from importlib.util import find_spec
from math import ceil
from typing import Union

import numpy as np

from moo_sim_interface.utils.batched_iterator import BatchedIterator
from moo_sim_interface.utils.dependency_installer import install_openmodelica_package
from moo_sim_interface.utils.post_simulation_data_processor import PostSimulationDataProcessor
from moo_sim_interface.utils.yaml_config_parser import prepare_simulation_environment


def run_simulation(return_results: bool = False, **args) -> Union[None, list]:
    if find_spec('OMPython') is None:
        simulator_path = args.get('simulator_path')
        install_openmodelica_package(simulator_path)  # try to install the OMPython package

    (model_filename, model_path, input_values, input_names, num_chunks, final_names, sync_execution,
     time_modulo, result_transformation, custom_build_dir) = prepare_simulation_environment(args)

    if version("OMPython") > "3.4.9":
        model_path = model_path.as_posix()
    if version("OMPython") < "3.6.0":
        print('\033[93m' + 'Warning: The current version of OMPython is not supported. Upgrade to version 3.6.0 or '
                           'proceed at your own risk.' + '\033[0m')

    post_simulation_data_processor = PostSimulationDataProcessor()
    pre_sim_scripts = args.get('pre_sim_scripts')
    post_sim_scripts = args.get('post_sim_scripts')
    sim_params = args.get('simulation_setup')
    model_name = args.get('model_name')

    print(f'Simulation of {np.size(input_values[0]) if len(input_values) > 0 else 0} parameter variation(s) on '
          f'{model_name}:')

    start_time = sim_params.get('start_time')
    stop_time = sim_params.get('stop_time')
    step_size = sim_params.get('step_size')
    number_of_intervals = sim_params.get('num_of_steps')
    if number_of_intervals is None:
        number_of_intervals = int((stop_time - start_time) / step_size)
    if step_size is None:
        step_size = (stop_time - start_time) / number_of_intervals
    method = args.get('solver')
    tolerance = sim_params.get('tolerance')
    flags = args.get('sim_flags')
    if len(flags) == 0:
        flags = None
    else:
        flags = ' '.join(flags)

    indices = list(np.ndindex(input_values[0].shape if len(input_values) > 0 else (1,)))

    if num_chunks == 1:
        from moo_sim_interface.utils.OMPythonFast import ModelicaSystemFast
        model = ModelicaSystemFast(model_path, model_name, commandLineOptions='--demoMode',
                                   customBuildDirectory=custom_build_dir)
        for script in pre_sim_scripts:
            res = model.getconn.execute("runScript(\"" + script + "\")")
            if "Failed" in res:
                print(f'Failed to execute script: {script}')

        combined_results = run_simulation_in_order(final_names, indices, input_names, input_values, method, model,
                                                   start_time, step_size, stop_time, tolerance, flags,
                                                   result_transformation)

        for script in post_sim_scripts:
            res = model.getconn.execute("runScript(\"" + script + "\")")
            if "Failed" in res:
                print(f'Failed to execute script: {script}')

    else:
        combined_results = run_simulation_in_parallel(final_names, indices, input_names, input_values, method,
                                                      model_path, model_name, start_time, step_size, stop_time,
                                                      tolerance, flags, num_chunks, result_transformation,
                                                      pre_sim_scripts, post_sim_scripts, custom_build_dir)

    processed_results = post_simulation_data_processor.do_post_processing(args, input_values, combined_results,
                                                                          model_name, return_results=return_results)

    if return_results:
        return processed_results


def run_simulation_in_order(final_names, indices, initial_names, input_values, method, model, start_time, step_size,
                            stop_time, tolerance, flags, result_transformation) -> list[list]:
    combined_results = []
    for i in indices:
        initial_values = [values[i] for values in input_values]  # set the start values

        model.setParameters([f'{name}={value}' for name, value in zip(initial_names, initial_values)])
        model.setSimulationOptions(
            [f'startTime={start_time}', f'stopTime={stop_time}', f'stepSize={step_size}', f'solver={method}',
             f'tolerance={tolerance}'])
        model.simulate(simflags=flags)  # simflags='-noEventEmit'
        # model.simulate(simflags='-lv=-assert,-stdout')  # simflags='-noEventEmit'
        results = model.getSolutions(final_names)

        combined_results.append([(i, result_transformation(results))])
        combined_results.append([])  # placeholder for all parameters results
    return combined_results


def run_simulation_in_parallel(final_names, indices, initial_names, input_values, method, model_path, model_name,
                               start_time, step_size, stop_time, tolerance, flags, num_chunks, result_transformation,
                               pre_sim_scripts, post_sim_scripts, custom_build_dir) -> list[list]:
    print(f'Running simulation in parallel with {num_chunks} workers.')

    batch_size = ceil(len(indices) / num_chunks)  # calculate the batch size and work on all batches in parallel

    batched_indices = [batch for batch in BatchedIterator(indices, batch_size)]

    # Prepare the arguments to be passed to each worker
    worker_args = [
        (indices, final_names, initial_names, input_values, method, model_path, model_name, start_time, step_size,
         stop_time, tolerance, flags, pre_sim_scripts, post_sim_scripts, custom_build_dir)
        for indices in batched_indices]

    with multiprocessing.Pool(processes=num_chunks) as pool:
        results = pool.starmap(simulate_model_worker, worker_args)

    # Process the results
    combined_results = []
    for indices, collected_results in results:
        for index, result in zip(indices, collected_results):
            combined_results.append([(index, result_transformation(result))])
            combined_results.append([])  # Placeholder for all parameters results (if needed)

    return combined_results


def simulate_model_worker(indices, final_names, initial_names, input_values, method, model_path, model_name,
                          start_time, step_size, stop_time, tolerance, flags, pre_sim_scripts, post_sim_scripts,
                          custom_build_dir):
    model, build_dir = create_omc_process(indices, model_path, model_name, pre_sim_scripts, custom_build_dir)

    collected_results = []

    for index in indices:
        initial_values = dict(zip(initial_names, [values[index] for values in input_values]))
        model.setParameters([f'{name}={value}' for name, value in initial_values.items()])
        model.setSimulationOptions(
            [f'startTime={start_time}', f'stopTime={stop_time}', f'stepSize={step_size}', f'solver={method}',
             f'tolerance={tolerance}']
        )

        result_file = construct_resultfile_name(model_name, index)

        # Simulate the model
        model.simulate(resultfile=result_file, simflags=flags)

        # Retrieve results
        result = model.getSolutions(final_names)
        collected_results.append(result)

    # Run post-simulation scripts
    for script in post_sim_scripts:
        res = model.getconn.execute("runScript(\"" + script + "\")")
        if "Failed" in res:
            print(f'Failed to execute script: {script}')

    stop_omc_process(model)

    if custom_build_dir is None:
        try:
            shutil.rmtree(build_dir)  # Remove the build directory
        except Exception as e:
            print(f"Error removing build directory {build_dir}: {e}")

    return indices, collected_results


def create_omc_process(indices, model_path, model_name, pre_sim_scripts, custom_build_dir):
    from moo_sim_interface.utils.OMPythonFast import ModelicaSystemFast

    # create a temporary build dir for multiple indices
    build_dir = construct_build_dir(model_name, indices, custom_build_dir)
    model = ModelicaSystemFast(model_path, model_name, customBuildDirectory=build_dir, commandLineOptions='--demoMode')
    for script in pre_sim_scripts:
        res = model.getconn.execute("runScript(\"" + script + "\")")
        if "Failed" in res:
            print(f'Failed to execute script: {script}')

    return model, build_dir


def stop_omc_process(model):
    # Explicitly quit the OMC process
    try:
        model.getconn.execute("quit()")  # Send quit command to OMC
        model.getconn._omc_process.wait(timeout=5.0)  # Wait for process to terminate
    except Exception as e:
        print(f"Error while terminating OMC process: {e}")
    finally:
        # Kill the process if it hasn't exited
        if model.getconn._omc_process.poll() is None:
            model.getconn._omc_process.kill()
        del model  # Explicitly delete the model object


def construct_resultfile_name(model_name, index):
    return f'{model_name}_{index}.mat'.replace(' ', '_')


def construct_build_dir(model_name, indices, custom_build_dir=None):
    index_appendix = f'{indices[0]}_{indices[-1]}' if len(indices) > 1 else f'{indices[0]}'
    base_dir = custom_build_dir if custom_build_dir is not None else os.getcwd()
    return os.path.join(base_dir, f'{model_name}_{index_appendix}'.replace(' ', '_'))
