import csv
import json
import os
import pathlib
import re
import time
from typing import Union

import plotly.graph_objects as go
from matplotlib import pyplot as plt

from moo_sim_interface.utils.recursively_ordered_dict import RecursivelyOrderedDict


def save_results_to_csv(results, sim_params, input_values, model_name):
    file_path = create_save_dir(model_name, '_results.csv')
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(sim_params.get('input_configuration').get('parameter_names') + sim_params.get(
            'output_configuration').get('parameter_names'))
        for index, result in results:
            writer.writerow([values[index] for values in input_values] + result)


def save_results_to_txt(results, sim_params, input_values, model_name):
    file_path = create_save_dir(model_name, '_results.txt')
    with open(file_path, 'w') as f:
        f.write(' '.join(sim_params.get('input_configuration').get('parameter_names')
                         + sim_params.get('output_configuration').get('parameter_names')) + '\n')
        for index, result in results:
            f.write(' '.join([str(values[index]) for values in input_values] + [str(x) for x in result]) + '\n')


def save_full_results_to_json(combined_results, model_name):
    full_results = []
    for i in range(1, len(combined_results), 2):
        full_results.extend(combined_results[i])

    file_path = create_save_dir(model_name, '_full_results.json')
    result_dict = {}
    for i, simulation_results in enumerate(full_results):
        result_dict[f'Simulation {i + 1}'] = simulation_results
    with open(file_path, 'w') as json_file:
        json.dump(result_dict, json_file, indent=2,
                  default=lambda o: o.data if isinstance(o, RecursivelyOrderedDict) else o)


def create_save_dir(model_name, file_name_suffix: str = ''):
    file_name = time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime()) + file_name_suffix
    file_path = pathlib.Path(os.getcwd()) / 'simulation_results' / model_name
    file_path.mkdir(parents=True, exist_ok=True)
    return file_path / file_name


def plot_results_matplotlib(data: list, sim_params: dict):
    x_axis_label = sim_params.get('output_configuration').get('parameter_names')[0]
    y_axis_label = sim_params.get('output_configuration').get('parameter_names')[1]
    results = [data[x][1] for x in range(len(data))]

    plt.figure(figsize=(12, 8), dpi=128)
    plt.scatter(*zip(*results))
    plt.xlabel(x_axis_label)
    plt.ylabel(y_axis_label)
    plt.show()


def plot_results_plotly(data: list, input_values, sim_params: dict):
    input_names = sim_params.get('input_configuration').get('parameter_names')
    x_axis_label = sim_params.get('output_configuration').get('parameter_names')[0]
    y_axis_label = sim_params.get('output_configuration').get('parameter_names')[1]

    hover_text_values = [[input_value[data[x][0]] for input_value in input_values] for x in range(len(data))]
    hover_text = ['<br>'.join([f'{input_names[i]}: {hover_text_values[x][i]}' for i in range(len(input_names))]) for x
                  in range(len(hover_text_values))]
    results = [data[x][1] for x in range(len(data))]

    fig = go.Figure(
        data=go.Scatter(x=[x[0] for x in results], y=[x[1] for x in results], mode='markers', text=hover_text))
    fig.update_layout(title='Simulation results', xaxis_title=x_axis_label, yaxis_title=y_axis_label)
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.show()


class PostSimulationDataProcessor:
    def __init__(self, post_simulation_options: dict = None, model_parameters: list = None):
        if post_simulation_options is None:
            post_simulation_options = {}
        if model_parameters is None:
            model_parameters = []

        self.save_all_simulation_parameters = post_simulation_options.get(
            'save_all_simulation_parameters')  # TODO: Implement this functionality for other environments than FMU

        if self.save_all_simulation_parameters:
            if post_simulation_options.get('parameters_regex_filter') != 'None':
                print(f'Saving all simulation parameters '
                      f'{post_simulation_options.get("filter_mode")}d by filter: '
                      f'{post_simulation_options.get("parameters_regex_filter")}')
                self.parameters_regex_filter = re.compile(post_simulation_options.get('parameters_regex_filter'))
                self.filter_mode = post_simulation_options.get('filter_mode')

                self._pre_process_model_parameters_by_filter(model_parameters)

            else:
                print('Saving all simulation parameters')
                self._pre_process_model_parameters(model_parameters)
        else:
            self.value_references = {}

    def _pre_process_model_parameters_by_filter(self, model_parameters: list):
        filtered_value_references = {}

        if self.filter_mode == 'include':
            for parameter in model_parameters:
                if self.parameters_regex_filter.search(parameter.name):
                    filtered_value_references[parameter.name] = parameter.valueReference

        elif self.filter_mode == 'exclude':
            for parameter in model_parameters:
                if self.parameters_regex_filter.search(parameter.name) is None:
                    filtered_value_references[parameter.name] = parameter.valueReference

        self.value_references = filtered_value_references

    def _pre_process_model_parameters(self, model_parameters: list):
        value_references = {}
        for parameter in model_parameters:
            value_references[parameter.name] = parameter.valueReference

        self.value_references = value_references

    def get_value_references(self):
        return self.value_references

    def do_post_processing(self, args, input_values, combined_results, model_name, return_results: bool = False) \
            -> Union[None, list]:
        sim_params = args.get('simulation_setup')
        post_simulation_options = args.get('post_simulation_options')

        results = []
        for i in range(0, len(combined_results), 2):
            results.extend(combined_results[i])

        save_options = post_simulation_options.get('save_results_options')
        if save_options == 'csv':
            save_results_to_csv(results, sim_params, input_values, model_name)
        elif save_options == 'txt':
            save_results_to_txt(results, sim_params, input_values, model_name)

        if post_simulation_options.get('print_results'):
            print(results)

        if self.save_all_simulation_parameters:
            save_full_results_to_json(combined_results, model_name)

        if post_simulation_options.get('plot_results'):
            if post_simulation_options.get('plot_results_lib') == 'matplotlib':
                plot_results_matplotlib(data=results, sim_params=sim_params)
            elif post_simulation_options.get('plot_results_lib') == 'plotly':
                plot_results_plotly(data=results, input_values=input_values, sim_params=sim_params)

        if return_results:
            return results
