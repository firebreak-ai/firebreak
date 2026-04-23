"""Unit tests for fbk.config module - config merging and PyYAML handling."""

import pytest
import sys
from unittest.mock import patch
from io import StringIO

from fbk.config import merge_configs, load_yaml, parse_frontmatter


class TestMergeConfigs:
    """Test config merging with proper precedence and deep merge."""

    def test_merge_disjoint_configs(self):
        """Disjoint configs should be merged with all keys present."""
        result = merge_configs({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_merge_overrides_later_wins(self):
        """Later config should override earlier config."""
        result = merge_configs({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_merge_nested_dicts_deep_merge(self):
        """Nested dicts should be deep merged, not replaced."""
        result = merge_configs({"x": {"y": 1}}, {"x": {"z": 2}})
        assert result == {"x": {"y": 1, "z": 2}}

    def test_merge_three_layer_precedence(self):
        """Three-layer merge should follow correct precedence."""
        DEFAULTS = {"key": "default_value", "other": "from_defaults"}
        project = {"key": "project_value"}
        spec = {"key": "spec_value"}
        result = merge_configs(merge_configs(DEFAULTS, project), spec)
        assert result["key"] == "spec_value"
        assert result["other"] == "from_defaults"


class TestLoadYaml:
    """Test load_yaml function."""

    def test_load_yaml_nonexistent_path(self):
        """Loading from non-existent path should return empty dict."""
        result = load_yaml("/nonexistent/path/to/config.yml")
        assert result == {}


class TestParseFrontmatter:
    """Test parse_frontmatter function."""

    def test_parse_frontmatter_valid_yaml(self, tmp_path):
        """Valid YAML frontmatter should be parsed into dict."""
        spec = tmp_path / "test-spec.md"
        spec.write_text("---\nkey: value\nnested:\n  inner: data\n---\n\nBody content\n")
        result = parse_frontmatter(str(spec))
        assert isinstance(result, dict)
        assert result.get("key") == "value"
        assert result.get("nested", {}).get("inner") == "data"


class TestPyYAMLRequired:
    """Test PyYAML requirement handling."""

    def test_missing_pyyaml_exits_with_clear_error(self):
        """Importing fbk.config without PyYAML should exit with code 2."""
        # We need to patch yaml module as unimportable before importing fbk.config
        with patch.dict("sys.modules", {"yaml": None}):
            # Remove fbk.config from sys.modules if already loaded
            if "fbk.config" in sys.modules:
                del sys.modules["fbk.config"]

            # Mock the import to raise ModuleNotFoundError for yaml
            def mock_import(name, *args, **kwargs):
                if name == "yaml":
                    raise ModuleNotFoundError("No module named 'yaml'")
                return original_import(name, *args, **kwargs)

            import builtins
            original_import = builtins.__import__

            with patch("builtins.__import__", side_effect=mock_import):
                # Capture stderr
                captured_err = StringIO()
                with patch("sys.stderr", captured_err):
                    with pytest.raises(SystemExit) as exc_info:
                        # Force reimport of fbk.config
                        if "fbk.config" in sys.modules:
                            del sys.modules["fbk.config"]
                        import fbk.config

                    # Check exit code
                    assert exc_info.value.code == 2

                    # Check stderr message
                    stderr_output = captured_err.getvalue()
                    assert "PyYAML required" in stderr_output
