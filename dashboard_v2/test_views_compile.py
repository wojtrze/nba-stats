"""The page scripts aren't imported by any other test: at least check they compile. Run with: python -m pytest dashboard_v2"""
import pathlib
import py_compile

import pytest

VIEWS = sorted((pathlib.Path(__file__).parent / 'views').glob('*.py'))


@pytest.mark.parametrize('path', VIEWS, ids=lambda p: p.name)
def test_view_compiles(path):
    py_compile.compile(str(path), doraise=True)
