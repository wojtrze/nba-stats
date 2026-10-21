import os
import sys

# the same import paths app.py sets up: v2's core package, the old dashboard's modules and the repository root
V2 = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(V2)
sys.path[:0] = [V2, os.path.join(ROOT, 'dashboard'), ROOT]
