from __future__ import annotations

import dataclasses
import datetime as _dt
import os
import re
import time
from typing import Any, Callable, Optional


def _now_iso() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def _float_from_text(text: str) -> float:
    m = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)
    if not m:
        raise ValueError(f"无法从返回值解析浮点数：{text!r}")
    return float(m.group(0))


def _parse_csv_floats(text: str) -> list[float]:
    parts = [p.strip() for p in text.strip().split(",") if p.strip()]
    floats: list[float] = []
    for p in parts:
        try:
            floats.append(float(p))
        except ValueError:
            floats.append(_float_from_text(p))
    return floats


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


@dataclasses.dataclass
class RegisterSpec:
    name: str
    address: int
    dtype: str = "u16"
    scale: float = 1.0
    fc: str = "holding"


def _register_count(dtype: str) -> int:
    dt = dtype.lower()
    if dt in ("u16", "s16", "bool"):
        return 1
    if dt in ("u32", "s32", "f32"):
        return 2
    raise ValueError(f"不支持的数据类型: {dtype}")


def _decode_registers(registers: list[int], dtype: str) -> float | int | bool:
    dt = dtype.lower()
    if dt == "u16":
        return int(registers[0] & 0xFFFF)
    if dt == "s16":
        v = int(registers[0] & 0xFFFF)
        return v - 0x10000 if v >= 0x8000 else v
    if dt in ("u32", "s32", "f32"):
        if len(registers) < 2:
            raise ValueError("32 位数据至少需要 2 个寄存器")
        raw = ((int(registers[0]) & 0xFFFF) << 16) | (int(registers[1]) & 0xFFFF)
        if dt == "u32":
            return raw
        if dt == "s32":
            return raw - 0x100000000 if raw >= 0x80000000 else raw
        import struct

        return float(struct.unpack(">f", struct.pack(">I", raw))[0])
    if dt == "bool":
        return bool(registers[0])
    raise ValueError(f"不支持的数据类型: {dtype}")


def _parse_specs(text: str) -> list[RegisterSpec]:
    if not text.strip():
        return []
    items: list[RegisterSpec] = []
    for token in [x.strip() for x in text.split(";") if x.strip()]:
        if "@" not in token:
            raise ValueError(f"寄存器定义缺少 @: {token}")
        name, rest = token.split("@", 1)
        parts = [p.strip() for p in rest.split(":")]
        address = int(parts[0], 0)
        dtype = parts[1] if len(parts) >= 2 and parts[1] else "u16"
        scale = float(parts[2]) if len(parts) >= 3 and parts[2] else 1.0
        fc = (parts[3] if len(parts) >= 4 and parts[3] else "holding").lower()
        items.append(RegisterSpec(name=name.strip(), address=address, dtype=dtype, scale=scale, fc=fc))
    return items


class TemperatureController:
    def connect(self) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def set_setpoint(self, temp_c: float) -> None:
        raise NotImplementedError

    def get_pv(self) -> float:
        raise NotImplementedError

    def get_sv(self) -> Optional[float]:
        return None


class DummyTemperatureController(TemperatureController):
    """无硬件时用于联调脚本流程。"""

    def __init__(self, ambient_c: float = 25.0, tau_s: float = 20.0) -> None:
        self.ambient_c = ambient_c
        self.tau_s = max(1e-6, tau_s)
        self._sv = ambient_c
        self._pv = ambient_c
        self._t_last = time.time()

    def connect(self) -> None:
        self._t_last = time.time()

    def close(self) -> None:
        return

    def _step(self) -> None:
        t = time.time()
        dt = t - self._t_last
        self._t_last = t
        alpha = 1.0 - pow(2.718281828, -dt / self.tau_s)
        self._pv = self._pv + alpha * (self._sv - self._pv)

    def set_setpoint(self, temp_c: float) -> None:
        self._step()
        self._sv = float(temp_c)

    def get_pv(self) -> float:
        self._step()
        return float(self._pv)

    def get_sv(self) -> Optional[float]:
        return float(self._sv)


@dataclasses.dataclass
class StabilityConfig:
    tol_c: float
    stable_s: float
    poll_s: float
    max_wait_s: float


def wait_for_stable(
    tc: TemperatureController,
    target_c: float,
    cfg: StabilityConfig,
    log: Callable[[str], None],
) -> float:
    start = time.time()
    stable_start: Optional[float] = None
    last_pv = float("nan")
    while True:
        pv = tc.get_pv()
        last_pv = pv
        err = pv - target_c
        within = abs(err) <= cfg.tol_c

        elapsed = time.time() - start
        if within:
            if stable_start is None:
                stable_start = time.time()
            stable_elapsed = time.time() - stable_start
        else:
            stable_start = None
            stable_elapsed = 0.0

        log(
            f"PV={pv:.3f} °C, 目标={target_c:.3f} °C, 误差={err:+.3f} °C, "
            f"稳定计时={stable_elapsed:.0f}/{cfg.stable_s:.0f} s"
        )

        if stable_start is not None and (time.time() - stable_start) >= cfg.stable_s:
            return last_pv

        if elapsed >= cfg.max_wait_s:
            raise TimeoutError(
                f"等待温度稳定超时：已等 {elapsed:.0f}s，仍未在 ±{cfg.tol_c}°C 内稳定 {cfg.stable_s}s"
            )

        time.sleep(cfg.poll_s)


def _gen_temps(start: float, stop: float, step: float) -> list[float]:
    if step == 0:
        raise ValueError("t-step 不能为 0")
    temps: list[float] = []
    direction = 1 if stop >= start else -1
    step = abs(step) * direction
    t = start
    max_n = int(abs((stop - start) / step)) + 3
    for _ in range(max_n):
        if (direction == 1 and t > stop + 1e-12) or (direction == -1 and t < stop - 1e-12):
            break
        temps.append(round(float(t), 10))
        t += step
    if temps and abs(temps[-1] - stop) > 1e-9:
        temps.append(float(stop))
    if not temps:
        temps = [float(start)]
    return temps


def _parse_temps_csv(s: str) -> list[float]:
    vals: list[float] = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        vals.append(float(part))
    if not vals:
        raise ValueError("--temps 为空")
    return vals


def _logger(prefix: str = "") -> Callable[[str], None]:
    def _log(msg: str) -> None:
        print(prefix + msg, flush=True)

    return _log


def _split_cmds(cmds: str) -> list[str]:
    return [c.strip() for c in cmds.split(";") if c.strip()]
