from __future__ import annotations

import re
import time
from typing import Any, Callable, Optional

from common import RegisterSpec, _decode_registers, _parse_csv_floats, _register_count, TemperatureController


class DP800:
    """RIGOL DP800 系列可编程线性直流电源 SCPI/VISA 控制。"""

    def __init__(
        self,
        resource: str,
        timeout_ms: int = 10000,
        read_termination: str = "\n",
        write_termination: str = "\n",
    ) -> None:
        self.resource = resource
        self.timeout_ms = timeout_ms
        self.read_termination = read_termination
        self.write_termination = write_termination
        self._inst = None

    def connect(self) -> None:
        try:
            import pyvisa  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖 pyvisa。请先安装：pip install pyvisa pyvisa-py") from e

        rm = pyvisa.ResourceManager()
        inst = rm.open_resource(self.resource)
        inst.timeout = self.timeout_ms
        inst.read_termination = self.read_termination
        inst.write_termination = self.write_termination
        self._inst = inst

    def close(self) -> None:
        if self._inst is not None:
            try:
                self._inst.close()
            finally:
                self._inst = None

    def write(self, cmd: str) -> None:
        if self._inst is None:
            raise RuntimeError("DP800 未连接")
        self._inst.write(cmd)

    def query(self, cmd: str) -> str:
        if self._inst is None:
            raise RuntimeError("DP800 未连接")
        return str(self._inst.query(cmd)).strip()

    def idn(self) -> str:
        return self.query("*IDN?")

    def set_channel(self, channel: str = "CH1") -> None:
        self.write(f":INST {channel}")

    def set_voltage(self, voltage: float, channel: Optional[str] = None) -> None:
        if channel:
            self.set_channel(channel)
        self.write(f":VOLT {voltage}")

    def set_current(self, current: float, channel: Optional[str] = None) -> None:
        if channel:
            self.set_channel(channel)
        self.write(f":CURR {current}")

    def output_on(self, channel: str = "CH1") -> None:
        self.write(f":OUTP {channel},ON")

    def output_off(self, channel: str = "CH1") -> None:
        self.write(f":OUTP {channel},OFF")

    def measure_voltage(self, channel: str = "CH1") -> float:
        return float(self.query(f":MEAS? {channel}"))

    def measure_current(self, channel: str = "CH1") -> float:
        return float(self.query(f":MEAS:CURR? {channel}"))

    def measure_power(self, channel: str = "CH1") -> float:
        return float(self.query(f":MEAS:POWE? {channel}"))

    def measure_all(self, channel: str = "CH1") -> tuple[float, float, float]:
        vals = _parse_csv_floats(self.query(f":MEAS:ALL? {channel}"))
        v = vals[0] if len(vals) >= 1 else 0.0
        c = vals[1] if len(vals) >= 2 else 0.0
        p = vals[2] if len(vals) >= 3 else 0.0
        return v, c, p

    def configure(
        self,
        voltage: float,
        current: float,
        channel: str = "CH1",
        ovp: Optional[float] = None,
        ocp: Optional[float] = None,
    ) -> None:
        self.set_channel(channel)
        if ovp is not None:
            self.write(f":VOLT:PROT {ovp}")
            self.write(":VOLT:PROT:STAT ON")
        if ocp is not None:
            self.write(f":CURR:PROT {ocp}")
            self.write(":CURR:PROT:STAT ON")
        self.set_voltage(voltage)
        self.set_current(current)

    def apply(self, channel: str, voltage: float, current: float) -> None:
        self.write(f":APPL {channel},{voltage},{current}")

    def get_output_mode(self, channel: str = "CH1") -> str:
        return self.query(f":OUTP:MODE? {channel}")


class ZM237x:
    """NF ZM2371/ZM2372 LCR 表远程控制。"""

    def __init__(
        self,
        resource: str,
        timeout_ms: int = 10000,
        read_termination: str = "\n",
        write_termination: str = "\n",
    ) -> None:
        self.resource = resource
        self.timeout_ms = timeout_ms
        self.read_termination = read_termination
        self.write_termination = write_termination
        self._inst = None

    def connect(self) -> None:
        try:
            import pyvisa  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖 pyvisa。请先安装：pip install pyvisa pyvisa-py") from e

        rm = pyvisa.ResourceManager()
        inst = rm.open_resource(self.resource)
        inst.timeout = self.timeout_ms
        inst.read_termination = self.read_termination
        inst.write_termination = self.write_termination
        self._inst = inst

    def close(self) -> None:
        if self._inst is not None:
            try:
                self._inst.close()
            finally:
                self._inst = None

    def write(self, cmd: str) -> None:
        if self._inst is None:
            raise RuntimeError("ZM237x 未连接")
        self._inst.write(cmd)

    def query(self, cmd: str) -> str:
        if self._inst is None:
            raise RuntimeError("ZM237x 未连接")
        return str(self._inst.query(cmd)).strip()

    def idn(self) -> str:
        return self.query("*IDN?")

    def reset(self) -> None:
        self.write("*RST")

    def set_frequency(self, freq_hz: float) -> None:
        self.write(f":SOUR:FREQ {freq_hz}")

    def set_voltage_level(self, volt_v: float) -> None:
        self.write(f":SOUR:VOLT {volt_v}")

    def set_measurement_speed(self, speed: str = "MED") -> None:
        self.write(f":APER {speed}")

    def set_trigger_source(self, source: str = "INT") -> None:
        self.write(f":TRIG:SOUR {source}")

    def set_trigger_delay(self, delay_s: float = 0.0) -> None:
        self.write(f":TRIG:DEL {delay_s}")

    def set_averaging(self, count: int = 1) -> None:
        if count <= 1:
            self.write(":AVER:STAT OFF")
        else:
            self.write(f":AVER:COUN {count}")
            self.write(":AVER:STAT ON")

    def set_primary_param(self, param: str = "C") -> None:
        self.write(f":CALC1:FORM {param}")

    def set_secondary_param(self, param: str = "D") -> None:
        self.write(f":CALC2:FORM {param}")

    def set_auto_range(self, enabled: bool = True) -> None:
        val = "ON" if enabled else "OFF"
        self.write(f":RANG:AUTO {val}")

    def set_range(self, range_ohm: float = 100.0) -> None:
        self.write(f":RANG {range_ohm}")

    def set_dc_bias(self, voltage: float = 0.0, enable: bool = False) -> None:
        self.write(f":SOUR:VOLT:OFFS {voltage}")
        state = "ON" if enable else "OFF"
        self.write(f":SOUR:VOLT:OFFS:STAT {state}")

    def set_cable_length(self, length_m: int = 0) -> None:
        self.write(f":CAL:CABL {length_m}")

    def enable_open_correction(self, enable: bool = True) -> None:
        val = "ON" if enable else "OFF"
        self.write(f":CORR:OPEN {val}")

    def enable_short_correction(self, enable: bool = True) -> None:
        val = "ON" if enable else "OFF"
        self.write(f":CORR:SHOR {val}")

    def measure_open_correction(self) -> None:
        self.write(":CORR:COLL STAN1")
        time.sleep(0.5)

    def measure_short_correction(self) -> None:
        self.write(":CORR:COLL STAN2")
        time.sleep(0.5)

    def configure_measurement(
        self,
        freq_hz: float = 1000.0,
        volt_v: float = 1.0,
        primary_param: str = "C",
        secondary_param: str = "D",
        speed: str = "MED",
        trigger_source: str = "INT",
        trigger_delay: float = 0.0,
        averaging: int = 1,
        auto_range: bool = True,
        range_ohm: float = 100.0,
    ) -> None:
        self.set_frequency(freq_hz)
        self.set_voltage_level(volt_v)
        self.set_primary_param(primary_param)
        self.set_secondary_param(secondary_param)
        self.set_measurement_speed(speed)
        self.set_trigger_source(trigger_source)
        self.set_trigger_delay(trigger_delay)
        self.set_averaging(averaging)
        self.set_auto_range(auto_range)
        if not auto_range:
            self.set_range(range_ohm)

    def measure_once(self) -> tuple[list[float], str]:
        raw = self.query(":READ?")
        vals = _parse_csv_floats(raw)
        # 返回值格式: <measurement status>, <primary>, <secondary> [, <bin>]
        # 跳过第一个测量状态值，只返回主参数和副参数
        if len(vals) >= 3:
            return vals[1:3], raw
        elif len(vals) >= 2:
            return [vals[1]], raw
        else:
            return vals, raw

    def trigger_and_read(self) -> tuple[list[float], str]:
        raw = self.query(":READ?")
        vals = _parse_csv_floats(raw)
        return vals, raw

    def get_voltage_monitor(self) -> float:
        return float(self.query(":DATA? VMON"))

    def get_current_monitor(self) -> float:
        return float(self.query(":DATA? IMON"))


class AsciiSerialTemperatureController(TemperatureController):
    """通过串口 ASCII 指令控制温控器。"""

    def __init__(
        self,
        port: str,
        baud: int,
        timeout_s: float,
        sv_cmd: str,
        pv_query: str,
        sv_query: Optional[str] = None,
        extract_regex: str = r"([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
        line_ending: str = "\r\n",
    ) -> None:
        self.port = port
        self.baud = baud
        self.timeout_s = timeout_s
        self.sv_cmd = sv_cmd
        self.pv_query = pv_query
        self.sv_query = sv_query
        self.extract_regex = re.compile(extract_regex)
        self.line_ending = line_ending
        self._ser = None

    def connect(self) -> None:
        try:
            import serial  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖 pyserial。请先安装：pip install pyserial") from e

        self._ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            timeout=self.timeout_s,
            bytesize=8,
            parity="N",
            stopbits=1,
        )

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            finally:
                self._ser = None

    def _write(self, s: str) -> None:
        if self._ser is None:
            raise RuntimeError("温控仪未连接")
        data = s.encode("ascii", errors="ignore")
        self._ser.write(data)

    def _readline(self) -> str:
        if self._ser is None:
            raise RuntimeError("温控仪未连接")
        raw = self._ser.readline()
        return raw.decode("ascii", errors="ignore").strip()

    def _query(self, cmd: str) -> str:
        self._write(cmd)
        return self._readline()

    def _extract_temp(self, text: str) -> float:
        m = self.extract_regex.search(text)
        if not m:
            raise ValueError(f"无法从返回值解析温度：{text!r}")
        return float(m.group(1))

    def set_setpoint(self, temp_c: float) -> None:
        cmd = self.sv_cmd.format(temp=float(temp_c))
        if not cmd.endswith(("\n", "\r")):
            cmd = cmd + self.line_ending
        self._write(cmd)

    def get_pv(self) -> float:
        cmd = self.pv_query
        if not cmd.endswith(("\n", "\r")):
            cmd = cmd + self.line_ending
        resp = self._query(cmd)
        return self._extract_temp(resp)

    def get_sv(self) -> Optional[float]:
        if not self.sv_query:
            return None
        cmd = self.sv_query
        if not cmd.endswith(("\n", "\r")):
            cmd = cmd + self.line_ending
        resp = self._query(cmd)
        return self._extract_temp(resp)


class ModbusReader:
    def __init__(
        self,
        link: str,
        unit: int,
        host: str = "127.0.0.1",
        port: int = 502,
        serial_port: str = "COM1",
        baud: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        timeout_s: float = 1.0,
    ) -> None:
        self.link = link.lower()
        self.unit = int(unit)
        self.host = host
        self.port = int(port)
        self.serial_port = serial_port
        self.baud = int(baud)
        self.parity = parity
        self.stopbits = int(stopbits)
        self.bytesize = int(bytesize)
        self.timeout_s = float(timeout_s)
        self._client = None

    def connect(self) -> None:
        try:
            from pymodbus.client import ModbusSerialClient, ModbusTcpClient  # type: ignore
        except Exception as e:
            raise RuntimeError("缺少依赖 pymodbus。请先安装：pip install pymodbus") from e

        if self.link == "tcp":
            client = ModbusTcpClient(host=self.host, port=self.port, timeout=self.timeout_s)
        elif self.link == "rtu":
            client = ModbusSerialClient(
                method="rtu",
                port=self.serial_port,
                baudrate=self.baud,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout_s,
            )
        else:
            raise ValueError(f"不支持的 Modbus 链路类型: {self.link}")

        if not client.connect():
            raise ConnectionError("Modbus 连接失败，请检查地址/端口/串口参数")
        self._client = client

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.close()
            finally:
                self._client = None

    def _call(self, method: Callable[..., Any], **kwargs: Any) -> Any:
        try:
            return method(**kwargs, slave=self.unit)
        except TypeError:
            return method(**kwargs, unit=self.unit)

    def read_one(self, spec: RegisterSpec) -> float | int | bool:
        if self._client is None:
            raise RuntimeError("Modbus 设备未连接")

        fc = spec.fc.lower()
        if fc in ("holding", "hr"):
            count = _register_count(spec.dtype)
            res = self._call(self._client.read_holding_registers, address=spec.address, count=count)
            if res.isError():
                raise RuntimeError(f"读取 holding 失败: {spec.name}@{spec.address}")
            value = _decode_registers(list(res.registers), spec.dtype)
        elif fc in ("input", "ir"):
            count = _register_count(spec.dtype)
            res = self._call(self._client.read_input_registers, address=spec.address, count=count)
            if res.isError():
                raise RuntimeError(f"读取 input 失败: {spec.name}@{spec.address}")
            value = _decode_registers(list(res.registers), spec.dtype)
        elif fc in ("coil", "coils"):
            res = self._call(self._client.read_coils, address=spec.address, count=1)
            if res.isError():
                raise RuntimeError(f"读取 coil 失败: {spec.name}@{spec.address}")
            value = bool(res.bits[0])
        elif fc in ("discrete", "di"):
            res = self._call(self._client.read_discrete_inputs, address=spec.address, count=1)
            if res.isError():
                raise RuntimeError(f"读取 discrete input 失败: {spec.name}@{spec.address}")
            value = bool(res.bits[0])
        else:
            raise ValueError(f"不支持的功能码类型: {spec.fc}")

        if isinstance(value, bool):
            return value
        return float(value) * float(spec.scale)
