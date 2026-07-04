"""双参数扫频功能。

双参数扫频支持同时扫描两个参数（如频率和电平），生成二维数据网格。
数据可以导出为 TXT 格式，兼容 Mathematica 导入。
支持生成 2D 热图/等高线图和 3D 曲面图预览。

双参数扫频数据格式（TXT）：
    # 双参数扫频数据
    # 参数1: 频率 (Hz)
    # 参数2: 电平 (V)
    # 测量参数: C (pF)
    # 参数1值列表: 100, 200, 300, ...
    # 参数2值列表: 0.5, 1.0, 1.5, ...
    # 数据矩阵 (行=参数1, 列=参数2):
    1.23  2.34  3.45  ...
    4.56  5.67  6.78  ...
    ...
"""

from __future__ import annotations

import csv
import math
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from gui_pages import LCR_PARAM_MAP
from typing import Any, Callable


# ==================== 双参数扫描参数说明 ====================

PARAM2D_INFO: dict[str, dict[str, str]] = {
    "频率": {"unit": "Hz", "desc": "LCR测试信号频率，范围通常 20Hz~1MHz"},
    "电平": {"unit": "V",  "desc": "LCR测试信号电平（电压幅度），范围通常 0.01V~5V"},
    "偏压": {"unit": "V",  "desc": "LCR直流偏置电压，用于叠加在测试信号上"},
    "电压": {"unit": "V",  "desc": "DP800输出电压，范围取决于通道规格"},
    "电流": {"unit": "A",  "desc": "DP800输出电流，范围取决于通道规格"},
}

MODE2D_INFO: dict[str, str] = {
    "线性": "线性扫描：等步长递增/递减",
    "对数": "对数扫描：等比例递增，适合宽范围扫频",
}

PLOT_TYPE_INFO: dict[str, str] = {
    "热图": "2D 热图：颜色表示测量值大小，直观显示参数关系",
    "等高线": "2D 等高线图：等值线表示测量值分布",
    "3D曲面": "3D 曲面图：三维视角观察参数与测量值的关系",
}


def _update_scan2d_hints(self) -> None:
    """更新双参数扫频界面的提示信息。"""
    for prefix in ("p1", "p2"):
        param = getattr(self, f"scan2d_{prefix}_param_var").get()
        info = PARAM2D_INFO.get(param, {"unit": "", "desc": ""})
        getattr(self, f"scan2d_{prefix}_hint").set(info["desc"])
        getattr(self, f"scan2d_{prefix}_start_unit").set(info["unit"])
        getattr(self, f"scan2d_{prefix}_stop_unit").set(info["unit"])
        mode = getattr(self, f"scan2d_{prefix}_mode_var").get()
        getattr(self, f"scan2d_{prefix}_step_unit").set(
            info["unit"] if mode == "线性" else "倍率")
        getattr(self, f"scan2d_{prefix}_mode_hint").set(
            MODE2D_INFO.get(mode, ""))


def _update_scan2d_points(self, prefix: str = "p1") -> None:
    """计算并显示指定参数轴的扫描点数。"""
    try:
        start = float(getattr(self, f"scan2d_{prefix}_start_var").get().strip())
        stop = float(getattr(self, f"scan2d_{prefix}_stop_var").get().strip())
        step = float(getattr(self, f"scan2d_{prefix}_step_var").get().strip())
        mode = getattr(self, f"scan2d_{prefix}_mode_var").get()

        if step <= 0:
            getattr(self, f"scan2d_{prefix}_points_var").set("步长需>0")
            return

        if mode == "线性":
            n = int(abs((stop - start) / step)) + 1
        else:  # 对数
            if start <= 0 or stop <= 0:
                getattr(self, f"scan2d_{prefix}_points_var").set("需正数")
                return
            ratio = stop / start
            n = int(math.log(ratio) / math.log(step)) + 1

        n = max(1, min(n, 500))  # 双参数扫描限制更严格
        getattr(self, f"scan2d_{prefix}_points_var").set(str(n))
    except (ValueError, ZeroDivisionError):
        getattr(self, f"scan2d_{prefix}_points_var").set("")


def _gen_scan2d_values(self, prefix: str) -> list[float]:
    """生成指定轴的扫描值列表。

    Args:
        prefix: "p1" 或 "p2"，表示参数1或参数2

    Returns:
        扫描值列表

    Raises:
        ValueError: 参数无效时抛出
    """
    start = float(getattr(self, f"scan2d_{prefix}_start_var").get().strip())
    stop = float(getattr(self, f"scan2d_{prefix}_stop_var").get().strip())
    step = float(getattr(self, f"scan2d_{prefix}_step_var").get().strip())
    mode = getattr(self, f"scan2d_{prefix}_mode_var").get()

    if step <= 0:
        raise ValueError("步长必须大于0")

    vals: list[float] = []

    if mode == "线性":
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
        if vals and abs(vals[-1] - stop) > 1e-9:
            vals.append(float(stop))
    else:
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
        if vals and abs(vals[-1] - stop) / max(abs(stop), 1e-12) > 1e-6:
            vals.append(float(stop))

    if not vals:
        vals = [float(start)]

    return vals


def _export_scan2d_txt(self) -> None:
    """将双参数扫描数据导出为 TXT 格式（兼容 Mathematica 导入）。"""
    if not hasattr(self, 'scan2d_data') or not self.scan2d_data:
        messagebox.showinfo("无数据", "没有可导出的双参数扫描数据")
        return

    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("文本文件", "*.txt"), ("CSV", "*.csv")])
    if not path:
        return

    try:
        data = self.scan2d_data
        p1_param = data.get("p1_param", "参数1")
        p2_param = data.get("p2_param", "参数2")
        p1_unit = data.get("p1_unit", "")
        p2_unit = data.get("p2_unit", "")
        meas_param = data.get("meas_param", "测量值")
        p1_vals = data.get("p1_vals", [])
        p2_vals = data.get("p2_vals", [])
        matrix_p = data.get("matrix_p", [])  # 主参数矩阵
        matrix_s = data.get("matrix_s", [])  # 副参数矩阵

        with open(path, "w", encoding="utf-8-sig") as f:
            f.write("# 双参数扫频数据\n")
            f.write(f"# 参数1: {p1_param} ({p1_unit})\n")
            f.write(f"# 参数2: {p2_param} ({p2_unit})\n")
            f.write(f"# 主测量参数: {meas_param}\n")
            f.write(f"# 副测量参数: {data.get('meas_secondary', '')}\n")
            f.write(f"# 参数1值列表: {', '.join(f'{v:.6g}' for v in p1_vals)}\n")
            f.write(f"# 参数2值列表: {', '.join(f'{v:.6g}' for v in p2_vals)}\n")
            f.write(f"# 数据矩阵 (行=参数1, 列=参数2):\n")
            f.write("# [主参数矩阵]\n")
            for row in matrix_p:
                f.write("  ".join(f"{v:.6g}" for v in row) + "\n")
            if matrix_s:
                f.write("# [副参数矩阵]\n")
                for row in matrix_s:
                    f.write("  ".join(f"{v:.6g}" for v in row) + "\n")

        self._append_log(f"双参数数据已导出: {path}")
        messagebox.showinfo("导出成功",
                            f"数据已导出到:\n{path}\n\n"
                            f"可在 Mathematica 中用以下命令导入:\n"
                            f"Import[\"{os.path.basename(path)}\", \"Table\"]")
    except Exception as e:
        messagebox.showerror("导出失败", str(e))


def _preview_scan2d_plot(self) -> None:
    """生成双参数扫描数据的图像预览（热图/等高线/3D曲面）。"""
    if not hasattr(self, 'scan2d_data') or not self.scan2d_data:
        messagebox.showinfo("无数据", "没有可预览的双参数扫描数据")
        return

    try:
        import matplotlib.pyplot as plt
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    except ImportError:
        messagebox.showerror("缺少依赖", "需要安装 matplotlib：pip install matplotlib")
        return

    data = self.scan2d_data
    p1_vals = data.get("p1_vals", [])
    p2_vals = data.get("p2_vals", [])
    matrix_p = data.get("matrix_p", [])
    matrix_s = data.get("matrix_s", [])
    p1_param = data.get("p1_param", "参数1")
    p2_param = data.get("p2_param", "参数2")
    p1_unit = data.get("p1_unit", "")
    p2_unit = data.get("p2_unit", "")
    meas_param = data.get("meas_param", "测量值")
    meas_secondary = data.get("meas_secondary", "")
    plot_type = self.scan2d_plot_type_var.get()

    if not p1_vals or not p2_vals or not matrix_p:
        messagebox.showinfo("无数据", "数据不完整，无法生成预览")
        return

    # 创建预览窗口
    preview_win = tk.Toplevel(self)
    preview_win.title("双参数扫频图像预览")
    preview_win.geometry("900x700")
    preview_win.transient(self)
    preview_win.grab_set()

    # 创建 Figure
    fig = Figure(figsize=(8, 6), dpi=100)

    if plot_type == "3D曲面":
        from mpl_toolkits.mplot3d import Axes3D
        ax = fig.add_subplot(111, projection="3d")
        X, Y = [list(p1_vals) for _ in p2_vals], [[v] * len(p1_vals) for v in p2_vals]
        Z = matrix_p
        surf = ax.plot_surface(X, Y, Z, cmap="viridis", edgecolor="none", alpha=0.9)
        ax.set_xlabel(f"{p1_param} ({p1_unit})")
        ax.set_ylabel(f"{p2_param} ({p2_unit})")
        ax.set_zlabel(meas_param)
        fig.colorbar(surf, ax=ax, shrink=0.6, aspect=20)
        ax.set_title(f"双参数扫频 3D 曲面图\n{p1_param} vs {p2_param}")

        # 如果有副参数，添加第二个子图
        if matrix_s:
            ax2 = fig.add_subplot(122, projection="3d")
            surf2 = ax2.plot_surface(X, Y, matrix_s, cmap="plasma", edgecolor="none", alpha=0.9)
            ax2.set_xlabel(f"{p1_param} ({p1_unit})")
            ax2.set_ylabel(f"{p2_param} ({p2_unit})")
            ax2.set_zlabel(meas_secondary)
            fig.colorbar(surf2, ax=ax2, shrink=0.6, aspect=20)
            ax2.set_title(f"双参数扫频 3D 曲面图\n{meas_secondary}")
            fig.subplots_adjust(wspace=0.3)

    elif plot_type == "等高线":
        ax = fig.add_subplot(111)
        X, Y = [list(p1_vals) for _ in p2_vals], [[v] * len(p1_vals) for v in p2_vals]
        Z = matrix_p
        contour = ax.contourf(X, Y, Z, levels=20, cmap="viridis")
        ax.contour(X, Y, Z, levels=10, colors="white", linewidths=0.5, alpha=0.5)
        ax.set_xlabel(f"{p1_param} ({p1_unit})")
        ax.set_ylabel(f"{p2_param} ({p2_unit})")
        fig.colorbar(contour, ax=ax, label=meas_param)
        ax.set_title(f"双参数扫频等高线图\n{p1_param} vs {p2_param}")

        if matrix_s:
            ax2 = fig.add_subplot(122)
            contour2 = ax2.contourf(X, Y, matrix_s, levels=20, cmap="plasma")
            ax2.contour(X, Y, matrix_s, levels=10, colors="white", linewidths=0.5, alpha=0.5)
            ax2.set_xlabel(f"{p1_param} ({p1_unit})")
            ax2.set_ylabel(f"{p2_param} ({p2_unit})")
            fig.colorbar(contour2, ax=ax2, label=meas_secondary)
            ax2.set_title(f"双参数扫频等高线图\n{meas_secondary}")
            fig.subplots_adjust(wspace=0.3)

    else:  # 热图
        ax = fig.add_subplot(111)
        extent = [p1_vals[0], p1_vals[-1], p2_vals[0], p2_vals[-1]]
        im = ax.imshow(matrix_p, aspect="auto", cmap="viridis",
                       extent=extent, origin="lower",
                       interpolation="bilinear")
        ax.set_xlabel(f"{p1_param} ({p1_unit})")
        ax.set_ylabel(f"{p2_param} ({p2_unit})")
        fig.colorbar(im, ax=ax, label=meas_param)
        ax.set_title(f"双参数扫频热图\n{p1_param} vs {p2_param}")

        if matrix_s:
            ax2 = fig.add_subplot(122)
            im2 = ax2.imshow(matrix_s, aspect="auto", cmap="plasma",
                            extent=extent, origin="lower",
                            interpolation="bilinear")
            ax2.set_xlabel(f"{p1_param} ({p1_unit})")
            ax2.set_ylabel(f"{p2_param} ({p2_unit})")
            fig.colorbar(im2, ax=ax2, label=meas_secondary)
            ax2.set_title(f"双参数扫频热图\n{meas_secondary}")
            fig.subplots_adjust(wspace=0.3)

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=preview_win)
    canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
    canvas.draw()

    # 添加关闭按钮
    ttk.Button(preview_win, text="关闭",
               command=preview_win.destroy).pack(pady=(0, 8))


def _stop_scan2d(self) -> None:
    """发送停止双参数扫描信号。"""
    self._scan2d_stop_flag = True
    self._append_log("双参数扫描停止信号已发送")


def _clear_scan2d(self) -> None:
    """清空双参数扫描数据和图表。"""
    self.scan2d_data = {}
    self.scan2d_table.clear()
    self.scan2d_info_var.set("")
    self._append_log("双参数扫描数据已清空")


def _start_scan2d(self) -> None:
    """开始双参数扫描。

    外层循环遍历参数1，内层循环遍历参数2，生成二维数据网格。
    支持扫描过程中停止、实时显示数据和进度。
    """
    inst = self.scan2d_instrument_var.get()
    if inst == "LCR" and not self.lcr_inst:
        messagebox.showwarning("未连接", "请先连接 LCR")
        return
    if inst == "DP800" and not self.dp_inst:
        messagebox.showwarning("未连接", "请先连接 DP800")
        return

    def work():
        self._scan2d_stop_flag = False
        self._threadsafe(lambda: self.scan2d_start_btn.config(state="disabled"))
        self._threadsafe(lambda: self.scan2d_stop_btn.config(state="normal"))
        self._threadsafe(lambda: self.scan2d_progress.start(10))
        try:
            # 读取参数
            p1_param = self.scan2d_p1_param_var.get()
            p2_param = self.scan2d_p2_param_var.get()
            dwell = float(self.scan2d_dwell_var.get().strip())
            pri = self.scan2d_primary_var.get()
            sec = self.scan2d_secondary_var.get()

            # 生成扫描值
            p1_vals = _gen_scan2d_values(self, "p1")
            p2_vals = _gen_scan2d_values(self, "p2")

            total = len(p1_vals) * len(p2_vals)
            self._threadsafe(lambda: self.scan2d_progress.config(mode="determinate", maximum=total))

            # 读取高级选项
            avg_count = max(1, int(float(self.scan2d_avg_var.get().strip())))
            delay = float(self.scan2d_delay_var.get().strip())

            # 初始化数据矩阵
            matrix_p: list[list[float]] = []
            matrix_s: list[list[float]] = []
            self.scan2d_table.clear()
            self.scan2d_table.set_columns(["#", f"{p1_param}", f"{p2_param}",
                                           f"{pri}", f"{sec}"])

            if inst == "LCR":
                lcr = self.lcr_inst
                lcr.set_primary_param(LCR_PARAM_MAP.get(pri, pri))
                lcr.set_secondary_param(LCR_PARAM_MAP.get(sec, sec))
                lcr.set_measurement_speed(self.scan2d_speed_var.get())
                lcr.set_auto_range(self.scan2d_range_var.get() == "AUTO")
                bias_val = float(self.scan2d_bias_var.get().strip())
                lcr.set_dc_bias(bias_val, enable=(abs(bias_val) > 1e-9))
                lcr.set_averaging(avg_count)
                lcr.set_trigger_delay(delay)

                for i, v1 in enumerate(p1_vals):
                    if self._scan2d_stop_flag:
                        break
                    row_p: list[float] = []
                    row_s: list[float] = []

                    # 设置参数1
                    if p1_param == "频率":
                        lcr.set_frequency(v1)
                    elif p1_param == "电平":
                        lcr.set_voltage_level(v1)
                    elif p1_param == "偏压":
                        lcr.set_dc_bias(v1, enable=(abs(v1) > 1e-9))

                    time.sleep(max(0, dwell * 0.3))  # 参数1切换后等待

                    for j, v2 in enumerate(p2_vals):
                        if self._scan2d_stop_flag:
                            break

                        # 设置参数2
                        if p2_param == "频率":
                            lcr.set_frequency(v2)
                        elif p2_param == "电平":
                            lcr.set_voltage_level(v2)
                        elif p2_param == "偏压":
                            lcr.set_dc_bias(v2, enable=(abs(v2) > 1e-9))

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

                        row_p.append(float(p))
                        row_s.append(float(s))

                        idx = i * len(p2_vals) + j + 1
                        self._threadsafe(
                            lambda idx=idx, v1=v1, v2=v2, p=p, s=s:
                            self.scan2d_table.add_row(
                                [str(idx), f"{v1:.6g}", f"{v2:.6g}",
                                 f"{p:.6g}", f"{s:.6g}"]))
                        self._threadsafe(
                            lambda idx=idx, total=total:
                            self.scan2d_info_var.set(
                                f"测量点 {idx}/{total}: {p1_param}={v1:.6g}, {p2_param}={v2:.6g}"))
                        self._threadsafe(
                            lambda idx=idx:
                            self.scan2d_progress.step(1))

                    matrix_p.append(row_p)
                    matrix_s.append(row_s)

            else:  # DP800
                dp = self.dp_inst
                ch = self.scan2d_dp_ch_var.get()

                for i, v1 in enumerate(p1_vals):
                    if self._scan2d_stop_flag:
                        break
                    row_p: list[float] = []
                    row_s: list[float] = []

                    # 设置参数1
                    if p1_param == "电压":
                        dp.set_voltage(v1, ch)
                    elif p1_param == "电流":
                        dp.set_current(v1, ch)

                    time.sleep(max(0, dwell * 0.3))

                    for j, v2 in enumerate(p2_vals):
                        if self._scan2d_stop_flag:
                            break

                        # 设置参数2
                        if p2_param == "电压":
                            dp.set_voltage(v2, ch)
                        elif p2_param == "电流":
                            dp.set_current(v2, ch)

                        time.sleep(max(0, dwell))

                        mv_sum, mc_sum = 0.0, 0.0
                        for _ in range(avg_count):
                            mv, mc, _ = dp.measure_all(ch)
                            mv_sum += mv
                            mc_sum += mc
                        mv = mv_sum / avg_count
                        mc = mc_sum / avg_count

                        row_p.append(float(mv))
                        row_s.append(float(mc))

                        idx = i * len(p2_vals) + j + 1
                        self._threadsafe(
                            lambda idx=idx, v1=v1, v2=v2, mv=mv, mc=mc:
                            self.scan2d_table.add_row(
                                [str(idx), f"{v1:.6g}", f"{v2:.6g}",
                                 f"{mv:.6g}", f"{mc:.6g}"]))
                        self._threadsafe(
                            lambda idx=idx, total=total:
                            self.scan2d_info_var.set(
                                f"测量点 {idx}/{total}: {p1_param}={v1:.6g}, {p2_param}={v2:.6g}"))
                        self._threadsafe(
                            lambda idx=idx:
                            self.scan2d_progress.step(1))

                    matrix_p.append(row_p)
                    matrix_s.append(row_s)

            # 保存数据
            self.scan2d_data = {
                "p1_param": p1_param,
                "p2_param": p2_param,
                "p1_unit": PARAM2D_INFO.get(p1_param, {}).get("unit", ""),
                "p2_unit": PARAM2D_INFO.get(p2_param, {}).get("unit", ""),
                "meas_param": pri,
                "meas_secondary": sec,
                "p1_vals": p1_vals,
                "p2_vals": p2_vals,
                "matrix_p": matrix_p,
                "matrix_s": matrix_s,
            }

            if not self._scan2d_stop_flag:
                self._threadsafe(
                    lambda: self._append_log(
                        f"双参数扫描完成: {len(p1_vals)}x{len(p2_vals)} = {total} 个点"))
                self._threadsafe(
                    lambda: messagebox.showinfo(
                        "扫描完成",
                        f"双参数扫描完成！\n"
                        f"参数1 ({p1_param}): {len(p1_vals)} 个点\n"
                        f"参数2 ({p2_param}): {len(p2_vals)} 个点\n"
                        f"总计: {total} 个测量点\n\n"
                        f"可使用「导出TXT」导出为 Mathematica 兼容格式\n"
                        f"可使用「图像预览」查看热图/等高线/3D曲面"))

        except Exception as e:
            self._threadsafe(lambda: messagebox.showerror("双参数扫描失败", str(e)))
            self._threadsafe(lambda: self._append_log(f"双参数扫描错误: {e}"))
        finally:
            self._threadsafe(lambda: self.scan2d_start_btn.config(state="normal"))
            self._threadsafe(lambda: self.scan2d_stop_btn.config(state="disabled"))
            self._threadsafe(lambda: self.scan2d_progress.stop())
            self._threadsafe(lambda: self.scan2d_progress.config(mode="indeterminate"))

    threading.Thread(target=work, daemon=True).start()