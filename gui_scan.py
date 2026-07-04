"""参数扫描功能。

扫描参数说明：
- 扫描仪器：选择 LCR 表或 DP800 电源作为扫描设备
- 扫描参数：选择要扫描的仪器参数（频率/电平/偏压/电压/电流）
- 扫描模式：线性（等步长）或对数（等比例）扫描
- 起始/终止：扫描范围的起止值
- 步长：线性模式为绝对步长，对数模式为倍率因子（如 2 表示每点频率翻倍）
- 点数：根据起始/终止/步长自动计算的扫描点数（只读）
- 驻留时间：每个扫描点设置参数后的等待时间，确保仪器稳定
- 主/副参数：LCR 测量的主要和次要参数（如 C-D、L-Q、R-Q 等）
- 速度：LCR 测量速度（SLOW=高精度/慢速，MED=中速，FAST=快速/低精度）
- 量程：LCR 自动或手动量程选择
- 偏压：LCR 直流偏置电压
- 平均：每个点的测量次数，取平均值（1=不平均）
- 延迟：触发后的等待时间
- DP通道：DP800 电源的输出通道
"""

from __future__ import annotations

import csv
import math
import threading
import time
import tkinter as tk
from tkinter import messagebox, filedialog
from gui_pages import LCR_PARAM_MAP


# ==================== 参数说明映射表 ====================

# 各扫描参数对应的：单位、说明
PARAM_INFO: dict[str, dict[str, str]] = {
    "频率": {"unit": "Hz", "desc": "LCR测试信号频率，范围通常 20Hz~1MHz"},
    "电平": {"unit": "V",  "desc": "LCR测试信号电平（电压幅度），范围通常 0.01V~5V"},
    "偏压": {"unit": "V",  "desc": "LCR直流偏置电压，用于叠加在测试信号上"},
    "电压": {"unit": "V",  "desc": "DP800输出电压，范围取决于通道规格"},
    "电流": {"unit": "A",  "desc": "DP800输出电流，范围取决于通道规格"},
}

# 扫描模式说明
MODE_INFO: dict[str, str] = {
    "线性": "线性扫描：等步长递增/递减，适合观察参数随变量的线性变化",
    "对数": "对数扫描：等比例递增，适合宽范围扫频（如频率从10Hz到1MHz）",
}

# 仪器说明
INST_INFO: dict[str, str] = {
    "LCR":  "LCR表：阻抗/电容/电感/电阻等参数测量",
    "DP800": "DP800电源：直流电压/电流输出与测量",
}


def _update_scan_hints(self) -> None:
    """根据当前选择的扫描参数和模式，更新界面上的说明文字和单位。"""
    param = self.scan_param_var.get()
    mode = self.scan_mode_var.get()
    inst = self.scan_instrument_var.get()

    # 更新参数说明和单位
    info = PARAM_INFO.get(param, {"unit": "", "desc": ""})
    self.scan_param_hint.set(info["desc"])
    self.scan_start_unit.set(info["unit"])
    self.scan_stop_unit.set(info["unit"])
    self.scan_step_unit.set(info["unit"] if mode == "线性" else "倍率")

    # 更新模式说明
    self.scan_mode_hint.set(MODE_INFO.get(mode, ""))

    # 更新仪器说明
    self.scan_inst_hint.set(INST_INFO.get(inst, ""))

    # 更新点数显示
    self._update_scan_points()


def _update_scan_points(self) -> None:
    """根据起始/终止/步长自动计算并显示扫描点数。"""
    try:
        start = float(self.scan_start_var.get().strip())
        stop = float(self.scan_stop_var.get().strip())
        step = float(self.scan_step_var.get().strip())
        mode = self.scan_mode_var.get()

        if step <= 0:
            self.scan_points_var.set("步长需>0")
            return

        if mode == "线性":
            n = int(abs((stop - start) / step)) + 1
        else:  # 对数
            if start <= 0 or stop <= 0:
                self.scan_points_var.set("需正数")
                return
            ratio = stop / start
            n = int(math.log(ratio) / math.log(step)) + 1

        n = max(1, min(n, 10000))  # 限制最大点数
        self.scan_points_var.set(str(n))
    except (ValueError, ZeroDivisionError):
        self.scan_points_var.set("")


def _update_scan_params(self) -> None:
    """切换扫描仪器时更新参数选项和界面布局。"""
    inst = self.scan_instrument_var.get()

    if inst == "LCR":
        # LCR 参数选项
        self.scan_param_combo.config(values=["频率","电平","偏压"])
        if self.scan_param_var.get() not in ("频率","电平","偏压"):
            self.scan_param_var.set("频率")
        # 显示 LCR 高级选项，隐藏 DP800 通道
        self.scan_dp_ch_combo.grid_remove()
        # 更新说明
        self._update_scan_hints()
    else:  # DP800
        # DP800 参数选项
        self.scan_param_combo.config(values=["电压","电流"])
        if self.scan_param_var.get() not in ("电压","电流"):
            self.scan_param_var.set("电压")
        # 显示 DP800 通道选择
        self.scan_dp_ch_combo.grid()
        # 更新说明
        self._update_scan_hints()


def _stop_scan(self) -> None:
    """发送停止扫描信号。"""
    self._scan_stop_flag = True
    self._append_log("扫描停止信号已发送")


def _clear_plot(self) -> None:
    """清空扫描数据和图表。"""
    self.scan_x.clear()
    self.scan_y.clear()
    self.scan_table.clear()
    self.plot_frame.ax.clear()
    if self.plot_frame.ax2 is not None:
        self.plot_frame.figure.delaxes(self.plot_frame.ax2)
        self.plot_frame.ax2 = None
    self.plot_frame.figure.tight_layout()
    self.plot_frame.canvas.draw()
    self.scan_info_var.set("")
    self._append_log("图表已清空")


def _gen_scan_values(self) -> list[float]:
    """根据扫描参数生成扫描值列表。

    支持线性扫描和对数扫描两种模式。
    线性模式：从起始值以固定步长递增/递减到终止值。
    对数模式：从起始值以固定倍率递增到终止值。

    Returns:
        扫描值列表

    Raises:
        ValueError: 参数无效时抛出
    """
    start = float(self.scan_start_var.get().strip())
    stop = float(self.scan_stop_var.get().strip())
    step = float(self.scan_step_var.get().strip())
    mode = self.scan_mode_var.get()

    if step <= 0:
        raise ValueError("步长必须大于0")

    vals: list[float] = []

    if mode == "线性":
        # 线性扫描：等步长
        direction = 1 if stop >= start else -1
        step_actual = step * direction
        v = start
        max_n = int(abs((stop - start) / step)) + 3
        for _ in range(max_n):
            if (direction == 1 and v > stop + 1e-12) or \
               (direction == -1 and v < stop - 1e-12):
                break
            vals.append(round(float(v), 10))
            v += step_actual
        # 确保终止值被包含
        if vals and abs(vals[-1] - stop) > 1e-9:
            vals.append(float(stop))
    else:
        # 对数扫描：等比例
        if start <= 0 or stop <= 0:
            raise ValueError("对数扫描要求起始值和终止值均为正数")
        if step <= 1:
            raise ValueError("对数扫描的步长（倍率）必须大于1")
        direction = 1 if stop >= start else -1
        v = start
        while (direction == 1 and v <= stop * 1.0001) or \
              (direction == -1 and v >= stop * 0.9999):
            vals.append(round(float(v), 10))
            v *= step ** direction
        # 确保终止值被包含
        if vals and abs(vals[-1] - stop) / max(abs(stop), 1e-12) > 1e-6:
            vals.append(float(stop))

    if not vals:
        vals = [float(start)]

    return vals


def _start_scan(self) -> None:
    """开始参数扫描。

    根据选择的仪器和参数，依次设置每个扫描点的值，
    等待驻留时间后测量并记录结果。
    支持扫描过程中停止、实时显示数据和图表更新。
    """
    inst = self.scan_instrument_var.get()
    if inst == "LCR" and not self.lcr_inst:
        messagebox.showwarning("未连接", "请先连接 LCR")
        return
    if inst == "DP800" and not self.dp_inst:
        messagebox.showwarning("未连接", "请先连接 DP800")
        return

    def work():
        self._scan_stop_flag = False
        self._threadsafe(lambda: self.scan_button.config(state="disabled"))
        self._threadsafe(lambda: self.scan_stop_button.config(state="normal"))
        self._threadsafe(lambda: self.scan_progress.start(10))
        try:
            param = self.scan_param_var.get()
            dwell = float(self.scan_dwell_var.get().strip())
            values = _gen_scan_values(self)
            pri = self.scan_primary_var.get()
            sec = self.scan_secondary_var.get()
            xs: list[float] = []
            ys_p: list[float] = []
            ys_s: list[float] = []
            self.scan_table.clear()

            # 读取高级选项
            avg_count = max(1, int(float(self.scan_avg_var.get().strip())))
            delay = float(self.scan_delay_var.get().strip())

            if inst == "LCR":
                lcr = self.lcr_inst
                # 配置 LCR 测量参数
                # 先设置基础测量条件（频率、电平），这些值从单次测量页面的变量读取
                lcr.set_frequency(float(self.lcr_freq_var.get().strip()))
                lcr.set_voltage_level(float(self.lcr_level_var.get().strip()))
                # 设置触发源为内部触发
                lcr.set_trigger_source("INT")
                # 设置主/副参数
                lcr.set_primary_param(LCR_PARAM_MAP.get(pri, pri))
                lcr.set_secondary_param(LCR_PARAM_MAP.get(sec, sec))
                lcr.set_measurement_speed(self.scan_speed_var.get())
                lcr.set_auto_range(self.scan_range_var.get() == "AUTO")
                # 如果手动量程，设置一个默认量程值（100Ω）
                if self.scan_range_var.get() != "AUTO":
                    lcr.set_range(100.0)
                # 设置偏压（使用扫描偏压值，非扫描参数时固定）
                bias_val = float(self.scan_bias_var.get().strip())
                lcr.set_dc_bias(bias_val, enable=(abs(bias_val) > 1e-9))
                # 设置平均
                lcr.set_averaging(avg_count)
                # 设置触发延迟
                lcr.set_trigger_delay(delay)

                for i, val in enumerate(values):
                    if self._scan_stop_flag:
                        break
                    info = f"{i+1}/{len(values)}: {param}={val:.6g}"
                    self._threadsafe(lambda: self.scan_info_var.set(info))

                    # 设置扫描参数
                    if param == "频率":
                        lcr.set_frequency(val)
                    elif param == "电平":
                        lcr.set_voltage_level(val)
                    elif param == "偏压":
                        lcr.set_dc_bias(val, enable=(abs(val) > 1e-9))

                    # 驻留等待
                    time.sleep(max(0, dwell))

                    # 测量（多次平均）
                    p_sum, s_sum = 0.0, 0.0
                    for _ in range(avg_count):
                        vals_raw, _ = lcr.measure_once()
                        p_sum += vals_raw[0] if len(vals_raw) >= 1 else 0
                        s_sum += vals_raw[1] if len(vals_raw) >= 2 else 0
                    p = p_sum / avg_count
                    s = s_sum / avg_count

                    xs.append(float(val))
                    ys_p.append(float(p))
                    ys_s.append(float(s))
                    self._threadsafe(
                        lambda i=i+1, vv=val, pp=p, ss=s:
                        self.scan_table.add_row(
                            [str(i), f"{vv:.6g}", f"{pp:.6g}", f"{ss:.6g}"]))
            else:  # DP800
                dp = self.dp_inst
                ch = self.scan_dp_ch_var.get()

                for i, val in enumerate(values):
                    if self._scan_stop_flag:
                        break
                    info = f"{i+1}/{len(values)}: {param}={val:.6g}"
                    self._threadsafe(lambda: self.scan_info_var.set(info))

                    # 设置扫描参数
                    if param == "电压":
                        dp.set_voltage(val, ch)
                    elif param == "电流":
                        dp.set_current(val, ch)

                    # 驻留等待
                    time.sleep(max(0, dwell))

                    # 测量（多次平均）
                    mv_sum, mc_sum = 0.0, 0.0
                    for _ in range(avg_count):
                        mv, mc, _ = dp.measure_all(ch)
                        mv_sum += mv
                        mc_sum += mc
                    mv = mv_sum / avg_count
                    mc = mc_sum / avg_count

                    xs.append(float(val))
                    ys_p.append(float(mv))
                    ys_s.append(float(mc))
                    self._threadsafe(
                        lambda i=i+1, vv=val, mv=mv, mc=mc:
                        self.scan_table.add_row(
                            [str(i), f"{vv:.6g}", f"{mv:.6g}", f"{mc:.6g}"]))

            self.scan_x = xs
            self.scan_y = {pri: ys_p, sec: ys_s}
            if xs:
                self._threadsafe(
                    lambda: self.plot_frame.clear_and_plot(
                        self.scan_x, self.scan_y, param, f"{pri}/{sec}"))
                self._threadsafe(
                    lambda: self._append_log(f"扫描完成: {len(xs)} 个点"))
        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("扫描失败", str(e)))
            self._threadsafe(lambda: self._append_log(f"扫描错误: {e}"))
        finally:
            self._threadsafe(lambda: self.scan_button.config(state="normal"))
            self._threadsafe(lambda: self.scan_stop_button.config(state="disabled"))
            self._threadsafe(lambda: self.scan_progress.stop())

    threading.Thread(target=work, daemon=True).start()


def _export_csv(self) -> None:
    """将扫描数据导出为 CSV 文件。"""
    if not self.scan_x:
        messagebox.showinfo("无数据", "没有可导出的扫描数据")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV", "*.csv")])
    if not path:
        return
    try:
        labels = list(self.scan_y.keys())
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            # 写入扫描参数信息作为注释
            param = self.scan_param_var.get()
            mode = self.scan_mode_var.get()
            w.writerow([f"# 扫描参数: {param}, 模式: {mode}"])
            w.writerow(["扫描值"] + labels)
            for i, x in enumerate(self.scan_x):
                row = [x] + [self.scan_y[k][i]
                             if i < len(self.scan_y[k]) else ""
                             for k in labels]
                w.writerow(row)
        self._append_log(f"数据已导出: {path}")
    except Exception as e:
        messagebox.showerror("导出失败", str(e))


def _export_txt(self) -> None:
    """将扫描数据导出为 TXT 格式文件（带表头和格式说明）。"""
    if not self.scan_x:
        messagebox.showinfo("无数据", "没有可导出的扫描数据")
        return
    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
        initialfile=f"scan_result_{time.strftime('%Y%m%d_%H%M%S')}.txt",
    )
    if not path:
        return
    try:
        labels = list(self.scan_y.keys())
        param = self.scan_param_var.get()
        mode = self.scan_mode_var.get()
        inst = self.scan_instrument_var.get()
        pri = self.scan_primary_var.get()
        sec = self.scan_secondary_var.get()

        with open(path, "w", encoding="utf-8-sig") as f:
            # 文件头
            f.write("=" * 60 + "\n")
            f.write("       仪器参数扫描测量结果\n")
            f.write("=" * 60 + "\n")
            f.write(f"扫描仪器:     {inst}\n")
            f.write(f"扫描参数:     {param}\n")
            f.write(f"扫描模式:     {mode}\n")
            f.write(f"测量参数:     {pri} / {sec}\n")
            f.write(f"扫描点数:     {len(self.scan_x)}\n")
            f.write(f"导出时间:     {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n")
            f.write("\n")

            # 数据表头
            header = f"{'序号':>6}  {'扫描值':>16}  {f'{pri}':>16}  {f'{sec}':>16}"
            f.write(header + "\n")
            f.write("-" * len(header) + "\n")

            # 数据行
            for i, x in enumerate(self.scan_x):
                p_val = self.scan_y[pri][i] if pri in self.scan_y and i < len(self.scan_y[pri]) else ""
                s_val = self.scan_y[sec][i] if sec in self.scan_y and i < len(self.scan_y[sec]) else ""
                line = f"{i+1:>6}  {x:>16.6g}  {p_val:>16.6g}  {s_val:>16.6g}"
                f.write(line + "\n")

            f.write("\n")
            f.write("=" * 60 + "\n")
            f.write("文件结束\n")

        self._append_log(f"数据已导出TXT: {path}")
        messagebox.showinfo("导出成功", f"扫描结果已导出到:\n{path}")
    except Exception as e:
        messagebox.showerror("导出失败", str(e))
