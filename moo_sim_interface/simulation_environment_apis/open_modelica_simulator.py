import multiprocessing
import os
import shutil
import subprocess
import tempfile
import uuid
from importlib.metadata import version
from importlib.util import find_spec
from typing import Union

import numpy as np

from moo_sim_interface.utils.dependency_installer import install_openmodelica_package
from moo_sim_interface.utils.post_simulation_data_processor import PostSimulationDataProcessor
from moo_sim_interface.utils.yaml_config_parser import prepare_simulation_environment


def run_simulation(return_results: bool = False, **args) -> Union[None, list]:
    if find_spec('OMPython') is None:
        # try to install the OMPython package
        simulator_path = args.get('simulator_path')
        install_openmodelica_package(simulator_path)

    (model_filename, model_path, input_values, input_names, num_chunks, final_names, sync_execution,
     time_modulo, result_transformation) = prepare_simulation_environment(args)

    if version("OMPython") > "3.4.9":
        model_path = model_path.as_posix()

    post_simulation_data_processor = PostSimulationDataProcessor(args.get('post_simulation_options'), [])
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

    indices = list(np.ndindex(input_values[0].shape if len(input_values) > 0 else (1,)))

    if num_chunks == 1:
        from moo_sim_interface.utils.OMPythonFast import ModelicaSystemFast
        model = ModelicaSystemFast(model_path, model_name, commandLineOptions='--demoMode')
        for script in pre_sim_scripts:
            res = model.getconn.execute("runScript(\"" + script + "\")")
            if "Failed" in res:
                print(f'Failed to execute script: {script}')

        combined_results = run_simulation_in_order(final_names, indices, input_names, input_values, method, model,
                                                   start_time, step_size, stop_time, tolerance, result_transformation)

        for script in post_sim_scripts:
            res = model.getconn.execute("runScript(\"" + script + "\")")
            if "Failed" in res:
                print(f'Failed to execute script: {script}')

    else:
        combined_results = run_simulation_in_parallel(final_names, indices, input_names, input_values, method,
                                                      model_path, model_name, start_time, step_size, stop_time,
                                                      tolerance, num_chunks, sim_params, result_transformation,
                                                      pre_sim_scripts, post_sim_scripts)

    processed_results = post_simulation_data_processor.do_post_processing(args, input_values, combined_results,
                                                                          model_name, return_results=return_results)

    if return_results:
        return processed_results


def run_simulation_in_order(final_names, indices, initial_names, input_values, method, model, start_time, step_size,
                            stop_time, tolerance, result_transformation):
    combined_results = []
    for i in indices:
        initial_values = [values[i] for values in input_values]  # set the start values

        model.setParameters([f'{name}={value}' for name, value in zip(initial_names, initial_values)])
        model.setSimulationOptions(
            [f'startTime={start_time}', f'stopTime={stop_time}', f'stepSize={step_size}', f'solver={method}',
             f'tolerance={tolerance}'])
        model.simulate()  # simflags='-noEventEmit'
        # model.simulate(simflags='-lv=-assert,-stdout')  # simflags='-noEventEmit'
        results = model.getSolutions(final_names)

        combined_results.append([(i, result_transformation(results))])
        combined_results.append([])  # placeholder for all parameters results
    return combined_results


def run_simulation_in_parallel(final_names, indices, initial_names, input_values, method, model_path, model_name,
                               start_time, step_size, stop_time, tolerance, num_chunks, sim_params,
                               result_transformation, pre_sim_scripts, post_sim_scripts):
    print(f'Running simulation in parallel with {num_chunks} chunks.')

    process_list = [create_omc_process(index, model_path, model_name, start_time, stop_time, step_size, method,
                                       tolerance, pre_sim_scripts, dict(zip(initial_names, [values[index] for values in
                                                                                            input_values]))) for
                    index in indices]

    with multiprocessing.Pool(processes=num_chunks) as pool:
        finished_models = pool.starmap(
            simulate_model,
            process_list
        )

    results = []
    for model in finished_models:
        result = model.getSolutions(final_names)
        print(f'Results from {model.getconn._omc_process.pid}: {result}')
        results.append(result)

        for script in post_sim_scripts:
            res = model.getconn.execute("runScript(\"" + script + "\")")
            if "Failed" in res:
                print(f'Failed to execute script: {script}')

    # with (contextlib.nullcontext()):
    #     dask_bag = bag.from_sequence(indices, npartitions=num_chunks)
    #     combined_results = dask_bag.map_partitions(simulation_wrapper_function, initial_names, input_values,
    #                                                final_names, method, model_path, model_name, start_time,
    #                                                step_size, stop_time, tolerance, result_transformation).compute()
    return results


def create_omc_process(index, model_path, model_name, start_time, stop_time,
                       step_size, solver, tolerance, pre_sim_scripts, initial_values: dict):
    from OMPython import ModelicaSystem
    build_dir = construct_build_dir(model_name, index)
    print(build_dir)
    os.mkdir(build_dir)
    model = ModelicaSystem(model_path, model_name, customBuildDirectory=build_dir, commandLineOptions='--demoMode')
    for script in pre_sim_scripts:
        res = model.getconn.execute("runScript(\"" + script + "\")")
        if "Failed" in res:
            print(f'Failed to execute script: {script}')

    model.setParameters([f'{name}={value}' for name, value in initial_values.items()])
    model.setSimulationOptions(
        [f'startTime={start_time}', f'stopTime={stop_time}', f'stepSize={step_size}', f'solver={solver}',
         f'tolerance={tolerance}']
    )

    result_file = construct_resultfile_name(model_name, index)

    return model, result_file


def simulate_model(model, result_file):
    omc_p = model.simulate(resultfile=result_file)

    poll = omc_p.poll()
    if poll is None:
        omc_p.wait()
        omc_p.terminate()
    return model


def simulation_wrapper_function(*args):
    (indices, initial_names, input_values, final_names, method, model_path, model_name, start_time, step_size,
     stop_time, tolerance, result_transformation) = args
    # Idea: Copy the Model exe and lib files to a temporary directory and run one instance of the model per chunk
    from OMPython import ModelicaSystem
    model = ModelicaSystem(model_path, model_name, commandLineOptions='--demoMode')

    # Create a temporary directory with a random ID
    temp_dir = os.path.join(tempfile.gettempdir(), str(uuid.uuid4()))
    os.makedirs(temp_dir, exist_ok=True)

    # Copy necessary files to the temporary directory
    for file in os.listdir(os.getcwd()):
        if os.path.splitext(file)[0] == model_name:
            shutil.copy(file, temp_dir)
    os.chdir(temp_dir)

    print(f'{model.getconn._omc_process.pid}')

    results = []
    for i in indices:
        initial_values = [values[i] for values in input_values]
        # TODO: use interface provided by ModelicaSystem
        getExeFile = os.path.join(os.getcwd(), '{}.{}'.format(model_name, "exe")).replace("\\", "/")

        result_file = construct_resultfile_name(model_name, i)

        sim_options = (
            f'startTime={start_time},stopTime={stop_time},stepSize={step_size},'
            f'tolerance={tolerance},solver=\"{method}\"')

        values1 = ','.join("%s=%s" % (key, val) for (key, val) in zip(initial_names, initial_values))
        override = " -override=" + values1 + ',' + sim_options
        model.getconn.sendExpression("simulate(" + model_name + "," + sim_options + ")")

        cmd = getExeFile + override + ' -r=' + result_file
        omhome = os.path.join(os.environ.get("OPENMODELICAHOME"))
        dllPath = os.path.join(omhome, "bin").replace("\\", "/") + os.pathsep + os.path.join(omhome,
                                                                                             "lib/omc").replace(
            "\\", "/") + os.pathsep + os.path.join(omhome, "lib/omc/cpp").replace("\\",
                                                                                  "/") + os.pathsep + os.path.join(
            omhome, "lib/omc/omsicpp").replace("\\", "/")
        my_env = os.environ.copy()
        my_env["PATH"] = dllPath + os.pathsep + my_env["PATH"]
        p = subprocess.Popen(cmd, env=my_env)
        p.wait()
        p.terminate()

        result = model.getSolutions(final_names, resultfile=result_file)
        # print(f'Results from {model.getconn._omc_process.pid}: {result}')

        results.append((i, result_transformation(result)))
    return results, []


def construct_resultfile_name(model_name, index):
    return os.path.join(os.getcwd(), f'{model_name}_{index}.mat'.replace(' ', '_'))


def construct_build_dir(model_name, index):
    return os.path.join(os.getcwd(), f'{model_name}_{index}'.replace(' ', '_'))
