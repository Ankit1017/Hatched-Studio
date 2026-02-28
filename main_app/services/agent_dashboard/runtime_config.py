from __future__ import annotations

import os


def use_generic_asset_flow() -> bool:
    return _env_bool("USE_GENERIC_ASSET_FLOW", default=True)


def enable_verify_stage() -> bool:
    return _env_bool("ENABLE_VERIFY_STAGE", default=True)


def execute_retry_count() -> int:
    return _env_int("EXECUTE_RETRY_COUNT", default=1, minimum=0, maximum=5)


def execute_stage_timeout_ms() -> int:
    return _env_int(
        "EXECUTE_STAGE_TIMEOUT_MS",
        default=stage_timeout_ms(),
        minimum=1,
        maximum=300000,
    )


def verify_stage_timeout_ms() -> int:
    return _env_int(
        "VERIFY_STAGE_TIMEOUT_MS",
        default=min(stage_timeout_ms(), 5000),
        minimum=1,
        maximum=60000,
    )


def stage_timeout_ms() -> int:
    return _env_int("STAGE_TIMEOUT_MS", default=30000, minimum=1, maximum=300000)


def workflow_fail_policy() -> str:
    raw = " ".join(str(os.getenv("WORKFLOW_FAIL_POLICY", "continue")).split()).strip().lower()
    return "fail_fast" if raw in {"fail_fast", "failfast"} else "continue"


def execution_dedup_enabled() -> bool:
    return _env_bool("EXECUTION_DEDUP_ENABLED", default=True)


def max_parallel_tools() -> int:
    return _env_int("MAX_PARALLEL_TOOLS", default=2, minimum=1, maximum=16)


def enable_parallel_dag() -> bool:
    return _env_bool("ENABLE_PARALLEL_DAG", default=True)


def enable_policy_gate() -> bool:
    return _env_bool("ENABLE_POLICY_GATE", default=True)


def policy_gate_mode() -> str:
    raw = " ".join(str(os.getenv("POLICY_GATE_MODE", "strict")).split()).strip().lower()
    return "warn_only" if raw in {"warn_only", "warn", "warning"} else "strict"


def run_ledger_retention_days() -> int:
    return _env_int("RUN_LEDGER_RETENTION_DAYS", default=30, minimum=1, maximum=3650)


def schema_validate_enforce() -> bool:
    return _env_bool("SCHEMA_VALIDATE_ENFORCE", default=True)


def _env_bool(name: str, *, default: bool) -> bool:
    raw = " ".join(str(os.getenv(name, "true" if default else "false")).split()).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _env_int(name: str, *, default: int, minimum: int, maximum: int) -> int:
    raw = " ".join(str(os.getenv(name, str(default))).split()).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        value = default
    return max(minimum, min(maximum, value))
