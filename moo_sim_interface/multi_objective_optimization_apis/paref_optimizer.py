import os
import pathlib
from typing import Union

import numpy as np
import pandas as pd
from paref.blackbox_functions.design_space.bounds import Bounds
from paref.interfaces.moo_algorithms.blackbox_function import BlackboxFunction
from paref.moo_algorithms.multi_dimensional.find_edge_points import FindEdgePoints
from paref.moo_algorithms.stopping_criteria.max_iterations_reached import MaxIterationsReached
from paref.moo_algorithms.two_dimensional.fill_gaps_of_pareto_front_2d import FillGapsOfParetoFront2D

from moo_sim_interface.simulator_api import sim_env_apis_wrapper
from moo_sim_interface.utils.post_optimization_data_processor import PostOptimizationDataProcessor
from moo_sim_interface.utils.yaml_config_parser import parse_sim_config_file


class _Blackbox(BlackboxFunction):
    def __init__(self, sim_args: dict, **moo_args):
        super().__init__()
        self.sim_args = sim_args
        self.n_workers = moo_args.get('paref_args').get('n_parallelization_for_sampling')
        self.target = moo_args.get('kpi_calculation').get('kpis')
        self.calculate_kpis = moo_args.get('kpi_calculation').get('kpi_function')
        self.d_design = len(sim_args.get('simulation_setup').get('input_configuration').get('parameter_names'))
        self.lower_b = np.array(moo_args.get('lower_bounds'))
        self.upper_b = np.array(moo_args.get('upper_bounds'))
        self.loaded_results_tracker = 0

    def __call__(self, x: np.ndarray, batch_evaluation: bool = False) -> np.ndarray:
        if batch_evaluation:
            inputs = x.T.tolist()
            if self.n_workers > 1:
                self.sim_args['n_chunks'] = self.n_workers
        else:
            inputs = [[val] for val in x]
            self.sim_args['n_chunks'] = 1

        self.sim_args['simulation_setup']['input_configuration']['parameter_values'] = inputs

        results = sim_env_apis_wrapper(**self.sim_args, return_results=True)

        if batch_evaluation:
            y = np.array([self.calculate_kpis(sim_result[1], xi) for sim_result, xi in zip(results, x)])
        else:
            y = self.calculate_kpis(results[0][1], x)

        return y

    @property
    def dimension_design_space(self) -> int:
        return self.d_design

    @property
    def dimension_target_space(self) -> int:
        return 2

    @property
    def design_space(self) -> Bounds:
        return Bounds(upper_bounds=self.upper_b, lower_bounds=self.lower_b)

    @property
    def allow_batch_evaluation(self) -> bool:
        return True


def run_optimization(return_results: bool = False, **moo_args) -> Union[pd.DataFrame | None]:
    sim_config_file = moo_args.get('simulation_config')
    sim_args = parse_sim_config_file(sim_config_file)

    design_space_overview = [
        name + (f'[{l:.2e}:' if l > 1e3 else f'[{l:.2f}:') + (f'{u:.2e}]' if u > 1e3 else f'{u:.2f}]') for name, l, u in
        zip(sim_args.get('simulation_setup').get('input_configuration').get('parameter_names'),
            moo_args.get('lower_bounds'), moo_args.get('upper_bounds'))]
    print('Optimization using paref with design space: ' + ', '.join(design_space_overview))

    result_df = _run_optimization(sim_args, moo_args, return_results)
    if return_results:
        return result_df


def _run_optimization(sim_args, moo_args, return_results: bool = False) -> Union[pd.DataFrame | None]:
    post_optimization_data_processor = PostOptimizationDataProcessor()

    store_intermediate_results = moo_args.get('paref_args').get('store_intermediate_results')
    load_intermediate_results = moo_args.get('paref_args').get('load_intermediate_results')

    model = _Blackbox(sim_args, **moo_args)
    model_evaluations = []

    if load_intermediate_results:
        intermediate_results = _load_intermediate_results(sim_args)
        model.evaluations = intermediate_results
        model.loaded_results_tracker = len(intermediate_results)

    lhc_samples = moo_args.get('paref_args').get('latin_hypercube_samples')
    if lhc_samples > 0 and not _is_intermediate_results_available(moo_args, model, lhc_samples):
        model.perform_lhc(lhc_samples)

        if store_intermediate_results:
            post_optimization_data_processor.store_intermediate_results(model.evaluations, sim_args)

    optimization_steps = moo_args.get('paref_args').get('optimization_steps')

    if optimization_steps is not None:
        for step in optimization_steps:
            for key, value in step.items():
                if _is_intermediate_results_available(moo_args, model, value):
                    continue
                if key == 'findEdgePoints':
                    max_iter_criteria = MaxIterationsReached(max_iterations=value)
                    task = FindEdgePoints()
                    task(blackbox_function=model, stopping_criteria=max_iter_criteria)
                elif key == 'fillGaps':
                    max_iter_criteria = MaxIterationsReached(max_iterations=value)
                    task = FillGapsOfParetoFront2D()
                    task(blackbox_function=model, stopping_criteria=max_iter_criteria)
                else:
                    raise NotImplementedError(f"Step {key} is not implemented")

            if store_intermediate_results:
                post_optimization_data_processor.store_intermediate_results(model.evaluations, sim_args)

    model_evaluations.append(model.evaluations)

    reshaped_evaluations = np.array([np.concatenate(item) for item in model_evaluations[0]])

    df = post_optimization_data_processor.do_post_processing(moo_args, sim_args, reshaped_evaluations)

    if return_results:
        return df


def _is_intermediate_results_available(moo_args, model, n_samples):
    intermediate_results_type = moo_args.get('paref_args').get('intermediate_results_type')
    if intermediate_results_type == 'basis':
        return False

    is_results_available = model.loaded_results_tracker >= n_samples
    if is_results_available:
        model.loaded_results_tracker -= n_samples
        return True
    else:
        return False


def _load_intermediate_results(sim_args):
    if sim_args.get('model_name') is None:
        model_name = pathlib.Path(sim_args.get('model_file')).stem
    else:
        model_name = sim_args.get('model_name')
    filename = model_name + '_intermediate_results.npy'
    if os.path.exists(filename):
        reshaped_evaluations = np.load(filename)
    else:
        raise FileNotFoundError(f"File {filename} not found")
    return reshaped_evaluations
