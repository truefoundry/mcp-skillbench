"""Resolve one isolated experiment and its filesystem inputs."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
EXPERIMENTS = ROOT / "experiments"


def load_dotenv() -> None:
    """Load KEY=VALUE pairs from the repo .env without printing values."""
    path = PROJECT / ".env"
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class Experiment:
    name: str
    directory: Path
    config: dict[str, Any]

    def path(self, key: str) -> Path:
        return (self.directory / self.config[key]).resolve()

    @property
    def questions(self) -> Path:
        return self.path("questions")

    @property
    def tools(self) -> Path:
        return self.path("tools")

    @property
    def fixtures(self) -> Path:
        return self.path("fixtures")

    @property
    def cache(self) -> Path:
        return self.path("cache")

    @property
    def runs(self) -> Path:
        return self.path("runs")

    @property
    def skill(self) -> Path:
        return (PROJECT / self.config["skill"]).resolve()


def load_experiment(name: str, *, require_enabled: bool = True) -> Experiment:
    directory = EXPERIMENTS / name
    config_path = directory / "config.json"
    if not config_path.exists():
        available = sorted(
            path.parent.name for path in EXPERIMENTS.glob("*/config.json")
        )
        raise SystemExit(
            f"Unknown experiment {name!r}; available experiments: {available}"
        )
    config = json.loads(config_path.read_text())
    if config.get("name") != name:
        raise ValueError(f"{config_path}: name must be {name!r}")
    if require_enabled and not config.get("enabled", False):
        raise SystemExit(f"Experiment {name!r} is disabled")
    return Experiment(name=name, directory=directory, config=config)
