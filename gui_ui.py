"""GUI 仪器控制面板主模块。"""
from __future__ import annotations

import csv
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Any, Callable

from common import DummyTemperatureController, StabilityConfig, wait_for_stable, _now_iso
from instrument_drivers import DP800, ZM237x
from gui_plot import PlotFrame
from gui_table import ScanTable
from gui_pages import LCR_PARAM_MAP


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("综合仪器控制面板 · DC电源 / LCR表 / 控温仪")
        self.geometry("1320x880")
        self.minsize(1100, 700)

        # 仪器实例
        self.dp_inst: DP800 | None = None
        self.lcr_inst: ZM237x | None = None
        self.tc_inst: DummyTemperatureController | None = None

        # 扫描缓存（单参数）
        self.scan_x: list[float] = []
        self.scan_y: dict[str, list[float]] = {}
        self._scan_stop_flag = False

        # ---------- StringVar ----------
        # DP800
        self.dp_resource_var   = tk.StringVar(value="USB0::0x1AB1::0x0E11::DP8C0000000::INSTR")
        self.dp_timeout_var    = tk.StringVar(value="10000")
        self.dp_channel_var    = tk.StringVar(value="CH1")
        self.dp_voltage_var    = tk.StringVar(value="1.0")
        self.dp_current_var    = tk.StringVar(value="0.1")

        # LCR
        self.lcr_resource_var  = tk.StringVar(value="USB0::0x0B3E::0x1003::ZM2371-123456::INSTR")
        self.lcr_timeout_var   = tk.StringVar(value="10000")
        self.lcr_freq_var      = tk.StringVar(value="1000")
        self.lcr_level_var     = tk.StringVar(value="1.0")
        self.lcr_primary_var   = tk.StringVar(value="电容(C)")
        self.lcr_secondary_var = tk.StringVar(value="损耗因子(D)")
        self.lcr_speed_var     = tk.StringVar(value="MED")
        self.lcr_range_var     = tk.StringVar(value="AUTO")
        self.lcr_bias_var      = tk.StringVar(value="0.0")

        # 控温仪
        self.tc_ambient_var   = tk.StringVar(value="25.0")
        self.tc_setpoint_var  = tk.StringVar(value="30.0")
        self.tc_tol_var       = tk.StringVar(value="0.5")
        self.tc_stable_s_var  = tk.StringVar(value="3.0")
        self.tc_poll_s_var    = tk.StringVar(value="0.5")
        self.tc_max_wait_var  = tk.StringVar(value="120.0")

        # 扫描参数（单参数）
        self.scan_instrument_var  = tk.StringVar(value="LCR")
        self.scan_param_var       = tk.StringVar(value="频率")
        self.scan_start_var       = tk.StringVar(value="100")
        self.scan_stop_var        = tk.StringVar(value="10000")
        self.scan_step_var        = tk.StringVar(value="100")
        self.scan_dwell_var       = tk.StringVar(value="0.5")
        self.scan_primary_var     = tk.StringVar(value="电容(C)")
        self.scan_secondary_var   = tk.StringVar(value="损耗因子(D)")
        # 扫描高级选项
        self.scan_mode_var        = tk.StringVar(value="线性")       # 扫描模式：线性/对数
        self.scan_dp_ch_var       = tk.StringVar(value="CH1")        # DP800扫描通道
        self.scan_avg_var         = tk.StringVar(value="1")          # 平均次数
        self.scan_delay_var       = tk.StringVar(value="0.0")        # 触发延迟(s)
        self.scan_speed_var       = tk.StringVar(value="MED")        # LCR测量速度
        self.scan_range_var       = tk.StringVar(value="AUTO")       # LCR量程模式
        self.scan_bias_var        = tk.StringVar(value="0.0")        # LCR偏压(V)
        self.scan_points_var      = tk.StringVar(value="")           # 自动计算点数(只读)

        # ---------- 双参数扫描 StringVar ----------
        self.scan2d_instrument_var  = tk.StringVar(value="LCR")
        # 参数1
        self.scan2d_p1_param_var    = tk.StringVar(value="频率")
        self.scan2d_p1_mode_var     = tk.StringVar(value="线性")
        self.scan2d_p1_start_var    = tk.StringVar(value="100")
        self.scan2d_p1_stop_var     = tk.StringVar(value="10000")
        self.scan2d_p1_step_var     = tk.StringVar(value="100")
        self.scan2d_p1_points_var   = tk.StringVar(value="")
        # 参数2
        self.scan2d_p2_param_var    = tk.StringVar(value="电平")
        self.scan2d_p2_mode_var     = tk.StringVar(value="线性")
        self.scan2d_p2_start_var    = tk.StringVar(value="0.5")
        self.scan2d_p2_stop_var     = tk.StringVar(value="2.0")
        self.scan2d_p2_step_var     = tk.StringVar(value="0.5")
        self.scan2d_p2_points_var   = tk.StringVar(value="")
        # 扫描设置
        self.scan2d_dwell_var       = tk.StringVar(value="0.5")
        # LCR 测量参数
        self.scan2d_primary_var     = tk.StringVar(value="电容(C)")
        self.scan2d_secondary_var   = tk.StringVar(value="损耗因子(D)")
        self.scan2d_speed_var       = tk.StringVar(value="MED")
        self.scan2d_range_var       = tk.StringVar(value="AUTO")
        self.scan2d_bias_var        = tk.StringVar(value="0.0")
        self.scan2d_avg_var         = tk.StringVar(value="1")
        self.scan2d_delay_var       = tk.StringVar(value="0.0")
        self.scan2d_dp_ch_var       = tk.StringVar(value="CH1")
        # 图像预览类型
        self.scan2d_plot_type_var   = tk.StringVar(value="热图")
        # 数据缓存
        self.scan2d_data: dict = {}
        self._scan2d_stop_flag = False

        # 状态
        self.status_var   = tk.StringVar(value="就绪")
        self.dp_status_var  = tk.StringVar(value="未连接")
        self.lcr_status_var = tk.StringVar(value="未连接")
        self.tc_status_var  = tk.StringVar(value="未连接 (模拟)")

        self._build_ui()
        self._append_log("综合控制面板已启动，请连接仪器后操作。")

    # ==================== 辅助方法 ====================

    def _append_log(self, msg: str) -> None:
        try:
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        except RuntimeError:
            pass

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", "end")

    def _set_single_result(self, text: str) -> None:
        self.single_result_text.delete("1.0", "end")
        self.single_result_text.insert("1.0", text)

    def _export_single_result_txt(self) -> None:
        """将当前测量结果文本导出为 TXT 文件。"""
        content = self.single_result_text.get("1.0", "end").strip()
        if not content:
            messagebox.showinfo("无数据", "没有可导出的测量结果")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialfile=f"measurement_result_{time.strftime('%Y%m%d_%H%M%S')}.txt",
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(content + "\n")
            self._append_log(f"测量结果已导出: {path}")
            messagebox.showinfo("导出成功", f"测量结果已导出到:\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    def _threadsafe(self, fn: Callable[[], None]) -> None:
        self.after(0, fn)