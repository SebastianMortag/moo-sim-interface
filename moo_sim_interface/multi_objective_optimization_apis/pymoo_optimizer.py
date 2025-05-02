from typing import Union

import numpy as np
import pandas as pd
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.optimize import minimize

from moo_sim_interface.simulator_api import sim_env_apis_wrapper
from moo_sim_interface.utils.yaml_config_parser import parse_sim_config_file


class _Blackbox(Problem):
    def __init__(self, sim_args: dict, **moo_args):
        super().__init__(n_var=4, n_obj=2, n_constr=0, xl=np.zeros(4), xu=np.ones(4))
        self.xl = np.array([0.0, 0.0, 0.0, 0.0])
        self.xu = np.array([1.0, 1.0, 1.0, 1.0])
        self.target = moo_args.get('kpi_calculation').get('kpis')
        self.sim_args = sim_args

    def _evaluate(self, x, out, *args, **kwargs):
        # compute the simulations
        self.sim_args['simulation_setup']['input_configuration']['parameter_values'] = x
        results = sim_env_apis_wrapper(**self.sim_args, return_results=True)
        out['F'] = np.array(results).T


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
    algorithm = NSGA2(pop_size=100)

    res = minimize(
        problem=_Blackbox(sim_args, **moo_args),
        algorithm=algorithm,
        termination=('n_gen', 100),
        seed=1,
        verbose=True
    )

    if return_results:
        results = pd.DataFrame(res.F, columns=['Objective 1', 'Objective 2'])
        results['Design Variables'] = [list(x) for x in res.X]
        results['Simulation Configuration'] = [sim_args] * len(results)
        return results
