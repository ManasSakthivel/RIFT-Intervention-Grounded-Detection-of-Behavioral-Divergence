import sys
import os

# Make both `rift` and `src.rift` importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.dirname(__file__))
