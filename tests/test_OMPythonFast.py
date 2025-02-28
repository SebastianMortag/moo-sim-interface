import os

import pytest
from OMPython import ModelicaSystem

skip_online = pytest.mark.skipif(
    os.getenv('SKIP_ONLINE_TESTS') == 'true',
    reason="Skipping tests that should only run online"
)


@skip_online
def test_modelica_system_double_pendulum():
    model = ModelicaSystem(
        fileName="/root/.openmodelica/libraries/Modelica 4.0.0+maint.om/package.mo",
        modelName="Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum"
    )
    model.simulate()
    result = model.getSolutions(["damper.tau"])

    assert result is not None
    assert result.shape == (1, 502)


@skip_online
def test_modelica_system_fast_double_pendulum():
    model = ModelicaSystem(
        fileName="/root/.openmodelica/libraries/Modelica 4.0.0+maint.om/package.mo",
        modelName="Modelica.Mechanics.MultiBody.Examples.Elementary.DoublePendulum"
    )
    model.simulate()
    result = model.getSolutions(["damper.tau"])

    assert result is not None
    assert result.shape == (1, 502)
