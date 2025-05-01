import unittest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from linux_edr.cli import app


class TestCLI(unittest.TestCase):
    """Tests for the CLI interface module."""

    def setUp(self):
        self.runner = CliRunner()

    @patch('linux_edr.cli.LinuxEDRApp')
    def test_run_command_default(self, mock_app_class):
        """Test 'run' command with default arguments."""
        # Setup mock
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance
        
        # Run the command
        result = self.runner.invoke(app, ["run"])
        
        # Verify the command ran successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify LinuxEDRApp was initialized with default parameters
        mock_app_class.assert_called_once_with(
            config_path=None,
            interval=None,
            output_file=None,
            debug=None
        )
        
        # Verify the app's run method was called
        mock_app_instance.run.assert_called_once()

    @patch('linux_edr.cli.LinuxEDRApp')
    def test_run_command_with_options(self, mock_app_class):
        """Test 'run' command with all options specified."""
        # Setup mock
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance
        
        # Run the command with options
        result = self.runner.invoke(app, [
            "run",
            "--config", "custom_config.ini",
            "--interval", "30",
            "--output", "output.json",
            "--debug"
        ])
        
        # Verify the command ran successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify LinuxEDRApp was initialized with the provided parameters
        mock_app_class.assert_called_once_with(
            config_path="custom_config.ini",
            interval=30,
            output_file="output.json",
            debug=True
        )
        
        # Verify the app's run method was called
        mock_app_instance.run.assert_called_once()

    @patch('linux_edr.config.Config')
    @patch('json.dumps')
    @patch('typer.echo')
    def test_show_config_command(self, mock_echo, mock_dumps, mock_config_class):
        """Test 'show-config' command."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_class.return_value = mock_config_instance
        
        mock_config_dict = {"DEFAULT": {"key": "value"}}
        mock_config_instance.as_dict.return_value = mock_config_dict
        
        mock_dumps.return_value = '{"DEFAULT": {"key": "value"}}'
        
        # Run the command
        result = self.runner.invoke(app, ["show-config"])
        
        # Verify the command ran successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify Config was initialized
        mock_config_class.assert_called_once_with(None)
        
        # Verify as_dict method was called
        mock_config_instance.as_dict.assert_called_once()
        
        # Verify json.dumps was called with the config dict
        mock_dumps.assert_called_once_with(mock_config_dict, indent=2)
        
        # Verify the result was echoed
        mock_echo.assert_called_once_with('{"DEFAULT": {"key": "value"}}')

    @patch('linux_edr.config.Config')
    def test_show_config_with_custom_config(self, mock_config_class):
        """Test 'show-config' command with custom config file."""
        # Setup mock
        mock_config_instance = MagicMock()
        mock_config_class.return_value = mock_config_instance
        mock_config_instance.as_dict.return_value = {}
        
        # Run the command with custom config
        result = self.runner.invoke(app, ["show-config", "--config", "custom_config.ini"])
        
        # Verify the command ran successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify Config was initialized with the provided config path
        mock_config_class.assert_called_once_with("custom_config.ini")


if __name__ == "__main__":
    unittest.main() 