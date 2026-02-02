#!/usr/bin/env python3.12
"""
Test runner for the voice assistant project.

This script provides a unified way to run tests across all services.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests():
    """Run all tests in the project."""
    print("Running tests for Voice Assistant project...")

    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    # Run pytest with configuration from pyproject.toml
    cmd = [sys.executable, "-m", "pytest", "src/", "-v"]

    print(f"Executing: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Tests failed!")
        sys.exit(result.returncode)
    else:
        print("All tests passed!")


def run_tests_with_coverage():
    """Run tests with coverage report."""
    print("Running tests with coverage...")

    # Change to project root
    project_root = Path(__file__).parent
    os.chdir(project_root)

    cmd = [
        sys.executable, "-m", "pytest",
        "src/",
        "--cov=src",
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "-v"
    ]

    print(f"Executing: {' '.join(cmd)}")

    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Tests failed!")
        sys.exit(result.returncode)
    else:
        print("All tests passed! Coverage report generated in htmlcov/ directory.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--coverage":
        run_tests_with_coverage()
    else:
        run_tests()