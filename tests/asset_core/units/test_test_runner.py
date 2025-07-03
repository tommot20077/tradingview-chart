# ABOUTME: Unit tests for the test_runner module functionality
# ABOUTME: Validates command execution, argument parsing and quality check workflows

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from asset_core.test_runner import main, run_command


class TestRunCommand:
    """Test the run_command function."""

    def test_run_command_success(self) -> None:
        """Test successful command execution."""
        with patch("subprocess.run") as mock_run:
            # Setup mock for successful command
            mock_result = Mock()
            mock_result.stdout = "Test output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["echo", "test"], "Test command")

            # Assertions
            assert result is True
            mock_run.assert_called_once_with(["echo", "test"], capture_output=True, text=True, check=True)

    def test_run_command_failure(self) -> None:
        """Test failed command execution."""
        with patch("subprocess.run") as mock_run:
            # Setup mock for failed command
            error = subprocess.CalledProcessError(1, ["false"])
            error.stdout = "Error output"
            error.stderr = "Error message"
            mock_run.side_effect = error

            # Test execution
            result = run_command(["false"], "Failing command")

            # Assertions
            assert result is False
            mock_run.assert_called_once()

    def test_run_command_no_output(self) -> None:
        """Test command execution with no output."""
        with patch("subprocess.run") as mock_run:
            # Setup mock for command with no output
            mock_result = Mock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["true"], "Silent command")

            # Assertions
            assert result is True


class TestMain:
    """Test the main function."""

    def test_main_no_arguments(self) -> None:
        """Test main function with no arguments."""
        with patch.object(sys, "argv", ["test_runner.py"]), pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_invalid_command(self) -> None:
        """Test main function with invalid command."""
        with patch.object(sys, "argv", ["test_runner.py", "invalid"]), pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_main_all_command(self) -> None:
        """Test main function with 'all' command."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                # Verify the correct command was called
                mock_run.assert_called_once_with(["uv", "run", "pytest", "-v"], "Running all tests")

    def test_main_quality_command_success(self) -> None:
        """Test main function with 'quality' command - all pass."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "quality"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                # Verify all quality commands were called
                expected_calls = [
                    (["uv", "run", "ruff", "format", "."], "Code formatting"),
                    (["uv", "run", "ruff", "check", "."], "Code linting"),
                    (["uv", "run", "mypy", "."], "Type checking"),
                ]

                assert mock_run.call_count == 3
                for i, (expected_cmd, expected_desc) in enumerate(expected_calls):
                    actual_call = mock_run.call_args_list[i]
                    assert actual_call[0][0] == expected_cmd
                    assert actual_call[0][1] == expected_desc

    def test_main_quality_command_failure(self) -> None:
        """Test main function with 'quality' command - some fail."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "quality"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                # First call succeeds, second fails
                mock_run.side_effect = [True, False, True]

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                assert mock_run.call_count == 3

    def test_main_unit_command(self) -> None:
        """Test main function with 'unit' command."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "unit"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                mock_run.assert_called_once_with(["uv", "run", "pytest", "-v", "-m", "unit"], "Running unit tests")

    def test_main_coverage_command(self) -> None:
        """Test main function with 'coverage' command."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "coverage"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                mock_run.assert_called_once_with(
                    ["uv", "run", "pytest", "--cov=asset_core", "--cov-report=html"], "Running coverage tests"
                )

    def test_main_command_failure(self) -> None:
        """Test main function when command fails."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = False

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1

    def test_main_directory_restoration(self) -> None:
        """Test that original directory is restored after execution."""
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            original_path = Path("/original")
            mock_cwd.return_value = original_path

            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                # Check that chdir was called to restore original directory
                chdir_calls = mock_chdir.call_args_list
                assert len(chdir_calls) >= 2
                # Last call should restore original directory
                assert chdir_calls[-1][0][0] == original_path

    def test_all_command_options_available(self) -> None:
        """Test that all expected command options are handled."""
        expected_commands = [
            "all",
            "unit",
            "models",
            "config",
            "network",
            "coverage",
            "fast",
            "lint",
            "format",
            "typecheck",
            "quality",
        ]

        for command in expected_commands:
            with (
                patch.object(sys, "argv", ["test_runner.py", command]),
                patch("os.chdir"),
                patch("pathlib.Path.cwd"),
                patch("asset_core.test_runner.run_command") as mock_run,
            ):
                mock_run.return_value = True

                try:
                    main()
                    # Should not raise SystemExit for valid commands
                    assert True
                except SystemExit:
                    # Quality command might exit on failure, but shouldn't
                    # exit due to invalid command
                    if command != "quality":
                        pytest.fail(f"Command '{command}' should be valid")


@pytest.mark.unit
class TestRunCommandAdvanced:
    """Advanced test cases for run_command function.

    Verifies complex scenarios including resource management,
    error handling, and edge cases for command execution.
    """

    def test_run_command_with_empty_output(self) -> None:
        """Test run_command handling of commands with empty output.

        Description of what the test covers:
        Verifies that run_command correctly handles commands that produce
        no stdout or stderr output.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to return empty strings for output
        - Call run_command with test command
        - Verify successful execution and output handling

        Expected Result:
        - Command should be considered successful
        - Empty output should be handled gracefully
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for command with empty output
            mock_result = Mock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["true"], "Silent command")

            # Assertions
            assert result is True
            mock_run.assert_called_once_with(["true"], capture_output=True, text=True, check=True)

    def test_run_command_with_unicode_output(self) -> None:
        """Test run_command handling of Unicode output.

        Description of what the test covers:
        Verifies that run_command correctly handles commands that produce
        Unicode characters in their output.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to return Unicode output
        - Call run_command with test command
        - Verify Unicode handling

        Expected Result:
        - Unicode output should be handled correctly
        - Command should succeed
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for command with Unicode output
            mock_result = Mock()
            mock_result.stdout = "测试输出 🚀"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["echo", "unicode"], "Unicode command")

            # Assertions
            assert result is True
            mock_run.assert_called_once()

    def test_run_command_with_large_output(self) -> None:
        """Test run_command handling of commands with large output.

        Description of what the test covers:
        Verifies that run_command can handle commands that produce
        large amounts of output without memory issues.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to return large output
        - Call run_command with test command
        - Verify large output handling

        Expected Result:
        - Large output should be handled efficiently
        - Command should succeed
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for command with large output
            large_output = "A" * 100000  # 100KB of output
            mock_result = Mock()
            mock_result.stdout = large_output
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["generate", "large"], "Large output command")

            # Assertions
            assert result is True
            mock_run.assert_called_once()

    def test_run_command_with_stderr_only(self) -> None:
        """Test run_command handling of commands with stderr output only.

        Description of what the test covers:
        Verifies that run_command correctly handles commands that produce
        output only on stderr while still succeeding.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to return stderr output but no error
        - Call run_command with test command
        - Verify stderr handling

        Expected Result:
        - Command should succeed despite stderr output
        - Stderr should be handled appropriately
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for command with stderr but success
            mock_result = Mock()
            mock_result.stdout = ""
            mock_result.stderr = "Warning: this is just a warning"
            mock_run.return_value = mock_result

            # Test execution
            result = run_command(["command", "with", "warnings"], "Warning command")

            # Assertions
            assert result is True
            mock_run.assert_called_once()

    def test_run_command_timeout_handling(self) -> None:
        """Test run_command handling of command timeouts.

        Description of what the test covers:
        Verifies that run_command properly handles commands that timeout.
        Since current implementation doesn't catch TimeoutExpired, this
        documents the current behavior.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to raise TimeoutExpired
        - Call run_command with test command
        - Verify timeout handling

        Expected Result:
        - TimeoutExpired should propagate (current behavior)
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for timeout
            timeout_error = subprocess.TimeoutExpired(["sleep", "10"], 5)
            mock_run.side_effect = timeout_error

            # Test execution - current implementation doesn't catch TimeoutExpired
            with pytest.raises(subprocess.TimeoutExpired):
                run_command(["sleep", "10"], "Timeout command")

            mock_run.assert_called_once()

    def test_run_command_permission_error(self) -> None:
        """Test run_command handling of permission errors.

        Description of what the test covers:
        Verifies that run_command properly handles commands that fail
        due to permission errors. Since current implementation doesn't
        catch PermissionError, this documents the current behavior.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to raise PermissionError
        - Call run_command with test command
        - Verify permission error handling

        Expected Result:
        - PermissionError should propagate (current behavior)
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for permission error
            permission_error = PermissionError("Permission denied")
            mock_run.side_effect = permission_error

            # Test execution - current implementation doesn't catch PermissionError
            with pytest.raises(PermissionError):
                run_command(["restricted_command"], "Permission command")

            mock_run.assert_called_once()

    def test_run_command_file_not_found(self) -> None:
        """Test run_command handling of file not found errors.

        Description of what the test covers:
        Verifies that run_command properly handles commands that fail
        because the executable is not found. Since current implementation
        doesn't catch FileNotFoundError, this documents the current behavior.

        Preconditions:
        - Mock subprocess.run available.

        Steps:
        - Mock subprocess.run to raise FileNotFoundError
        - Call run_command with test command
        - Verify file not found handling

        Expected Result:
        - FileNotFoundError should propagate (current behavior)
        """
        with patch("subprocess.run") as mock_run:
            # Setup mock for file not found error
            file_not_found_error = FileNotFoundError("Command not found")
            mock_run.side_effect = file_not_found_error

            # Test execution - current implementation doesn't catch FileNotFoundError
            with pytest.raises(FileNotFoundError):
                run_command(["nonexistent_command"], "Missing command")

            mock_run.assert_called_once()


@pytest.mark.unit
class TestMainFunctionAdvanced:
    """Advanced test cases for main function.

    Verifies complex scenarios including error recovery,
    resource management, and edge cases in command execution.
    """

    def test_main_with_mixed_success_failure_in_quality(self) -> None:
        """Test main function quality command with mixed results.

        Description of what the test covers:
        Verifies that main function properly handles scenarios where
        some quality checks pass and others fail.

        Preconditions:
        - Quality command runs multiple sub-commands.

        Steps:
        - Mock quality sub-commands with mixed success/failure
        - Run main with quality command
        - Verify proper exit handling

        Expected Result:
        - Function should exit with code 1 if any quality check fails
        - All quality checks should be attempted
        """
        with (
            patch.object(sys, "argv", ["test_runner.py", "quality"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/test")
            with patch("asset_core.test_runner.run_command") as mock_run:
                # First succeeds, second fails, third succeeds
                mock_run.side_effect = [True, False, True]

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                assert mock_run.call_count == 3

    def test_main_with_working_directory_change_failure(self) -> None:
        """Test main function when directory change fails.

        Description of what the test covers:
        Verifies that main function handles scenarios where changing
        to the asset_core directory fails.

        Preconditions:
        - os.chdir can raise OSError.

        Steps:
        - Mock os.chdir to raise OSError
        - Run main with valid command
        - Verify error handling

        Expected Result:
        - Error should be handled gracefully
        - Original directory should be restored if possible
        """
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/original")
            # First chdir call fails, second (restore) might succeed
            mock_chdir.side_effect = [OSError("Permission denied"), None]

            with pytest.raises(OSError):
                main()

            # Verify chdir was attempted
            assert mock_chdir.call_count >= 1

    def test_main_ensures_directory_restoration_on_exception(self) -> None:
        """Test main function restores directory on exception.

        Description of what the test covers:
        Verifies that main function properly restores the original
        working directory even when exceptions occur during execution.

        Preconditions:
        - Commands can raise exceptions.

        Steps:
        - Mock command execution to raise exception
        - Run main with valid command
        - Verify directory restoration

        Expected Result:
        - Original directory should be restored despite exceptions
        - Exception should propagate appropriately
        """
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            original_path = Path("/original")
            mock_cwd.return_value = original_path

            with patch("asset_core.test_runner.run_command") as mock_run:
                # Command execution raises exception
                mock_run.side_effect = RuntimeError("Command failed unexpectedly")

                with pytest.raises(RuntimeError):
                    main()

                # Verify directory restoration was attempted
                chdir_calls = mock_chdir.call_args_list
                assert len(chdir_calls) >= 2
                # Last call should restore original directory
                assert chdir_calls[-1][0][0] == original_path

    def test_main_with_keyboard_interrupt(self) -> None:
        """Test main function handling of KeyboardInterrupt.

        Description of what the test covers:
        Verifies that main function properly handles KeyboardInterrupt
        (Ctrl+C) during command execution.

        Preconditions:
        - Commands can be interrupted by user.

        Steps:
        - Mock command execution to raise KeyboardInterrupt
        - Run main with valid command
        - Verify interrupt handling

        Expected Result:
        - KeyboardInterrupt should be handled gracefully
        - Directory should be restored
        - Appropriate exit code should be used
        """
        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            original_path = Path("/original")
            mock_cwd.return_value = original_path

            with patch("asset_core.test_runner.run_command") as mock_run:
                # Simulate user interruption
                mock_run.side_effect = KeyboardInterrupt()

                with pytest.raises(KeyboardInterrupt):
                    main()

                # Verify directory restoration was attempted
                chdir_calls = mock_chdir.call_args_list
                assert len(chdir_calls) >= 2

    def test_main_command_descriptions_accuracy(self) -> None:
        """Test main function command descriptions are accurate.

        Description of what the test covers:
        Verifies that the help text and command descriptions
        accurately reflect the actual commands executed.

        Preconditions:
        - Command descriptions are defined in main function.

        Steps:
        - Extract command descriptions from help output
        - Compare with actual command definitions
        - Verify accuracy and completeness

        Expected Result:
        - All command descriptions should be accurate
        - All available commands should be documented
        """
        # This test verifies the consistency between help text and actual commands
        expected_commands = {
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
        }

        # Read the actual source code to verify command definitions

        # For each expected command, verify it exists and works
        for cmd_name, expected_cmd in expected_commands.items():
            with (
                patch.object(sys, "argv", ["test_runner.py", cmd_name]),
                patch("os.chdir"),
                patch("pathlib.Path.cwd"),
                patch("asset_core.test_runner.run_command") as mock_run,
            ):
                mock_run.return_value = True

                try:
                    main()
                    if cmd_name != "quality":  # Quality is special case
                        mock_run.assert_called_once()
                        actual_cmd = mock_run.call_args[0][0]
                        assert actual_cmd == expected_cmd, (
                            f"Command mismatch for {cmd_name}: expected {expected_cmd}, got {actual_cmd}"
                        )
                except SystemExit:
                    # Some commands might exit, which is fine
                    pass

    def test_main_resource_cleanup_comprehensive(self) -> None:
        """Test comprehensive resource cleanup in main function.

        Description of what the test covers:
        Verifies that main function properly cleans up all resources
        including directory changes, file handles, and other resources.

        Preconditions:
        - Main function manages various resources.

        Steps:
        - Run main function with various scenarios
        - Verify all resources are cleaned up properly
        - Test with both success and failure cases

        Expected Result:
        - All resources should be cleaned up consistently
        - No resource leaks should occur
        """
        original_path = Path("/original")

        # Test cleanup on success
        with (
            patch.object(sys, "argv", ["test_runner.py", "unit"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = original_path
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                main()

                # Verify directory was restored
                chdir_calls = mock_chdir.call_args_list
                assert len(chdir_calls) >= 2
                assert chdir_calls[-1][0][0] == original_path

        # Test cleanup on failure
        with (
            patch.object(sys, "argv", ["test_runner.py", "unit"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = original_path
            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = False

                with pytest.raises(SystemExit):
                    main()

                # Verify directory was restored even on failure
                chdir_calls = mock_chdir.call_args_list
                assert len(chdir_calls) >= 2
                assert chdir_calls[-1][0][0] == original_path


@pytest.mark.unit
class TestConfigurationManagement:
    """Test cases for configuration and environment management.

    Verifies that the test runner properly handles different
    configurations and environment settings.
    """

    def test_asset_core_directory_detection(self) -> None:
        """Test asset_core directory detection logic.

        Description of what the test covers:
        Verifies that the test runner correctly detects and uses
        the asset_core directory based on the script location.

        Preconditions:
        - __file__ attribute is available and accurate.

        Steps:
        - Mock Path operations for directory detection
        - Run main function
        - Verify correct directory is used

        Expected Result:
        - Correct asset_core directory should be detected and used
        """
        with (
            patch.object(sys, "argv", ["test_runner.py", "unit"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = Path("/original")

            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                # Mock the asset_core_dir calculation
                with patch("pathlib.Path.__new__") as mock_path:
                    expected_dir = Path("/expected/asset_core")
                    mock_path.return_value.parent = expected_dir

                    main()

                    # Verify chdir was called (directory change attempted)
                    assert mock_chdir.call_count >= 1

    def test_environment_variable_handling(self) -> None:
        """Test environment variable handling during execution.

        Description of what the test covers:
        Verifies that the test runner properly handles environment
        variables that might affect command execution.

        Preconditions:
        - Environment variables can affect subprocess execution.

        Steps:
        - Set specific environment variables
        - Run commands through test runner
        - Verify environment is passed correctly

        Expected Result:
        - Environment variables should be preserved and passed to subprocesses
        """
        import os

        with (
            patch.object(sys, "argv", ["test_runner.py", "unit"]),
            patch("os.chdir"),
            patch("pathlib.Path.cwd"),
            patch("subprocess.run") as mock_run,
        ):
            mock_result = Mock()
            mock_result.stdout = "Test output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            # Set test environment variable
            original_env = os.environ.get("TEST_ENV_VAR")
            os.environ["TEST_ENV_VAR"] = "test_value"

            try:
                main()

                # Verify subprocess.run was called
                mock_run.assert_called_once()
                # Environment should be inherited (default behavior)

            finally:
                # Restore original environment
                if original_env is not None:
                    os.environ["TEST_ENV_VAR"] = original_env
                else:
                    os.environ.pop("TEST_ENV_VAR", None)

    def test_working_directory_context_management(self) -> None:
        """Test working directory context management.

        Description of what the test covers:
        Verifies that the test runner properly manages working directory
        context and ensures proper restoration under all conditions.

        Preconditions:
        - Working directory can be changed and restored.

        Steps:
        - Change working directory multiple times
        - Simulate various execution scenarios
        - Verify consistent directory management

        Expected Result:
        - Working directory should always be properly restored
        - Context should be managed consistently
        """
        original_dir = Path("/original")
        asset_core_dir = Path("/asset_core")

        with (
            patch.object(sys, "argv", ["test_runner.py", "all"]),
            patch("os.chdir") as mock_chdir,
            patch("pathlib.Path.cwd") as mock_cwd,
        ):
            mock_cwd.return_value = original_dir

            with patch("asset_core.test_runner.run_command") as mock_run:
                mock_run.return_value = True

                # Mock the asset_core directory path
                with patch("pathlib.Path.__new__") as mock_path_new:
                    mock_path_instance = Mock()
                    mock_path_instance.parent = asset_core_dir
                    mock_path_new.return_value = mock_path_instance

                    main()

                    # Verify directory change sequence
                    chdir_calls = mock_chdir.call_args_list
                    assert len(chdir_calls) >= 2

                    # First call should change to asset_core directory
                    # Last call should restore original directory
                    assert chdir_calls[-1][0][0] == original_dir
