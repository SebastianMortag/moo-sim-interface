import contextlib
import os
import random
import shutil
from math import floor
from typing import Union

import dask
import fmpy
import numpy as np
from dask import bag
from dask.diagnostics import ProgressBar
from fmpy import read_model_description
from fmpy.fmi2 import FMU2Slave

import moo_sim_interface
from moo_sim_interface.utils.post_simulation_data_processor import PostSimulationDataProcessor
from moo_sim_interface.utils.recursively_ordered_dict import RecursivelyOrderedDict
from moo_sim_interface.utils.yaml_config_parser import parse_sim_config_file, prepare_simulation_environment

SIMULATION_RAMP_UP_TIME = 0.02


def run_fmu_simulation(return_results: bool = False, **kwargs) -> Union[None, list]:
    (fmu_filename, fmu_path, input_values, input_parameter_names, num_chunks, output_parameter_names, sync_execution,
     time_modulo, result_transformation, _) = prepare_simulation_environment(kwargs)

    if kwargs.get('model_name') is None:
        model_name = fmu_path.stem
    else:
        model_name = kwargs.get('model_name')

    print(f'Simulation of {np.size(input_values[0]) if len(input_values) > 0 else 0} parameter variation(s) on '
          f'{model_name}:')

    if sync_execution:
        dask.config.set(scheduler='synchronous')  # synchronized scheduler

    model_description = read_model_description(fmu_path)  # read the model description

    # collect the value references for the parameters to read / write
    value_references = {}
    for parameter in model_description.modelVariables:
        value_references[parameter.name] = parameter.valueReference

    post_simulation_data_processor = PostSimulationDataProcessor(kwargs.get('fmu_settings'),
                                                                 model_description.modelVariables)
    all_value_references = post_simulation_data_processor.get_value_references()
    sim_params = kwargs.get('simulation_setup')

    fmu_unzipped_dir = fmpy.extract(fmu_path)  # extract the FMU

    fmu_args = {'guid': model_description.guid,
                'modelIdentifier': model_description.coSimulation.modelIdentifier,
                'unzipDirectory': fmu_unzipped_dir}

    print_sim_progress = kwargs.get('fmu_settings').get('print_single_simulation_progress')

    # get the value references for the start and output values
    start_value_references = [value_references[name] for name in input_parameter_names]
    result_value_references = [value_references[name] for name in output_parameter_names]

    indices = list(np.ndindex(input_values[0].shape if len(input_values) > 0 else (1,)))

    with (ProgressBar() if kwargs.get('fmu_settings').get('show_progressbar') else contextlib.nullcontext()):
        dask_bag = bag.from_sequence(indices, npartitions=num_chunks)
        combined_results = dask_bag.map_partitions(simulation_wrapper_function, input_values, fmu_args, sim_params,
                                                   start_value_references, result_value_references, time_modulo,
                                                   print_sim_progress, sync_execution,
                                                   result_transformation, all_value_references).compute()

    # unload the shared library
    if sync_execution:
        while True:
            try:
                fmpy.freeLibrary(_dll_handle)
            except OSError:
                break

    shutil.rmtree(fmu_unzipped_dir, ignore_errors=True)  # clean up the temporary directory

    processed_results = post_simulation_data_processor.do_post_processing(kwargs, input_values, combined_results,
                                                                          model_name, return_results=return_results)

    if return_results:
        return processed_results


def simulation_wrapper_function(*args):
    indices, input_values, fmu_args, sim_params, start_value_references, result_value_references, time_modulo, \
        print_sim_progress, sync_execution, result_transformation, all_value_references = args
    zipped = []
    all_parameters_simulation_results = []
    fmu = FMU2Slave(**fmu_args)
    fmu.instantiate()

    for i in indices:  # iterate over all indices in this batch
        start_values = [values[i] for values in input_values]  # set the start values
        fmu.reset()
        fmu.setupExperiment()
        fmu.setReal(vr=start_value_references, value=start_values)

        fmu.enterInitializationMode()
        fmu.exitInitializationMode()

        start_time = sim_params.get('start_time')
        stop_time = sim_params.get('stop_time')
        step_size = sim_params.get('step_size')

        if step_size is None:
            step_size = (stop_time - start_time) / sim_params.get('num_of_steps')

        time = start_time
        sim_results = []

        while time <= SIMULATION_RAMP_UP_TIME:
            try:
                fmu.doStep(currentCommunicationPoint=time, communicationStepSize=step_size)
                time += step_size
            except Exception as e:
                handle_error(args, i, zipped, all_parameters_simulation_results, e)
                break

        # simulation loop
        while time < stop_time:
            try:
                time = do_simulation_step(fmu, result_value_references, sim_results, step_size, time)
            except Exception as e:
                handle_error(args, i, zipped, all_parameters_simulation_results, e)
                break

            if time % time_modulo == 0:
                print(f'Current time: {floor(time / time_modulo)}{print_sim_progress}')

        else:
            # this code block saves all simulation parameters at every step of the simulation, EXTREMELY SLOW!
            # produces .json output files of several GBs in size
            # for parameter_name, parameter_result in zip(all_value_references.keys(),
            #                                           fmu.getReal(all_value_references.values())):
            #     sim_result_list = full_simulation_results.get(parameter_name, [])
            #     sim_result_list.append(parameter_result)
            #     full_simulation_results[parameter_name] = sim_result_list
            full_simulation_results = RecursivelyOrderedDict()
            for parameter_name, parameter_result in zip(all_value_references.keys(),
                                                        fmu.getReal(all_value_references.values())):
                full_simulation_results[parameter_name] = parameter_result
            all_parameters_simulation_results.append(full_simulation_results)

            sim_results = np.array(sim_results).T.tolist()
            # apply transformation to the results; store the index and the results
            zipped.append((i, result_transformation(sim_results)))

    fmu.terminate()

    fmu.fmi2FreeInstance(fmu.component)  # call the FMI API directly to avoid unloading the share library

    if sim_params.get('sync'):
        global _dll_handle  # remember the shared library handle, so we can unload it later
        _dll_handle = fmu.dll._handle
    else:
        fmpy.freeLibrary(fmu.dll._handle)  # unload the shared library directly

    return zipped, all_parameters_simulation_results


def do_simulation_step(fmu, result_value_references, sim_results, step_size, time):
    fmu.doStep(currentCommunicationPoint=time, communicationStepSize=step_size)
    time += step_size
    result = fmu.getReal(result_value_references)
    sim_results.append(result)
    return time


def handle_error(args, i, zipped, all_parameters_simulation_results, exception):
    safe_mode_type = args[3].get('safe_mode_type')
    if safe_mode_type == 0:
        raise exception
    elif safe_mode_type == 1:
        print(f'Error occurred, skipping simulation: {i}')
        all_parameters_simulation_results.append({np.nan})
        zipped.append((i, np.nan))
    elif safe_mode_type == 2:
        os._exit(0)
    elif safe_mode_type == 3:
        print(f'Error occurred, retrying simulation: {i}')
        # increase the input values randomly between 1e-7% and 0.001%
        input_values = [value[i] * (1 + random.randint(1, 10000) / 1e9) for value in args[1]]
        for idx, value in enumerate(args[1]):
            value[i] = input_values[idx]
        t_args = list(args)
        t_args[0] = [i]
        args = tuple(t_args)
        a, b = simulation_wrapper_function(*args)
        zipped.append(a[0])
        all_parameters_simulation_results.append(b[0])
    elif safe_mode_type == 4:
        alt_config = args[3].get('alt_config_file')
        print(f'Error occurred, running alternative configuration: {alt_config}')
        moo_sim_interface.simulator_api.sim_env_apis_wrapper(**parse_sim_config_file(alt_config))
        all_parameters_simulation_results.append({alt_config})
        zipped.append((i, alt_config))
