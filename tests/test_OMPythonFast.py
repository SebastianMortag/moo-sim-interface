import os
from typing import List

import numpy as np
import pytest
from OMPython import ModelicaSystem

from moo_sim_interface.utils.OMPythonFast import ModelicaSystemFast

skip_docker = pytest.mark.skipif(
    os.getenv('SKIP_DOCKER_TESTS') == 'true',
    reason="Skipping tests that should only run via ci in Docker"
)


@skip_docker
def test_modelica_system_double_pendulum():
    model = ModelicaSystem(
        fileName="/home/hostuser/.openmodelica/libraries/Modelica 4.0.0+maint.om/package.mo",
        modelName="Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum"
    )
    model.simulate()
    result = model.getSolutions(["damper.tau"])

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (1, 502)


@skip_docker
def test_modelica_system_fast_double_pendulum():
    model = ModelicaSystemFast(
        fileName="/home/hostuser/.openmodelica/libraries/Modelica 4.0.0+maint.om/package.mo",
        modelName="Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum"
    )
    model.simulate()
    result = model.getSolutions(["damper.tau"])

    assert result is not None
    assert isinstance(result, List)
    assert len(result) == 1
    assert len(result[0]) == 502
