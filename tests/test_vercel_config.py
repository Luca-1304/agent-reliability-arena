import json
from pathlib import Path


def test_repository_root_vercel_config_targets_portfolio() -> None:
    config = json.loads(Path("vercel.json").read_text(encoding="utf-8"))

    assert config["framework"] is None
    assert config["buildCommand"] is None
    assert config["installCommand"] == ""
    assert config["outputDirectory"] == "web/cinematic-plus"


def test_portfolio_root_vercel_config_serves_current_directory() -> None:
    config = json.loads(
        Path("web/cinematic-plus/vercel.json").read_text(encoding="utf-8")
    )

    assert config["framework"] is None
    assert config["buildCommand"] is None
    assert config["installCommand"] == ""
    assert config["outputDirectory"] == "."
