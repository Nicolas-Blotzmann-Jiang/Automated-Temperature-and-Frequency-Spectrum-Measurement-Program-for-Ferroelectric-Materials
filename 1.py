"""兼容入口。

真实仪器连接代码已拆到 instrument_drivers.py，
纯工具和模拟控制代码在 common.py，
单次测量流程在 workflow.py。
"""

from common import (
    DummyTemperatureController,
    RegisterSpec,
    StabilityConfig,
    TemperatureController,
    _decode_registers,
    _ensure_parent_dir,
    _float_from_text,
    _gen_temps,
    _logger,
    _now_iso,
    _parse_csv_floats,
    _parse_specs,
    _parse_temps_csv,
    _register_count,
    _split_cmds,
    wait_for_stable,
)
from instrument_drivers import (
    AsciiSerialTemperatureController,
    DP800,
    ModbusReader,
    ZM237x,
)
from workflow import dp_single_measure


__all__ = [
    "AsciiSerialTemperatureController",
    "DP800",
    "DummyTemperatureController",
    "ModbusReader",
    "RegisterSpec",
    "StabilityConfig",
    "TemperatureController",
    "ZM237x",
    "_decode_registers",
    "_ensure_parent_dir",
    "_float_from_text",
    "_gen_temps",
    "_logger",
    "_now_iso",
    "_parse_csv_floats",
    "_parse_specs",
    "_parse_temps_csv",
    "_register_count",
    "_split_cmds",
    "dp_single_measure",
    "wait_for_stable",
]


if __name__ == "__main__":
    from gui import main

    main()
