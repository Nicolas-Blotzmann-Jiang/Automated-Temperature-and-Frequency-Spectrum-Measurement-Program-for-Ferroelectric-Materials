from __future__ import annotations

import time
from typing import Any, Callable

from common import _now_iso
from instrument_drivers import DP800


def dp_single_measure(
    dp_visa: str,
    timeout_ms: int,
    channel: str,
    voltage: float,
    current: float,
    log: Callable[[str], None],
) -> dict[str, Any]:
    """执行一次 DP800 电源测量并返回结果字典。"""
    dp = DP800(resource=dp_visa, timeout_ms=timeout_ms)
    try:
        log("连接 DP800...")
        dp.connect()
        idn = dp.idn()
        log(f"*IDN? = {idn}")

        dp.apply(channel, voltage, current)
        dp.output_on(channel)
        time.sleep(0.5)

        v, c, p = dp.measure_all(channel)
        mode = dp.get_output_mode(channel)

        result = {
            "timestamp": _now_iso(),
            "instrument": idn,
            "channel": channel,
            "set_voltage": voltage,
            "set_current": current,
            "measured_voltage": v,
            "measured_current": c,
            "measured_power": p,
            "output_mode": mode,
        }
        log(f"测量完成：V={v:.6g} V, I={c:.6g} A, P={p:.6g} W, 模式={mode}")
        return result
    finally:
        dp.close()
