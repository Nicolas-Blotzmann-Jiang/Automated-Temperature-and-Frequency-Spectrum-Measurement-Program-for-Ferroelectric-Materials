"""UI 构建方法 — 供 App 类混用。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from gui_pages import build_single_page, build_scan_page, build_scan2d_page


def build_ui(self) -> None:
    self.columnconfigure(0, weight=1)
    self.rowconfigure(1, weight=1)

    header = ttk.Frame(self, padding=(16, 12, 16, 6))
    header.grid(row=0, column=0, sticky="ew")
    ttk.Label(header, text="综合仪器控制面板",
              font=("", 18, "bold")).pack(side="left")
    ttk.Label(header, text="DC电源 / LCR表 / 控温仪",
              font=("", 10)).pack(side="left", padx=(12, 0))

    body = ttk.Frame(self, padding=(12, 4, 12, 12))
    body.grid(row=1, column=0, sticky="nsew")
    body.columnconfigure(0, weight=1)
    body.rowconfigure(0, weight=1)

    nb = ttk.Notebook(body)
    nb.grid(row=0, column=0, sticky="nsew")

    pcon = ttk.Frame(nb); psin = ttk.Frame(nb); psca = ttk.Frame(nb); psca2d = ttk.Frame(nb)
    nb.add(pcon, text="  仪器连接  ")
    nb.add(psin, text="  单次测量  ")
    nb.add(psca, text="  参数扫描  ")
    nb.add(psca2d, text="  双参数扫描  ")

    build_connect_page(self, pcon)
    build_single_page(self, psin)
    build_scan_page(self, psca)
    build_scan2d_page(self, psca2d)


def build_connect_page(self, parent: ttk.Frame) -> None:
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=1)
    parent.columnconfigure(2, weight=1)
    parent.rowconfigure(0, weight=0)
    parent.rowconfigure(1, weight=1)

    top = ttk.Frame(parent, padding=(0, 0, 0, 8))
    top.grid(row=0, column=0, columnspan=3, sticky="ew")
    ttk.Button(top, text="自动识别并连接全部仪器",
               command=self._auto_connect_all).pack(side="left")

    # ----- DP800 -----
    f = ttk.LabelFrame(parent, text="DP800 直流电源", padding=12)
    f.grid(row=1, column=0, sticky="nsew", padx=(0, 4))
    ttk.Label(f, text="VISA 地址:").grid(row=0, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.dp_resource_var, width=32).grid(
        row=1, column=0, sticky="ew", pady=2)
    ttk.Label(f, text="超时 (ms):").grid(row=2, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.dp_timeout_var, width=12).grid(
        row=3, column=0, sticky="w", pady=2)
    bf = ttk.Frame(f)
    bf.grid(row=4, column=0, sticky="ew", pady=(8, 0))
    ttk.Button(bf, text="连接",
               command=self._connect_dp).pack(side="left", padx=(0, 4))
    ttk.Button(bf, text="自动连接",
               command=self._auto_connect_all).pack(side="left", padx=(0, 4))
    ttk.Button(bf, text="断开",
               command=self._disconnect_dp).pack(side="left")
    ttk.Label(f, textvariable=self.dp_status_var,
              foreground="gray").grid(row=5, column=0, sticky="w", pady=(4, 0))

    # ----- LCR -----
    f = ttk.LabelFrame(parent, text="ZM237x LCR 表", padding=12)
    f.grid(row=1, column=1, sticky="nsew", padx=4)
    ttk.Label(f, text="VISA 地址:").grid(row=0, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.lcr_resource_var, width=32).grid(
        row=1, column=0, sticky="ew", pady=2)
    ttk.Label(f, text="超时 (ms):").grid(row=2, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.lcr_timeout_var, width=12).grid(
        row=3, column=0, sticky="w", pady=2)
    bf = ttk.Frame(f)
    bf.grid(row=4, column=0, sticky="ew", pady=(8, 0))
    ttk.Button(bf, text="连接",
               command=self._connect_lcr).pack(side="left", padx=(0, 4))
    ttk.Button(bf, text="自动连接",
               command=self._auto_connect_all).pack(side="left", padx=(0, 4))
    ttk.Button(bf, text="断开",
               command=self._disconnect_lcr).pack(side="left")
    ttk.Label(f, textvariable=self.lcr_status_var,
              foreground="gray").grid(row=5, column=0, sticky="w", pady=(4, 0))

    # ----- 控温仪 -----
    f = ttk.LabelFrame(parent, text="控温仪 (模拟)", padding=12)
    f.grid(row=1, column=2, sticky="nsew", padx=(4, 0))
    ttk.Label(f, text="环境温度 (°C):").grid(row=0, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.tc_ambient_var,
              width=10).grid(row=1, column=0, sticky="w", pady=2)
    ttk.Label(f, text="设定点 (°C):").grid(row=2, column=0, sticky="w")
    ttk.Entry(f, textvariable=self.tc_setpoint_var,
              width=10).grid(row=3, column=0, sticky="w", pady=2)
    sf = ttk.LabelFrame(f, text="稳定判定", padding=8)
    sf.grid(row=4, column=0, sticky="ew", pady=(6, 0))
    for i, (lb, vv) in enumerate([
        ("容差 (°C)", self.tc_tol_var), ("稳定 (s)", self.tc_stable_s_var),
        ("轮询 (s)", self.tc_poll_s_var), ("最长等待 (s)", self.tc_max_wait_var)
    ]):
        ttk.Label(sf, text=lb).grid(row=i, column=0, sticky="w", pady=1)
        ttk.Entry(sf, textvariable=vv, width=10).grid(
            row=i, column=1, sticky="w", pady=1, padx=(6, 0))
    bf = ttk.Frame(f)
    bf.grid(row=5, column=0, sticky="ew", pady=(8, 0))
    ttk.Button(bf, text="初始化",
               command=self._init_tc).pack(side="left", padx=(0, 4))
    ttk.Button(bf, text="设为目标温度",
               command=self._set_tc_target).pack(side="left")
    ttk.Label(f, textvariable=self.tc_status_var,
              foreground="gray").grid(row=6, column=0, sticky="w", pady=(4, 0))