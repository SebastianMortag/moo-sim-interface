import os
import pathlib
import time

import numpy as np
import pandas as pd


def save_results_to_csv(dataframe, model_name):
    file_path = create_save_dir(model_name, '_results.csv')
    dataframe.to_csv(file_path, sep=';', index=False, encoding='utf-8')


def create_save_dir(model_name, file_name_suffix: str = ''):
    file_name = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + file_name_suffix
    file_path = pathlib.Path(os.getcwd()) / 'optimization_results' / model_name
    file_path.mkdir(parents=True, exist_ok=True)
    return file_path / file_name


class PostOptimizationDataProcessor:
    def do_post_processing(self, moo_args, sim_args, evaluations) -> pd.DataFrame:
        moo_kpis = moo_args.get('kpi_calculation').get('kpis')

        d_names = sim_args.get('simulation_setup').get('input_configuration').get('parameter_names') if moo_args.get(
            'include_design_space') else []

        t_names = moo_kpis if len(moo_kpis) > 1 else sim_args.get('simulation_setup').get('output_configuration').get(
            'parameter_names')

        columns = d_names + t_names

        df = pd.DataFrame(evaluations, columns=columns)

        if moo_args.get('save_results'):
            if sim_args.get('model_name') is None:
                model_name = pathlib.Path(sim_args.get('model_file')).stem
            else:
                model_name = sim_args.get('model_name')
            save_results_to_csv(df, model_name)

        # do pareto plots
        # do statistical analysis like covar, sobol, sensitivity, loco ...
        # attach moo paths analysis

        return df

    def store_intermediate_results(self, results, sim_args):
        reshaped_evaluations = np.array([np.concatenate(item) for item in results])
        if sim_args.get('model_name') is None:
            model_name = pathlib.Path(sim_args.get('model_file')).stem
        else:
            model_name = sim_args.get('model_name')
        # write the numpy array to a file
        filename = model_name + '_intermediate_results.npy'
        if os.path.exists(filename):
            os.remove(filename)
        np.save(filename, reshaped_evaluations)
