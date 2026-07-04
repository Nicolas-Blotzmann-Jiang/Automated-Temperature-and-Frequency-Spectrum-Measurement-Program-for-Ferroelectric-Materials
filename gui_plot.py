from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any


class PlotFrame(ttk.Frame):
    """内嵌 matplotlib 绘图的 Frame，支持双 Y 轴。"""
    def __init__(self, master: tk.Widget, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            from matplotlib.figure import Figure
        except ImportError:
            messagebox.showerror("缺少依赖", "需要安装 matplotlib：pip install matplotlib")
            raise
        self.figure = Figure(figsize=(5, 3.5), dpi=100)
        self.ax = self.figure.add_subplot(111)
        self.ax2 = None  # 右 Y 轴，按需创建
        self.ax.set_xlabel("扫描参数")
        self.ax.set_ylabel("测量值")
        self.ax.grid(True, linestyle="--", alpha=0.6)

        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self.canvas, self, pack_toolbar=False)
        toolbar.pack(side="bottom", fill="x")
        toolbar.update()

    def clear_and_plot(self, xs: list[float], ys: dict[str, list[float]],
                       xlabel: str, ylabel: str) -> None:
        """清除旧图并绘制新曲线。
        
        当 ys 中有 2 个键值对时，自动使用双 Y 轴：
        - 第一个键值对用左 Y 轴（主参数）
        - 第二个键值对用右 Y 轴（副参数）
        各自独立缩放，避免数量级差异导致小参数显示为直线。
        """
        # 清除旧图
        self.ax.clear()
        if self.ax2 is not None:
            # 移除旧的右 Y 轴（通过删除再重建）
            self.figure.delaxes(self.ax2)
            self.ax2 = None

        self.ax.set_xlabel(xlabel)
        self.ax.grid(True, linestyle="--", alpha=0.6)

        if not xs or not ys:
            self.ax.set_ylabel(ylabel)
            self.figure.tight_layout()
            self.canvas.draw()
            return

        items = list(ys.items())

        if len(items) == 2:
            # 双 Y 轴模式
            label1, yvals1 = items[0]
            label2, yvals2 = items[1]

            # 左 Y 轴 - 主参数
            self.ax.set_ylabel(label1, color="C0")
            if yvals1:
                self.ax.plot(xs, yvals1, marker="o", linestyle="-",
                             label=label1, markersize=4, color="C0")
            self.ax.tick_params(axis="y", labelcolor="C0")

            # 右 Y 轴 - 副参数
            self.ax2 = self.ax.twinx()
            self.ax2.set_ylabel(label2, color="C1")
            if yvals2:
                self.ax2.plot(xs, yvals2, marker="s", linestyle="--",
                              label=label2, markersize=4, color="C1")
            self.ax2.tick_params(axis="y", labelcolor="C1")

            # 合并图例
            lines1, labels1 = self.ax.get_legend_handles_labels()
            lines2, labels2 = self.ax2.get_legend_handles_labels()
            self.ax.legend(lines1 + lines2, labels1 + labels2, loc="best")
        else:
            # 单 Y 轴模式（1 个或 3+ 个键值对）
            self.ax.set_ylabel(ylabel)
            for label, yvals in items:
                if yvals:
                    self.ax.plot(xs, yvals, marker="o", linestyle="-",
                                 label=label, markersize=4)
            if len(items) > 1:
                self.ax.legend()

        self.figure.tight_layout()
        self.canvas.draw()
