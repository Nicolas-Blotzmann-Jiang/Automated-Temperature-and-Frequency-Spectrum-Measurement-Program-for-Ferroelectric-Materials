"""仪器连接、断开、单次测量操作。"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox

from instrument_drivers import DP800, ZM237x
from gui_pages import LCR_PARAM_MAP
from common import DummyTemperatureController, StabilityConfig, wait_for_stable, _now_iso
from visa_scan import discover_instruments


def _idn_matches(idn: str, *needles: str) -> bool:
    text = idn.upper()
    return all(needle.upper() in text for needle in needles)


# ==================== DP800 ====================

def _connect_device(self, cls, resource_var, timeout_var, status_var, log_prefix: str, title: str):
    def work():
        try:
            inst = cls(resource_var.get().strip(), int(timeout_var.get().strip()))
            inst.connect()
            idn = inst.idn()
            return inst, idn
        except Exception as e:
            self._threadsafe(lambda: status_var.set("连接失败"))
            self._threadsafe(lambda: messagebox.showerror(title, str(e)))
            return None, None

    inst, idn = work()
    if inst is not None and idn is not None:
        return inst, idn
    return None, None

def _connect_dp(self) -> None:
    def work():
        try:
            inst = DP800(self.dp_resource_var.get().strip(),
                         int(self.dp_timeout_var.get().strip()))
            inst.connect()
            idn = inst.idn()
            if not _idn_matches(idn, "RIGOL", "DP8"):
                inst.close()
                raise RuntimeError(f"该 VISA 地址实际连接到 {idn}，不是 DP800。请检查是否选错仪器类型。")
            self.dp_inst = inst
            self._threadsafe(lambda: self.dp_status_var.set(f"已连接: {idn}"))
            self._threadsafe(lambda: self._append_log(f"DP800 已连接: {idn}"))
        except Exception as e:
            self._threadsafe(lambda: self.dp_status_var.set("连接失败"))
            self._threadsafe(lambda: messagebox.showerror("DP800 连接失败", str(e)))
    threading.Thread(target=work, daemon=True).start()


def _auto_connect_all(self) -> None:
    def work():
        try:
            dp_timeout = int(self.dp_timeout_var.get().strip())
        except Exception:
            dp_timeout = 10000
        try:
            lcr_timeout = int(self.lcr_timeout_var.get().strip())
        except Exception:
            lcr_timeout = 10000

        try:
            data = discover_instruments(timeout_ms=max(dp_timeout, lcr_timeout))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("自动识别失败", str(e)))
            return

        classified = data.get("classified", {})
        dp_candidates = classified.get("DP800", []) or []
        lcr_candidates = classified.get("LCR", []) or []

        if dp_candidates:
            self.dp_resource_var.set(dp_candidates[0])
        if lcr_candidates:
            self.lcr_resource_var.set(lcr_candidates[0])

        if not dp_candidates and not lcr_candidates:
            self._threadsafe(lambda: messagebox.showinfo("未识别到仪器", "未发现可自动匹配的 DP800 或 LCR 资源。"))
            self._threadsafe(lambda: self._append_log("自动识别未找到可匹配仪器"))
            return

        connect_logs: list[str] = []

        if dp_candidates:
            try:
                inst = DP800(dp_candidates[0], dp_timeout)
                inst.connect()
                idn = inst.idn()
                if not _idn_matches(idn, "RIGOL", "DP8"):
                    inst.close()
                    raise RuntimeError(f"扫描到的地址 {dp_candidates[0]} 实际是 {idn}，不是 DP800。")
                self.dp_inst = inst
                connect_logs.append(f"DP800 已连接: {idn} @ {dp_candidates[0]}")
                self._threadsafe(lambda: self.dp_status_var.set(f"已连接: {idn}"))
            except Exception as e:
                connect_logs.append(f"DP800 连接失败: {e}")
                self._threadsafe(lambda: self.dp_status_var.set("连接失败"))

        if lcr_candidates:
            try:
                inst = ZM237x(lcr_candidates[0], lcr_timeout)
                inst.connect()
                idn = inst.idn()
                if not _idn_matches(idn, "NF", "ZM237"):
                    inst.close()
                    raise RuntimeError(f"扫描到的地址 {lcr_candidates[0]} 实际是 {idn}，不是 LCR。")
                self.lcr_inst = inst
                connect_logs.append(f"LCR 已连接: {idn} @ {lcr_candidates[0]}")
                self._threadsafe(lambda: self.lcr_status_var.set(f"已连接: {idn}"))
            except Exception as e:
                connect_logs.append(f"LCR 连接失败: {e}")
                self._threadsafe(lambda: self.lcr_status_var.set("连接失败"))

        for line in connect_logs:
            self._threadsafe(lambda line=line: self._append_log(line))

        if not connect_logs:
            self._threadsafe(lambda: messagebox.showinfo("自动连接", "未执行任何连接。"))

    threading.Thread(target=work, daemon=True).start()

def _disconnect_dp(self) -> None:
    if self.dp_inst:
        try:
            self.dp_inst.close()
        except Exception:
            pass
        self.dp_inst = None
    self.dp_status_var.set("已断开")
    self._append_log("DP800 已断开")

def _dp_output(self, on: bool) -> None:
    inst = self.dp_inst
    if not inst:
        messagebox.showwarning("未连接", "请先连接 DP800")
        return
    def work():
        try:
            ch = self.dp_channel_var.get()
            if on:
                inst.output_on(ch)
                self._threadsafe(lambda: self._append_log(f"DP800 {ch} ON"))
            else:
                inst.output_off(ch)
                self._threadsafe(lambda: self._append_log(f"DP800 {ch} OFF"))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("DP800 控制失败", str(e)))
    threading.Thread(target=work, daemon=True).start()

def _dp_measure(self) -> None:
    inst = self.dp_inst
    if not inst:
        messagebox.showwarning("未连接", "请先连接 DP800")
        return
    def work():
        try:
            ch = self.dp_channel_var.get()
            v = float(self.dp_voltage_var.get().strip())
            c = float(self.dp_current_var.get().strip())
            inst.apply(ch, v, c)
            inst.output_on(ch)
            time.sleep(0.3)
            mv, mc, mp = inst.measure_all(ch)
            mode = inst.get_output_mode(ch)
            txt = (f"--- DP800 ---\n通道: {ch}\n"
                   f"设定: {v}V / {c}A\n"
                   f"实测: {mv:.6g}V / {mc:.6g}A / {mp:.6g}W\n"
                   f"模式: {mode}\n时间: {_now_iso()}")
            self._threadsafe(lambda: self._set_single_result(txt))
            self._threadsafe(lambda: self._append_log(
                f"DP800: V={mv:.6g} I={mc:.6g} P={mp:.6g}"))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("DP800 测量失败", str(e)))
    threading.Thread(target=work, daemon=True).start()


# ==================== LCR ====================

def _connect_lcr(self) -> None:
    def work():
        try:
            inst = ZM237x(self.lcr_resource_var.get().strip(),
                          int(self.lcr_timeout_var.get().strip()))
            inst.connect()
            idn = inst.idn()
            if not _idn_matches(idn, "NF", "ZM237"):
                inst.close()
                raise RuntimeError(f"该 VISA 地址实际连接到 {idn}，不是 ZM237x。请检查是否选错仪器类型。")
            self.lcr_inst = inst
            self._threadsafe(lambda: self.lcr_status_var.set(f"已连接: {idn}"))
            self._threadsafe(lambda: self._append_log(f"LCR 已连接: {idn}"))
        except Exception as e:
            self._threadsafe(lambda: self.lcr_status_var.set("连接失败"))
            self._threadsafe(lambda: messagebox.showerror("LCR 连接失败", str(e)))
    threading.Thread(target=work, daemon=True).start()

def _disconnect_lcr(self) -> None:
    if self.lcr_inst:
        try:
            self.lcr_inst.close()
        except Exception:
            pass
        self.lcr_inst = None
    self.lcr_status_var.set("已断开")
    self._append_log("LCR 已断开")

def _lcr_measure(self) -> None:
    inst = self.lcr_inst
    if not inst:
        messagebox.showwarning("未连接", "请先连接 LCR")
        return
    def work():
        try:
            freq = float(self.lcr_freq_var.get().strip())
            level = float(self.lcr_level_var.get().strip())
            pri = self.lcr_primary_var.get()
            sec = self.lcr_secondary_var.get()
            speed = self.lcr_speed_var.get()
            bias = float(self.lcr_bias_var.get().strip())
            inst.set_frequency(freq)
            inst.set_voltage_level(level)
            inst.set_primary_param(LCR_PARAM_MAP.get(pri, pri))
            inst.set_secondary_param(LCR_PARAM_MAP.get(sec, sec))
            inst.set_measurement_speed(speed)
            inst.set_dc_bias(bias, enable=(abs(bias) > 1e-9))
            if self.lcr_range_var.get() == "AUTO":
                inst.set_auto_range(True)
            else:
                inst.set_auto_range(False)
            vals, raw = inst.measure_once()
            p = vals[0] if len(vals) >= 1 else 0
            s = vals[1] if len(vals) >= 2 else 0
            txt = (f"--- LCR ---\n频率: {freq} Hz\n电平: {level} V\n"
                   f"偏压: {bias} V\n"
                   f"{pri} = {p:.6g}\n{sec} = {s:.6g}\n"
                   f"原始: {raw}\n时间: {_now_iso()}")
            self._threadsafe(lambda: self._set_single_result(txt))
            self._threadsafe(lambda: self._append_log(
                f"LCR: {pri}={p:.6g} {sec}={s:.6g}"))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("LCR 测量失败", str(e)))
    threading.Thread(target=work, daemon=True).start()


# ==================== 控温仪 ====================

def _init_tc(self) -> None:
    try:
        amb = float(self.tc_ambient_var.get().strip())
        self.tc_inst = DummyTemperatureController(ambient_c=amb)
        self.tc_inst.connect()
        self.tc_status_var.set(f"已初始化 (环境 {amb}°C)")
        self._append_log(f"控温仪模拟初始化: 环境 {amb}°C")
    except Exception as e:
        messagebox.showerror("控温仪初始化失败", str(e))

def _set_tc_target(self) -> None:
    tc = self.tc_inst
    if not tc:
        messagebox.showwarning("未初始化", "请先初始化控温仪")
        return
    try:
        sv = float(self.tc_setpoint_var.get().strip())
        tc.set_setpoint(sv)
        self.tc_status_var.set(f"设定温度 {sv}°C")
        self._append_log(f"控温仪设定: {sv}°C")
    except Exception as e:
        messagebox.showerror("设定失败", str(e))

def _tc_read(self) -> None:
    tc = self.tc_inst
    if not tc:
        messagebox.showwarning("未初始化", "请先初始化控温仪")
        return
    try:
        pv = tc.get_pv()
        sv = tc.get_sv()
        txt = (f"--- 控温仪 ---\nPV = {pv:.3f} °C\n"
               f"SV = {sv if sv is not None else 'N/A'} °C\n"
               f"时间: {_now_iso()}")
        self._threadsafe(lambda: self._set_single_result(txt))
        self._threadsafe(lambda: self._append_log(f"控温仪: PV={pv:.3f}°C"))
    except Exception as e:
        messagebox.showerror("读取失败", str(e))

def _tc_wait_stable(self) -> None:
    tc = self.tc_inst
    if not tc:
        messagebox.showwarning("未初始化", "请先初始化控温仪")
        return
    def work():
        try:
            target = float(self.tc_setpoint_var.get().strip())
            cfg = StabilityConfig(
                tol_c=float(self.tc_tol_var.get().strip()),
                stable_s=float(self.tc_stable_s_var.get().strip()),
                poll_s=float(self.tc_poll_s_var.get().strip()),
                max_wait_s=float(self.tc_max_wait_var.get().strip()))
            self._threadsafe(lambda: self._append_log("等待温度稳定..."))
            pv = wait_for_stable(
                tc, target, cfg,
                lambda m: self._threadsafe(
                    lambda: self._append_log(m)))
            txt = (f"--- 稳定完成 ---\n最终 PV = {pv:.3f} °C\n"
                   f"目标 = {target:.3f} °C\n时间: {_now_iso()}")
            self._threadsafe(lambda: self._set_single_result(txt))
        except TimeoutError as e:
            self._threadsafe(lambda: messagebox.showwarning("超时", str(e)))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("失败", str(e)))
    threading.Thread(target=work, daemon=True).start()
