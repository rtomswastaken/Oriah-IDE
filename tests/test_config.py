import os
from oriah.config import EngineConfig

def test_engine_config_defaults():
    config = EngineConfig()
    assert config.base_url == "http://localhost:11434/v1"
    assert config.model == "qwen2.5-coder:14b"
    assert config.timeout == 60.0
    assert config.max_steps == 25
    assert os.path.isabs(config.resolved_workspace)

def test_engine_config_custom():
    config = EngineConfig(base_url="http://localhost:1234/v1", model="deepseek-coder:6.7b", timeout=30.0)
    assert config.base_url == "http://localhost:1234/v1"
    assert config.model == "deepseek-coder:6.7b"
    assert config.timeout == 30.0
