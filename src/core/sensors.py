from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class FanStatus:
    name: str
    temperature: float
    auto_control_enabled: bool
    critical_mode_enabled: bool
    current_speed: float
    target_speed: float
    speed_steps: int


class NbfcError(Exception):
    pass


def _run_nbfc_status() -> str:
    try:
        result = subprocess.run(
            ["nbfc", "status", "-a"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except FileNotFoundError as exc:
        raise NbfcError("nbfc command not found. Is nbfc-linux installed?") from exc
    except subprocess.TimeoutExpired as exc:
        raise NbfcError("nbfc command timed out.") from exc

    if result.returncode != 0:
        raise NbfcError(f"nbfc returned an error: {result.stderr.strip()}")

    return result.stdout


def _parse_bool(value: str) -> bool:
    return value.strip().lower() == "true"


def parse_status(raw_output: str) -> list[FanStatus]:
    fans: list[FanStatus] = []
    current: dict[str, str] = {}

    for line in raw_output.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if key == "Fan Display Name":
            if current:
                fans.append(_build_fan_status(current))
            current = {"Fan Display Name": value}
        elif current:
            current[key] = value

    if current:
        fans.append(_build_fan_status(current))

    return fans


def _build_fan_status(data: dict[str, str]) -> FanStatus:
    try:
        return FanStatus(
            name=data["Fan Display Name"],
            temperature=float(data["Temperature"]),
            auto_control_enabled=_parse_bool(data["Auto Control Enabled"]),
            critical_mode_enabled=_parse_bool(data["Critical Mode Enabled"]),
            current_speed=float(data["Current Fan Speed"]),
            target_speed=float(data["Target Fan Speed"]),
            speed_steps=int(data["Fan Speed Steps"]),
        )
    except KeyError as exc:
        raise NbfcError(f"Missing expected field in nbfc output: {exc}") from exc
    except ValueError as exc:
        raise NbfcError(f"Failed to parse numeric value: {exc}") from exc


def get_fan_statuses() -> list[FanStatus]:
    raw = _run_nbfc_status()
    return parse_status(raw)


if __name__ == "__main__":
    for fan in get_fan_statuses():
        print(fan)