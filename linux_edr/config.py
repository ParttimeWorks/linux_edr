import os
import logging
import configparser
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, cast, TypeVar, overload

logger = logging.getLogger(__name__)

# Default config file paths to try in order
DEFAULT_CONFIG_PATHS: List[str] = [
    "./config.ini",
    "~/.config/linux_edr/config.ini",
    "/etc/linux_edr/config.ini",
]

# Type variable for generic return types
T = TypeVar("T")


class Config:
    """
    Configuration loader and manager for Linux EDR.

    This class handles loading configuration from .ini files and provides
    methods to access configuration values with appropriate type conversion.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file (optional)
        """
        self.config = configparser.ConfigParser()
        self.config_path = self._find_config(config_path)
        logger.debug(f"Using config file: {self.config_path}")
        self.load()

    def _find_config(self, config_path: Optional[str] = None) -> str:
        """Find configuration file in default locations or use specified path."""
        # Use specified path if it exists
        if config_path and os.path.exists(config_path):
            return config_path

        # Try default locations
        for path in DEFAULT_CONFIG_PATHS:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                return expanded_path

        # If no config is found, use the package default
        package_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(package_dir, "config.ini")

    def load(self) -> None:
        """Load configuration from file."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found: {self.config_path}")
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        try:
            self.config.read(self.config_path)
            logger.debug(f"Loaded configuration from {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading config from {self.config_path}: {e}")
            raise

    @overload
    def get(self, section: str, option: str, fallback: str) -> str: ...

    @overload
    def get(self, section: str, option: str, fallback: int) -> int: ...

    @overload
    def get(self, section: str, option: str, fallback: bool) -> bool: ...

    @overload
    def get(self, section: str, option: str, fallback: None = None) -> Optional[str]: ...

    def get(self, section: str, option: str, fallback: Any = None) -> Any:
        """
        Get a configuration value with type conversion.

        Args:
            section: Section name in the config file
            option: Option name in the section
            fallback: Default value if option is not found

        Returns:
            The configuration value converted to the appropriate type
        """
        if section not in self.config:
            return fallback

        if option not in self.config[section]:
            return fallback

        value = self.config[section][option]

        # Empty string handling
        if value.strip() == "":
            return fallback

        # Handle boolean values
        if isinstance(fallback, bool) or value.lower() in (
            "true",
            "false",
            "yes",
            "no",
            "on",
            "off",
        ):
            return value.lower() in ("true", "yes", "on", "1")

        # Handle integer values
        if isinstance(fallback, int):
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Failed to convert {value} to int, using fallback {fallback}")
                return fallback

        # Handle float values
        if isinstance(fallback, float):
            try:
                return float(value)
            except ValueError:
                logger.warning(f"Failed to convert {value} to float, using fallback {fallback}")
                return fallback

        # Return as string by default
        return value

    def as_dict(self) -> Dict[str, Dict[str, Any]]:
        """
        Convert the configuration to a nested dictionary.

        Returns:
            Dictionary representation of the configuration
        """
        result: Dict[str, Dict[str, Any]] = {}

        # Process DEFAULT section first
        if "DEFAULT" in self.config:
            result["DEFAULT"] = dict(self.config["DEFAULT"])

        # Process all non-DEFAULT sections
        for section in self.config.sections():
            result[section] = dict(self.config[section])

        return result

    def get_section(self, section: str) -> Dict[str, str]:
        """
        Get an entire section as a dictionary.

        Args:
            section: Section name to retrieve

        Returns:
            Dictionary of options and values in the section
        """
        if section in self.config:
            return dict(self.config[section])
        return {}
