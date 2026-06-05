from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None


ROTATION_STATUS_CODES = {401, 402, 403, 429, 432}


def env_keys(base_name: str, *, max_keys: int = 10) -> list[str]:
    names = [base_name]
    names.extend(f"{base_name}_{index}" for index in range(2, max_keys + 1))
    return [value for name in names if (value := os.environ.get(name))]


def post_json_with_key_rotation(
    url: str,
    payload: dict[str, Any],
    *,
    env_base: str,
    api_key_field: str | None = None,
    headers_factory: Callable[[str], dict[str, str]] | None = None,
    timeout: int = 30,
):
    if requests is None:
        return None

    last_response = None
    for api_key in env_keys(env_base):
        request_payload = dict(payload)
        if api_key_field:
            request_payload[api_key_field] = api_key
        headers = headers_factory(api_key) if headers_factory else None
        try:
            response = requests.post(url, json=request_payload, headers=headers, timeout=timeout)
        except requests.RequestException:
            continue
        last_response = response
        if response.ok or response.status_code not in ROTATION_STATUS_CODES:
            return response
    return last_response
