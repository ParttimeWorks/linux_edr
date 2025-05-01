import unittest
import os
import tempfile
import time
from linux_edr.config import Config


class TestConfig(unittest.TestCase):

    def test_config_loading(self):
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[DEFAULT]
trace_path = /test/trace_pipe
report_interval = 30
debug = true

[OPENAI]
api_key = test_key
            """)
            config_path = f.name

        try:
            # Load the config
            config = Config(config_path)
            
            # Test basic values
            self.assertEqual(config.get("DEFAULT", "trace_path"), "/test/trace_pipe")
            self.assertEqual(config.get("DEFAULT", "report_interval", 30), 30)
            self.assertTrue(config.get("DEFAULT", "debug", True))
            self.assertEqual(config.get("OPENAI", "api_key"), "test_key")
            
            # Test fallback values
            self.assertEqual(config.get("DEFAULT", "nonexistent", "fallback"), "fallback")
            self.assertEqual(config.get("NONEXISTENT", "option", 123), 123)
            
            # Test as_dict method
            config_dict = config.as_dict()
            self.assertIn("DEFAULT", config_dict)
            self.assertIn("OPENAI", config_dict)
            self.assertEqual(config_dict["DEFAULT"]["trace_path"], "/test/trace_pipe")
            
        finally:
            # Clean up the temporary file
            os.unlink(config_path)
    
    def test_boolean_conversion(self):
        # Create a temporary config file with boolean values
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[TEST]
true_value = true
false_value = false
yes_value = yes
no_value = no
on_value = on
off_value = off
one_value = 1
zero_value = 0
            """)
            config_path = f.name

        try:
            # Load the config
            config = Config(config_path)
            
            # Test boolean conversion for various formats
            self.assertTrue(config.get("TEST", "true_value", False))
            self.assertFalse(config.get("TEST", "false_value", True))
            self.assertTrue(config.get("TEST", "yes_value", False))
            self.assertFalse(config.get("TEST", "no_value", True))
            self.assertTrue(config.get("TEST", "on_value", False))
            self.assertFalse(config.get("TEST", "off_value", True))
            self.assertTrue(config.get("TEST", "one_value", False))
            self.assertFalse(config.get("TEST", "zero_value", True))
            
        finally:
            # Clean up the temporary file
            os.unlink(config_path)
    
    def test_integer_conversion(self):
        # Create a temporary config file with integer values
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[TEST]
int_value = 42
float_string = 3.14
invalid_int = abc
empty_value = 
            """)
            config_path = f.name

        try:
            # Load the config
            config = Config(config_path)
            
            # Test integer conversion
            self.assertEqual(config.get("TEST", "int_value", 0), 42)
            
            # Test float conversion
            self.assertEqual(config.get("TEST", "float_string", 0.0), 3.14)
            self.assertEqual(config.get("TEST", "float_string", 1.0), 3.14)
            
            # Test invalid integer - should use fallback
            self.assertEqual(config.get("TEST", "invalid_int", 99), 99)
            
            # Test empty value - should use fallback
            self.assertEqual(config.get("TEST", "empty_value", "default"), "default")
            
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_float_conversion(self):
        # Create a temporary config file with float values
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[TEST]
float_value = 3.14
invalid_float = xyz
            """)
            config_path = f.name

        try:
            # Load the config
            config = Config(config_path)
            
            # Test float conversion
            self.assertEqual(config.get("TEST", "float_value", 1.0), 3.14)
            
            # Test invalid float - should use fallback
            self.assertEqual(config.get("TEST", "invalid_float", 2.5), 2.5)
            
        finally:
            # Clean up the temporary file
            os.unlink(config_path)

    def test_get_section(self):
        # Create a temporary config file with multiple sections
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[DEFAULT]
trace_path = /test/trace_pipe

[SECTION1]
key1 = value1
key2 = value2

[SECTION2]
key3 = value3
            """)
            config_path = f.name
        
        try:
            config = Config(config_path)
            
            # Test getting entire sections
            section1 = config.get_section("SECTION1")
            self.assertIn("key1", section1)
            self.assertIn("key2", section1)
            self.assertEqual(section1["key1"], "value1")
            self.assertEqual(section1["key2"], "value2")
            
            # Test getting nonexistent section
            empty_section = config.get_section("NONEXISTENT")
            self.assertEqual(empty_section, {})
            
        finally:
            os.unlink(config_path)

    def test_config_not_found(self):
        # Test with a nonexistent config file - use a unique path to ensure it doesn't exist
        nonexistent_path = "/tmp/nonexistent_config_file_for_test_" + str(time.time()) + ".ini"
        
        # The constructor doesn't fail - it uses default path when not found
        config = Config(nonexistent_path)
        
        # FileNotFoundError is raised when load() is called
        # The path in load() may use a default package path, not our nonexistent_path
        # Let's just verify that loading fails with FileNotFoundError when path doesn't exist
        try:
            # Force a reload of an invalid config path
            config.config_path = nonexistent_path  # Set path directly to our nonexistent path
            with self.assertRaises(FileNotFoundError):
                config.load()
        except Exception as e:
            self.fail(f"Expected FileNotFoundError but got {type(e).__name__}: {e}")

    def test_reports_section(self):
        # Create a temporary config file with a REPORTS section
        with tempfile.NamedTemporaryFile(delete=False, mode='w') as f:
            f.write("""
[DEFAULT]
trace_path = /test/trace_pipe

[REPORTS]
reports_dir = /tmp/edr_reports
""")
            config_path = f.name
        try:
            config = Config(config_path)
            self.assertEqual(config.get("REPORTS", "reports_dir"), "/tmp/edr_reports")
        finally:
            os.unlink(config_path)


if __name__ == "__main__":
    unittest.main() 