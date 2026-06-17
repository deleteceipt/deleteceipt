"""Config loader for GDPR compliance checker operator configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class OperatorConfig:
    organization_id: str
    vertical: str
    signing_key: str          # resolved from signing_key or signing_key_env
    signing_key_id: str = ""
    ci_threshold: float = 50.0
    answers: dict = field(default_factory=dict)


def load_config(path: Path) -> OperatorConfig:
    """Load operator.yaml and resolve signing key from env if needed."""
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    # Resolve signing key: literal wins over env var reference
    signing_key = data.get("signing_key", "")
    if not signing_key:
        env_var = data.get("signing_key_env", "")
        if env_var:
            signing_key = os.environ.get(env_var, "")
    if not signing_key:
        raise ValueError(
            "No signing key found. Set 'signing_key' in the config or "
            "export the env var named by 'signing_key_env'."
        )

    return OperatorConfig(
        organization_id=data.get("organization_id", "unknown"),
        vertical=data.get("vertical", "general_saas"),
        signing_key=signing_key,
        signing_key_id=data.get("signing_key_id", ""),
        ci_threshold=float(data.get("ci_threshold", 50.0)),
        answers=data.get("answers", {}),
    )
