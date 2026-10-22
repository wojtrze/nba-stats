"""Run with: python -m pytest dashboard"""
import json

import numpy as np
import pytest

from metrics import IDENTITY_CALIBRATION, calibrate
from models import load_calibration

SHRINK = {'a': 1.0, 'b': 0.2, 'c': -0.1, 'd': 0.0}     # trust the model 20%, Overs a bit less


def test_identity_returns_the_models_chance():
    for p, market in ((0.6, 0.5), (0.31, 0.45), (0.9, 0.52)):
        assert calibrate(p, market, 'Over', IDENTITY_CALIBRATION) == pytest.approx(p)
    assert calibrate(0.6, 0.5, 'Over') == pytest.approx(0.6)          # no coefficients = identity
    assert np.isnan(calibrate(np.nan, 0.5, 'Over', SHRINK))


def test_shrinks_toward_the_market_and_keeps_the_order():
    p = calibrate(0.70, 0.50, 'Under', SHRINK)
    assert 0.5 < p < 0.55                                              # 20% of the model's opinion
    low, mid, high = (calibrate(x, 0.5, 'Under', SHRINK) for x in (0.55, 0.62, 0.70))
    assert low < mid < high                                            # the 95% range stays ordered
    assert calibrate(0.6, 0.5, 'Over', SHRINK) < calibrate(0.6, 0.5, 'Under', SHRINK)   # the Over bias
    assert calibrate(0.6, np.nan, 'Under', SHRINK) == pytest.approx(calibrate(0.6, 0.5, 'Under', SHRINK))


def test_load_calibration(tmp_path):
    assert load_calibration(str(tmp_path / 'missing.json')) == IDENTITY_CALIBRATION
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps({'coefficients': SHRINK}))
    assert load_calibration(str(path)) == SHRINK
