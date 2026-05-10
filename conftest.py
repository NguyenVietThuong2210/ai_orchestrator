"""
Pytest configuration — add project root to sys.path so imports work
without installing the package.
"""
import sys
import pathlib

# Ensure project root is on the path
sys.path.insert(0, str(pathlib.Path(__file__).parent))
