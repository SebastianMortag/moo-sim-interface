# moo-sim-interface

moo-sim-interface is a Python package for the simulation of Modelica-based models, either as FMUs [Functional Mock-up Units](https://fmi-standard.org/) or using the OpenModelica or Dymola Python APIs. It allows for easily configurable simulation
setup, execution and evaluation via a generic text-based interface. Its main purpose is parallelization of simulations
and parameter sweeps. Furthermore, it provides a generic interface for Multi-Objective-Optimization.

## Usage

The key idea is to provide a single configuration file in YAML format, which contains the necessary information to set up and run the simulations.
To _get started_, it is recommended to copy one of the provided examples and adjust it to your needs.

The tool can be used either as a command line tool via:

```run_sim -h``` to access the help menu and
```run_sim -f sim_config_file``` to run the simulations defined in the configuration file.

**or** as a python package by importing the module and calling the function:

```python
from moo_sim_interface.simulator_api import run_simulations
run_simulations(sim_config_file)
```

When working with relative paths, configuration files and FMU files should be located in 'configs' and 'fmus' folders within your working directory.

## Example

Here is an example of how to run a parameter sweep in parallel using a FMU model:
Download the 'configs' and 'fmus' folders containing the examples and place them within your current working directory.
Launch the simulations using the following command, which will output the results into a csv file:

```run_sim -f pv_heat_example_config.yml```

## Installation

```pip install git+https://github.com/SebastianMortag/moo-sim-interface.git```

### Requirements

- Python 3.10 or higher
- Numpy 2.2.0 or higher
- dask 2024.7.1 or higher
- PyYAML 6.0.0 or higher
- Plotly 5.15.0 or higher
- Matplotlib 3.7.0 or higher


- FMPy 0.3.22 or higher (for FMU simulations)
- OMPython 3.6.0 or higher (for OpenModelica simulations)
- Dymola 2022 or higher (for Dymola simulations)

## Hints

### OpenModelica FMU Export

**Disable LOG Messages:**

To prevent the solver CVode from printing log messages, set the Translation Flag ```--fmiFlags=none``` in
_OpenModelica->SimulationSetup->Translation Flags->Additional Translation Flags_ AND check **Save translation flags
inside model**.
Or add the Translation Flag for all Simulations via _OpenModelica->Tools->Options->Simulation->Additional Translation
Flags_.

Disable **stdout** messages from CombiTimeTable by selecting _CombiTimeTable->verboseRead:_ false

**Configure FMI Settings:**

_Tools->Options->FMI_

* Version: 2.0
* Typ: Co-Simulation
* Solver for Co-Simulation: _CVODE_
*
    - [x] Include Modelica based resources via loadResource

**Include Resources in the fmu:**

In some cases, generating the fmu file fails when adding files as input resources.
Go to _OpenModelica->Tools->Options->General->Working Directory_ and choose a short path i.e. _C:/OMEdit_

### Dymola FMU Export

**Configure FMI Settings:**

_Simulation Setup->FMI Export_

* Type: Co-simulation using Cvode
* Version: 2.0
* Options:
    - [x] Copy resources to FMU
    - [x] FMU needs no license key

Running FMUs requires access to the Runtime-Licence, this is not possible if the licence is managed by a DSLS Server. See chapter _Limitations_ in the Dymola User Manual.
In order to export FMUs with Dymola, which require no license key, your licence must allow for binary model export.

**Parameter Evaluation:**

Activate **Evaluate parameters to reduce models** in _Simulation Setup->Translation_
This leads to the output of the model being fixed since parameters become constants, but simulation time is reduced.
Can be used to simulate poorly parameterized models, since singularities at t=0 can occur when the initial values are
not set correctly. This sets the flag _Evaluate=false_ in the uses Annotations of the Modelica file.
Parameters that are evaluated (symbolically) bevor the FMU is simulated, are marked as **constant** in the FMU. Their
values con no longer be changed.
To exclude specific parameters from the evaluation, add `annotation (Evaluate=false)` to the parameter declaration.
If the declaration is in an unmodifiable submodule, propagate the parameter into a modifiable submodule and add the
annotation there.

**Maximum Simulation Run Time:**
(From Dymola User Manual 2B, p.22)

Go to _Simulation Setup->General->Max simulation run time->Per simulation_ and specify the maximum (real) time in
seconds that a simulation is allowed to run. If the simulation time exceeds this value, the simulation is aborted.

### OpenModelica Scripting API

**Disable LOG Messages:**

Various options exist to disable log messages in OpenModelica.

_Command Line Options (e.g. Compiler Flags for omc / Translation Flags in OMEdit):_
* ```--demoMode``` Disable Info messages when loading a model. Warnings, like Lexer, are still displayed
For example: ```ModelicaSystem(model_path, model_name, commandLineOptions='--demoMode')```
* ```-q``` Silent mode, purpose unknown

_Simulations Flags (C Runtime Simulation Flags):_
* ```-lv=-LOG_SUCCESS``` Disable messages like "Simulation finished successfully"
For example: ```model.simulate(simflags='-lv=-LOG_SUCCESS')```
* ```-lv=-LOG_STDOUT``` Disable all messages written to stdout
* ```-lv=-LOG_ASSERT``` Disable all assert messages of type Info
For OpenModelica v1.21 and below please use: ```-stdout``` and ```-assert```

## Planned Features
* Auto-remove OM/Dymola result files after successful simulations
* Select custom folders for OM/Dymola result files
* Run OM simulations in parallel (WiP)
* Inject LOG messages suppression into the simulation apis
* Implement safe mode for automatic simulation error handling for OM and Dymola
* Implement input and output parameter configuration using a csv file
