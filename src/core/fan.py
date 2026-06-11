from __future__ import annotations

import subprocess

from .sensors import NbfcError, get_fan_statuses

MIN_SPEED = 0.0
MAX_SPEED = 100.0


def _run_nbfc_set(args: list[str]) -> None:
    try:
        result = subprocess.run(
            ["pkexec", "nbfc", "set", *args],
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


def _validate_speed(speed: float) -> None:
    if not (MIN_SPEED <= speed <= MAX_SPEED):
        raise ValueError(f"Speed must be between {MIN_SPEED} and {MAX_SPEED}, got {speed}")


def _validate_fan_index(fan_index: int) -> None:
    fan_count = len(get_fan_statuses())
    if not (0 <= fan_index < fan_count):
        raise ValueError(f"Fan index must be between 0 and {fan_count - 1}, got {fan_index}")


def list_fans() -> list[tuple[int, str]]:
    return [(i, fan.name) for i, fan in enumerate(get_fan_statuses())]


def set_fan_speed(fan_index: int, speed: float) -> None:
    _validate_fan_index(fan_index)
    _validate_speed(speed)
    _run_nbfc_set(["-f", str(fan_index), "-s", str(speed)])


def set_fan_auto(fan_index: int) -> None:
    _validate_fan_index(fan_index)
    _run_nbfc_set(["-f", str(fan_index), "-a"])


def set_fan_max(fan_index: int) -> None:
    set_fan_speed(fan_index, MAX_SPEED)


def set_all_fans_speed(speed: float) -> None:
    _validate_speed(speed)
    for index, _ in list_fans():
        set_fan_speed(index, speed)


def set_all_fans_auto() -> None:
    for index, _ in list_fans():
        set_fan_auto(index)


def set_all_fans_max() -> None:
    set_all_fans_speed(MAX_SPEED)


if __name__ == "__main__":
    for index, name in list_fans():
        print(f"{index}: {name}")