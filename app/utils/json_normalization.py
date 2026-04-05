import hashlib
import json
from typing import Any


def normalize_json(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            key: normalize_json(value)
            for key, value in sorted(data.items())
            if value is not None
        }

    if isinstance(data, list):
        return [normalize_json(value) for value in data]

    return data


def canonical_json(data: Any) -> str:
    normalized = normalize_json(data)
    return json.dumps(
        normalized,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def generate_fingerprint(organization_id: Any, rule_type: str, config: Any) -> str:
    canonical = canonical_json(config or {})
    raw = f"{organization_id}|{rule_type}|{canonical}"
    return hashlib.sha256(raw.encode()).hexdigest()
