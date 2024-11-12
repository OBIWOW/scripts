import pytest
from unittest.mock import mock_open, patch

from obiwow.data_reader_parser import parse_yaml


class TestOpenConf:
    def test_open_conf_valid_yaml(self):
        mock_yaml_content = """
        key1: value1
        key2: value2
        """
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            result = parse_yaml("dummy_path.yaml")
            assert result == {"key1": "value1", "key2": "value2"}

    def test_open_conf_yaml_syntax_error(self, capsys):
        mock_yaml_content = """
        key1: value1
        key2: value2:
        """
        with patch("builtins.open", mock_open(read_data=mock_yaml_content)):
            result = parse_yaml("dummy_path.yaml")
            captured = capsys.readouterr()
            assert result is None
            assert "Error in configuration file dummy_path.yaml" in captured.out

    def test_open_conf_non_existent_file(self):
        with patch("builtins.open", side_effect=FileNotFoundError):
            result = parse_yaml("non_existent_file.yaml")
            assert result is None


if __name__ == "__main__":
    pytest.main()
