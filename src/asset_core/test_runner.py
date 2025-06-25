#!/usr/bin/env python3
"""Test runner script for asset_core."""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}")
    print(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False


def main() -> None:
    """Main test runner function."""
    # Change to asset_core directory
    asset_core_dir = Path(__file__).parent
    print(f"Working in: {asset_core_dir}")

    # Available test commands
    commands = {
        "all": ["uv", "run", "pytest", "-v"],
        "unit": ["uv", "run", "pytest", "-v", "-m", "unit"],
        "models": ["uv", "run", "pytest", "-v", "-m", "models"],
        "config": ["uv", "run", "pytest", "-v", "-m", "config"],
        "network": ["uv", "run", "pytest", "-v", "-m", "network"],
        "coverage": ["uv", "run", "pytest", "--cov=asset_core", "--cov-report=html"],
        "fast": ["uv", "run", "pytest", "-v", "-m", "not slow"],
        "lint": ["uv", "run", "ruff", "check", "."],
        "format": ["uv", "run", "ruff", "format", "."],
        "typecheck": ["uv", "run", "mypy", "."],
        "quality": [],  # Special case for running all quality checks
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("Usage: python test_runner.py <command>")
        print("\nAvailable commands:")
        for cmd, desc in {
            "all": "Run all tests",
            "unit": "Run unit tests only",
            "models": "Run model tests only",
            "config": "Run config tests only",
            "network": "Run network tests only",
            "coverage": "Run tests with coverage report",
            "fast": "Run fast tests (exclude slow)",
            "lint": "Run code linting",
            "format": "Format code",
            "typecheck": "Run type checking",
            "quality": "Run all quality checks (lint + format + typecheck)",
        }.items():
            print(f"  {cmd}: {desc}")
        sys.exit(1)

    command = sys.argv[1]

    # Change to asset_core directory
    original_cwd = Path.cwd()
    import os

    try:
        os.chdir(asset_core_dir)

        if command == "quality":
            # Run all quality checks
            success = True
            success &= run_command(["uv", "run", "ruff", "format", "."], "Code formatting")
            success &= run_command(["uv", "run", "ruff", "check", "."], "Code linting")
            success &= run_command(["uv", "run", "mypy", "."], "Type checking")

            if success:
                print("\n✅ All quality checks passed!")
            else:
                print("\n❌ Some quality checks failed!")
                sys.exit(1)
        else:
            # Run the specified command
            success = run_command(commands[command], f"Running {command} tests")
            if not success:
                sys.exit(1)

    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()
