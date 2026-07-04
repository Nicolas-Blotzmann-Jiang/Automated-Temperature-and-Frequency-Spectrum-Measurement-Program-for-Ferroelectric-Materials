"""单次测量页、扫描页和双参数扫描页的 UI 构建方法。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from gui_plot import PlotFrame
from gui_table import ScanTable


# ==================== LCR 参数列表 ====================
# 主参数（:CALC1:FORM）支持：Z|Y|R|RP|RS|G|C|CP|CS|L|LP|LS|REAL|MLIN
LCR_PRIMARY_PARAMS = ["电容(C)", "电感(L)", "电阻(R)", "阻抗(Z)", "导纳(Y)", "等效串联电阻(ESR)", "电导(G)", "相位角(θ)"]

# 副参数（:CALC2:FORM）支持：Q|D|PHAS|X|B|RS|RP|G|LP|RDC|IMAG|REAL
LCR_SECONDARY_PARAMS = ["损耗因子(D)", "品质因数(Q)", "电抗(X)", "电导(G)", "等效串联电阻(ESR)", "相位角(θ)"]

# 兼容旧代码：完整参数列表
LCR_PARAMS = LCR_PRIMARY_PARAMS + [p for p in LCR_SECONDARY_PARAMS if p not in LCR_PRIMARY_PARAMS]

# LCR 中文参数 → SCPI 字母缩写映射
LCR_PARAM_MAP: dict[str, str] = {
    "电容(C)": "C",
    "电感(L)": "L",
    "电阻(R)": "R",
    "阻抗(Z)": "Z",
    "损耗因子(D)": "D",
    "品质因数(Q)": "Q",
    "等效串联电阻(ESR)": "RS",
    "电抗(X)": "X",
    "电导(G)": "G",
    "导纳(Y)": "Y",
    "相位角(θ)": "PHAS",
}


def build_single_page(self, parent: ttk.Frame) -> None:
    parent.columnconfigure(0, weight=2)
    parent.columnconfigure(1, weight=3)
    parent.rowconfigure(0, weight=1)

    left = ttk.Frame(parent, padding=8)
    left.grid(row=0, column=0, sticky="nsew")
    left.columnconfigure(0, weight=1)

    # DP800
    g = ttk.LabelFrame(left, text="DP800", padding=10)
    g.grid(row=0, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(g, text="通道:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(g, textvariable=self.dp_channel_var,
                 values=("CH1","CH2","CH3"), width=6,
                 state="readonly").grid(row=0, column=1, sticky="w",
                                         padx=(6, 0))
    ttk.Label(g, text="电压 (V):").grid(row=1, column=0, sticky="w",
                                         pady=(4, 0))
    ttk.Entry(g, textvariable=self.dp_voltage_var,
              width=10).grid(row=1, column=1, sticky="w",
                             padx=(6, 0), pady=(4, 0))
    ttk.Label(g, text="电流 (A):").grid(row=2, column=0, sticky="w",
                                         pady=(4, 0))
    ttk.Entry(g, textvariable=self.dp_current_var,
              width=10).grid(row=2, column=1, sticky="w",
                             padx=(6, 0), pady=(4, 0))
    br = ttk.Frame(g)
    br.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
    ttk.Button(br, text="测量",
               command=self._dp_measure).pack(side="left", padx=(0, 4))
    ttk.Button(br, text="ON",
               command=lambda: self._dp_output(True)).pack(side="left",
                                                            padx=(0, 4))
    ttk.Button(br, text="OFF",
               command=lambda: self._dp_output(False)).pack(side="left")

    # LCR
    g = ttk.LabelFrame(left, text="LCR 表", padding=10)
    g.grid(row=1, column=0, sticky="ew", pady=(0, 8))
    ttk.Label(g, text="频率 (Hz):").grid(row=0, column=0, sticky="w")
    ttk.Entry(g, textvariable=self.lcr_freq_var,
              width=10).grid(row=0, column=1, sticky="w", padx=(6, 0))
    ttk.Label(g, text="电平 (V):").grid(row=1, column=0, sticky="w",
                                         pady=(4, 0))
    ttk.Entry(g, textvariable=self.lcr_level_var,
              width=10).grid(row=1, column=1, sticky="w",
                             padx=(6, 0), pady=(4, 0))
    ttk.Label(g, text="主/副:").grid(row=2, column=0, sticky="w",
                                      pady=(4, 0))
    pr = ttk.Frame(g)
    pr.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(4, 0))
    ttk.Combobox(pr, textvariable=self.lcr_primary_var,
                 values=LCR_PARAMS, width=5,
                 state="readonly").pack(side="left", padx=(0, 4))
    ttk.Combobox(pr, textvariable=self.lcr_secondary_var,
                 values=LCR_SECONDARY_PARAMS, width=5,
                 state="readonly").pack(side="left")
    ttk.Label(g, text="速度:").grid(row=3, column=0, sticky="w",
                                     pady=(4, 0))
    ttk.Combobox(g, textvariable=self.lcr_speed_var,
                 values=("SLOW","MED","FAST"), width=6,
                 state="readonly").grid(row=3, column=1, sticky="w",
                                        padx=(6, 0), pady=(4, 0))
    ttk.Label(g, text="量程:").grid(row=4, column=0, sticky="w",
                                     pady=(4, 0))
    rf = ttk.Frame(g)
    rf.grid(row=4, column=1, sticky="w", padx=(6, 0), pady=(4, 0))
    ttk.Radiobutton(rf, text="自动", variable=self.lcr_range_var,
                    value="AUTO").pack(side="left")
    ttk.Radiobutton(rf, text="手动", variable=self.lcr_range_var,
                    value="MANUAL").pack(side="left", padx=(6, 0))
    ttk.Label(g, text="偏压 (V):").grid(row=5, column=0, sticky="w",
                                         pady=(4, 0))
    ttk.Entry(g, textvariable=self.lcr_bias_var,
              width=10).grid(row=5, column=1, sticky="w",
                             padx=(6, 0), pady=(4, 0))
    ttk.Button(g, text="测量", command=self._lcr_measure).grid(
        row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    # 控温仪
    g = ttk.LabelFrame(left, text="控温仪", padding=10)
    g.grid(row=2, column=0, sticky="ew")
    ttk.Button(g, text="读取温度",
               command=self._tc_read).pack(fill="x")
    ttk.Button(g, text="等待稳定",
               command=self._tc_wait_stable).pack(fill="x", pady=(4, 0))

    # 右侧结果/日志
    right = ttk.Frame(parent, padding=8)
    right.grid(row=0, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=3)
    right.rowconfigure(1, weight=1)

    sr = ttk.LabelFrame(right, text="测量结果", padding=8)
    sr.grid(row=0, column=0, sticky="nsew")
    sr.columnconfigure(0, weight=1); sr.rowconfigure(0, weight=1)
    self.single_result_text = tk.Text(sr, wrap="word",
                                       font=("Consolas", 10))
    self.single_result_text.grid(row=0, column=0, sticky="nsew")
    ttk.Scrollbar(sr, orient="vertical",
                  command=self.single_result_text.yview).grid(
                      row=0, column=1, sticky="ns")
    ttk.Button(sr, text="导出TXT格式测量结果",
               command=self._export_single_result_txt).grid(
                   row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    lf = ttk.LabelFrame(right, text="系统日志", padding=8)
    lf.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
    lf.columnconfigure(0, weight=1); lf.rowconfigure(0, weight=1)
    self.log_text = tk.Text(lf, wrap="word", height=8,
                             font=("Consolas", 9))
    self.log_text.grid(row=0, column=0, sticky="nsew")
    ttk.Scrollbar(lf, orient="vertical",
                  command=self.log_text.yview).grid(
                      row=0, column=1, sticky="ns")
    ttk.Button(lf, text="清空",
               command=self._clear_log).grid(row=0, column=2,
                                              sticky="ne", padx=(4, 0))


def build_scan_page(self, parent: ttk.Frame) -> None:
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=0)
    parent.rowconfigure(0, weight=1)

    left = ttk.Frame(parent, padding=8)
    left.grid(row=0, column=0, sticky="nsew")
    left.columnconfigure(0, weight=1)

    # ========== 扫描仪器 ==========
    ig = ttk.LabelFrame(left, text="扫描仪器", padding=10)
    ig.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    ig.columnconfigure(2, weight=1)
    ttk.Label(ig, text="仪器:").grid(row=0, column=0, sticky="w")
    cb = ttk.Combobox(ig, textvariable=self.scan_instrument_var,
                      values=("LCR","DP800"), width=8, state="readonly")
    cb.grid(row=0, column=1, sticky="w", padx=(6, 0))
    cb.bind("<<ComboboxSelected>>", lambda _: self._update_scan_params())
    # 仪器说明
    self.scan_inst_hint = tk.StringVar(value="LCR表：阻抗/电容/电感等参数测量")
    ttk.Label(ig, textvariable=self.scan_inst_hint,
              foreground="gray", font=("", 8)).grid(row=0, column=2, sticky="w", padx=(10, 0))

    # ========== 扫描参数 ==========
    pg = ttk.LabelFrame(left, text="扫描参数", padding=10)
    pg.grid(row=1, column=0, sticky="ew", pady=(0, 6))
    pg.columnconfigure(1, weight=1)
    pg.columnconfigure(3, weight=1)

    # 第0行：扫描参数选择
    ttk.Label(pg, text="参数:").grid(row=0, column=0, sticky="w")
    self.scan_param_combo = ttk.Combobox(
        pg, textvariable=self.scan_param_var,
        values=["频率","电平","偏压"], width=10, state="readonly")
    self.scan_param_combo.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=2)
    self.scan_param_combo.bind("<<ComboboxSelected>>", lambda _: self._update_scan_hints())
    # 参数说明
    self.scan_param_hint = tk.StringVar(value="LCR测试信号频率，单位：Hz")
    ttk.Label(pg, textvariable=self.scan_param_hint,
              foreground="gray", font=("", 8)).grid(row=0, column=2, columnspan=2, sticky="w", padx=(10, 0))

    # 第1行：扫描模式
    ttk.Label(pg, text="模式:").grid(row=1, column=0, sticky="w")
    mode_frame = ttk.Frame(pg)
    mode_frame.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Radiobutton(mode_frame, text="线性", variable=self.scan_mode_var,
                    value="线性", command=self._update_scan_hints).pack(side="left")
    ttk.Radiobutton(mode_frame, text="对数", variable=self.scan_mode_var,
                    value="对数", command=self._update_scan_hints).pack(side="left", padx=(6, 0))
    self.scan_mode_hint = tk.StringVar(value="线性扫描：等步长递增/递减")
    ttk.Label(pg, textvariable=self.scan_mode_hint,
              foreground="gray", font=("", 8)).grid(row=1, column=2, columnspan=2, sticky="w", padx=(10, 0))

    # 第2行：起始值
    ttk.Label(pg, text="起始:").grid(row=2, column=0, sticky="w")
    start_frame = ttk.Frame(pg)
    start_frame.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(start_frame, textvariable=self.scan_start_var, width=12).pack(side="left")
    self.scan_start_unit = tk.StringVar(value="Hz")
    ttk.Label(start_frame, textvariable=self.scan_start_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    # 第3行：终止值
    ttk.Label(pg, text="终止:").grid(row=3, column=0, sticky="w")
    stop_frame = ttk.Frame(pg)
    stop_frame.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(stop_frame, textvariable=self.scan_stop_var, width=12).pack(side="left")
    self.scan_stop_unit = tk.StringVar(value="Hz")
    ttk.Label(stop_frame, textvariable=self.scan_stop_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    # 第4行：步长/点数
    ttk.Label(pg, text="步长:").grid(row=4, column=0, sticky="w")
    step_frame = ttk.Frame(pg)
    step_frame.grid(row=4, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(step_frame, textvariable=self.scan_step_var, width=12).pack(side="left")
    self.scan_step_unit = tk.StringVar(value="Hz")
    ttk.Label(step_frame, textvariable=self.scan_step_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))
    # 自动计算点数
    ttk.Label(pg, text="点数:").grid(row=4, column=2, sticky="w", padx=(10, 0))
    ttk.Entry(pg, textvariable=self.scan_points_var, width=8,
              state="readonly").grid(row=4, column=3, sticky="w", pady=2)

    # 第5行：驻留时间
    ttk.Label(pg, text="驻留 (s):").grid(row=5, column=0, sticky="w")
    dwell_frame = ttk.Frame(pg)
    dwell_frame.grid(row=5, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(dwell_frame, textvariable=self.scan_dwell_var, width=12).pack(side="left")
    ttk.Label(dwell_frame, text="每个点的等待时间",
              foreground="gray", font=("", 8)).pack(side="left", padx=(4, 0))

    # ========== LCR 高级选项 ==========
    lg = ttk.LabelFrame(left, text="LCR 高级选项", padding=10)
    lg.grid(row=2, column=0, sticky="ew", pady=(0, 6))
    lg.columnconfigure(1, weight=1)
    lg.columnconfigure(3, weight=1)

    # 第0行：主/副参数
    ttk.Label(lg, text="主/副:").grid(row=0, column=0, sticky="w")
    pr_frame = ttk.Frame(lg)
    pr_frame.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Combobox(pr_frame, textvariable=self.scan_primary_var,
                 values=LCR_PARAMS, width=6, state="readonly").pack(side="left", padx=(0, 4))
    ttk.Combobox(pr_frame, textvariable=self.scan_secondary_var,
                 values=LCR_SECONDARY_PARAMS, width=6, state="readonly").pack(side="left")

    # 第1行：速度/量程
    ttk.Label(lg, text="速度:").grid(row=1, column=0, sticky="w")
    ttk.Combobox(lg, textvariable=self.scan_speed_var,
                 values=("SLOW","MED","FAST"), width=6, state="readonly").grid(
                     row=1, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="量程:").grid(row=1, column=2, sticky="w", padx=(10, 0))
    range_frame = ttk.Frame(lg)
    range_frame.grid(row=1, column=3, sticky="w", pady=2)
    ttk.Radiobutton(range_frame, text="自动", variable=self.scan_range_var,
                    value="AUTO").pack(side="left")
    ttk.Radiobutton(range_frame, text="手动", variable=self.scan_range_var,
                    value="MANUAL").pack(side="left", padx=(6, 0))

    # 第2行：偏压/平均
    ttk.Label(lg, text="偏压 (V):").grid(row=2, column=0, sticky="w")
    ttk.Entry(lg, textvariable=self.scan_bias_var, width=10).grid(
        row=2, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="平均:").grid(row=2, column=2, sticky="w", padx=(10, 0))
    ttk.Entry(lg, textvariable=self.scan_avg_var, width=6).grid(
        row=2, column=3, sticky="w", pady=2)

    # 第3行：延迟/DP通道
    ttk.Label(lg, text="延迟 (s):").grid(row=3, column=0, sticky="w")
    ttk.Entry(lg, textvariable=self.scan_delay_var, width=10).grid(
        row=3, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="DP通道:").grid(row=3, column=2, sticky="w", padx=(10, 0))
    self.scan_dp_ch_combo = ttk.Combobox(lg, textvariable=self.scan_dp_ch_var,
                                         values=("CH1","CH2","CH3"), width=6, state="readonly")
    self.scan_dp_ch_combo.grid(row=3, column=3, sticky="w", pady=2)
    self.scan_dp_ch_combo.grid_remove()  # 默认隐藏，选择 DP800 时显示

    # ========== 操作按钮 ==========
    btn_frame = ttk.Frame(left)
    btn_frame.grid(row=3, column=0, sticky="ew", pady=(6, 0))
    btn_frame.columnconfigure(0, weight=1)
    btn_frame.columnconfigure(1, weight=1)
    btn_frame.columnconfigure(2, weight=1)
    btn_frame.columnconfigure(3, weight=1)
    btn_frame.columnconfigure(4, weight=1)
    self.scan_button = ttk.Button(btn_frame, text="开始扫描", command=self._start_scan)
    self.scan_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
    self.scan_stop_button = ttk.Button(btn_frame, text="停止", command=self._stop_scan, state="disabled")
    self.scan_stop_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
    ttk.Button(btn_frame, text="清空", command=self._clear_plot).grid(
        row=0, column=2, sticky="ew", padx=(4, 0))
    ttk.Button(btn_frame, text="导出CSV", command=self._export_csv).grid(
        row=0, column=3, sticky="ew", padx=(4, 0))
    ttk.Button(btn_frame, text="导出TXT", command=self._export_txt).grid(
        row=0, column=4, sticky="ew", padx=(4, 0))

    # ========== 进度条 ==========
    self.scan_progress = ttk.Progressbar(left, mode="indeterminate")
    self.scan_progress.grid(row=4, column=0, sticky="ew", pady=(6, 0))

    # ========== 状态信息 ==========
    self.scan_info_var = tk.StringVar(value="")
    ttk.Label(left, textvariable=self.scan_info_var,
              foreground="blue").grid(row=5, column=0, sticky="w", pady=(4, 0))

    # ========== 右侧：图表 + 表格 ==========
    right = ttk.Frame(parent, padding=8)
    right.grid(row=0, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=3)
    right.rowconfigure(1, weight=2)

    # 图表
    self.plot_frame = PlotFrame(right)
    self.plot_frame.grid(row=0, column=0, sticky="nsew")

    # 表格
    self.scan_table = ScanTable(right, columns=["#", "扫描值", "主参数", "副参数"])
    self.scan_table.grid(row=1, column=0, sticky="nsew", pady=(6, 0))


def build_scan2d_page(self, parent: ttk.Frame) -> None:
    parent.columnconfigure(0, weight=1)
    parent.columnconfigure(1, weight=0)
    parent.rowconfigure(0, weight=1)

    left = ttk.Frame(parent, padding=8)
    left.grid(row=0, column=0, sticky="nsew")
    left.columnconfigure(0, weight=1)

    # ========== 双参数扫描仪器 ==========
    ig = ttk.LabelFrame(left, text="双参数扫描仪器", padding=10)
    ig.grid(row=0, column=0, sticky="ew", pady=(0, 6))
    ig.columnconfigure(2, weight=1)
    ttk.Label(ig, text="仪器:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(ig, textvariable=self.scan2d_instrument_var,
                 values=("LCR","DP800"), width=8, state="readonly").grid(
                     row=0, column=1, sticky="w", padx=(6, 0))

    # ========== 参数1 ==========
    p1g = ttk.LabelFrame(left, text="参数1", padding=10)
    p1g.grid(row=1, column=0, sticky="ew", pady=(0, 6))
    p1g.columnconfigure(1, weight=1)
    p1g.columnconfigure(3, weight=1)

    ttk.Label(p1g, text="参数:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(p1g, textvariable=self.scan2d_p1_param_var,
                 values=["频率","电平","偏压"], width=10, state="readonly").grid(
                     row=0, column=1, sticky="w", padx=(6, 0), pady=2)
    self.scan2d_p1_hint = tk.StringVar(value="LCR测试信号频率，单位：Hz")
    ttk.Label(p1g, textvariable=self.scan2d_p1_hint,
              foreground="gray", font=("", 8)).grid(row=0, column=2, columnspan=2, sticky="w", padx=(10, 0))

    ttk.Label(p1g, text="模式:").grid(row=1, column=0, sticky="w")
    mf1 = ttk.Frame(p1g)
    mf1.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Radiobutton(mf1, text="线性", variable=self.scan2d_p1_mode_var,
                    value="线性", command=lambda: self._update_scan2d_hints()).pack(side="left")
    ttk.Radiobutton(mf1, text="对数", variable=self.scan2d_p1_mode_var,
                    value="对数", command=lambda: self._update_scan2d_hints()).pack(side="left", padx=(6, 0))
    self.scan2d_p1_mode_hint = tk.StringVar(value="线性扫描：等步长递增/递减")
    ttk.Label(p1g, textvariable=self.scan2d_p1_mode_hint,
              foreground="gray", font=("", 8)).grid(row=1, column=2, columnspan=2, sticky="w", padx=(10, 0))

    ttk.Label(p1g, text="起始:").grid(row=2, column=0, sticky="w")
    sf1 = ttk.Frame(p1g)
    sf1.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(sf1, textvariable=self.scan2d_p1_start_var, width=12).pack(side="left")
    self.scan2d_p1_start_unit = tk.StringVar(value="Hz")
    ttk.Label(sf1, textvariable=self.scan2d_p1_start_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    ttk.Label(p1g, text="终止:").grid(row=3, column=0, sticky="w")
    stf1 = ttk.Frame(p1g)
    stf1.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(stf1, textvariable=self.scan2d_p1_stop_var, width=12).pack(side="left")
    self.scan2d_p1_stop_unit = tk.StringVar(value="Hz")
    ttk.Label(stf1, textvariable=self.scan2d_p1_stop_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    ttk.Label(p1g, text="步长:").grid(row=4, column=0, sticky="w")
    stpf1 = ttk.Frame(p1g)
    stpf1.grid(row=4, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(stpf1, textvariable=self.scan2d_p1_step_var, width=12).pack(side="left")
    self.scan2d_p1_step_unit = tk.StringVar(value="Hz")
    ttk.Label(stpf1, textvariable=self.scan2d_p1_step_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))
    ttk.Label(p1g, text="点数:").grid(row=4, column=2, sticky="w", padx=(10, 0))
    ttk.Entry(p1g, textvariable=self.scan2d_p1_points_var, width=8,
              state="readonly").grid(row=4, column=3, sticky="w", pady=2)

    # ========== 参数2 ==========
    p2g = ttk.LabelFrame(left, text="参数2", padding=10)
    p2g.grid(row=2, column=0, sticky="ew", pady=(0, 6))
    p2g.columnconfigure(1, weight=1)
    p2g.columnconfigure(3, weight=1)

    ttk.Label(p2g, text="参数:").grid(row=0, column=0, sticky="w")
    ttk.Combobox(p2g, textvariable=self.scan2d_p2_param_var,
                 values=["频率","电平","偏压"], width=10, state="readonly").grid(
                     row=0, column=1, sticky="w", padx=(6, 0), pady=2)
    self.scan2d_p2_hint = tk.StringVar(value="LCR测试信号电平，单位：V")
    ttk.Label(p2g, textvariable=self.scan2d_p2_hint,
              foreground="gray", font=("", 8)).grid(row=0, column=2, columnspan=2, sticky="w", padx=(10, 0))

    ttk.Label(p2g, text="模式:").grid(row=1, column=0, sticky="w")
    mf2 = ttk.Frame(p2g)
    mf2.grid(row=1, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Radiobutton(mf2, text="线性", variable=self.scan2d_p2_mode_var,
                    value="线性", command=lambda: self._update_scan2d_hints()).pack(side="left")
    ttk.Radiobutton(mf2, text="对数", variable=self.scan2d_p2_mode_var,
                    value="对数", command=lambda: self._update_scan2d_hints()).pack(side="left", padx=(6, 0))
    self.scan2d_p2_mode_hint = tk.StringVar(value="线性扫描：等步长递增/递减")
    ttk.Label(p2g, textvariable=self.scan2d_p2_mode_hint,
              foreground="gray", font=("", 8)).grid(row=1, column=2, columnspan=2, sticky="w", padx=(10, 0))

    ttk.Label(p2g, text="起始:").grid(row=2, column=0, sticky="w")
    sf2 = ttk.Frame(p2g)
    sf2.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(sf2, textvariable=self.scan2d_p2_start_var, width=12).pack(side="left")
    self.scan2d_p2_start_unit = tk.StringVar(value="V")
    ttk.Label(sf2, textvariable=self.scan2d_p2_start_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    ttk.Label(p2g, text="终止:").grid(row=3, column=0, sticky="w")
    stf2 = ttk.Frame(p2g)
    stf2.grid(row=3, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(stf2, textvariable=self.scan2d_p2_stop_var, width=12).pack(side="left")
    self.scan2d_p2_stop_unit = tk.StringVar(value="V")
    ttk.Label(stf2, textvariable=self.scan2d_p2_stop_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))

    ttk.Label(p2g, text="步长:").grid(row=4, column=0, sticky="w")
    stpf2 = ttk.Frame(p2g)
    stpf2.grid(row=4, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Entry(stpf2, textvariable=self.scan2d_p2_step_var, width=12).pack(side="left")
    self.scan2d_p2_step_unit = tk.StringVar(value="V")
    ttk.Label(stpf2, textvariable=self.scan2d_p2_step_unit,
              foreground="blue", font=("", 8)).pack(side="left", padx=(4, 0))
    ttk.Label(p2g, text="点数:").grid(row=4, column=2, sticky="w", padx=(10, 0))
    ttk.Entry(p2g, textvariable=self.scan2d_p2_points_var, width=8,
              state="readonly").grid(row=4, column=3, sticky="w", pady=2)

    # ========== 双参数扫描设置 ==========
    sg = ttk.LabelFrame(left, text="扫描设置", padding=10)
    sg.grid(row=3, column=0, sticky="ew", pady=(0, 6))
    sg.columnconfigure(1, weight=1)
    sg.columnconfigure(3, weight=1)

    ttk.Label(sg, text="驻留 (s):").grid(row=0, column=0, sticky="w")
    ttk.Entry(sg, textvariable=self.scan2d_dwell_var, width=10).grid(
        row=0, column=1, sticky="w", padx=(6, 0), pady=2)

    # ========== LCR 高级选项 ==========
    lg = ttk.LabelFrame(left, text="LCR 高级选项", padding=10)
    lg.grid(row=4, column=0, sticky="ew", pady=(0, 6))
    lg.columnconfigure(1, weight=1)
    lg.columnconfigure(3, weight=1)

    ttk.Label(lg, text="主/副:").grid(row=0, column=0, sticky="w")
    prf = ttk.Frame(lg)
    prf.grid(row=0, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Combobox(prf, textvariable=self.scan2d_primary_var,
                 values=LCR_PARAMS, width=6, state="readonly").pack(side="left", padx=(0, 4))
    ttk.Combobox(prf, textvariable=self.scan2d_secondary_var,
                 values=LCR_SECONDARY_PARAMS, width=6, state="readonly").pack(side="left")

    ttk.Label(lg, text="速度:").grid(row=1, column=0, sticky="w")
    ttk.Combobox(lg, textvariable=self.scan2d_speed_var,
                 values=("SLOW","MED","FAST"), width=6, state="readonly").grid(
                     row=1, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="量程:").grid(row=1, column=2, sticky="w", padx=(10, 0))
    rf = ttk.Frame(lg)
    rf.grid(row=1, column=3, sticky="w", pady=2)
    ttk.Radiobutton(rf, text="自动", variable=self.scan2d_range_var,
                    value="AUTO").pack(side="left")
    ttk.Radiobutton(rf, text="手动", variable=self.scan2d_range_var,
                    value="MANUAL").pack(side="left", padx=(6, 0))

    ttk.Label(lg, text="偏压 (V):").grid(row=2, column=0, sticky="w")
    ttk.Entry(lg, textvariable=self.scan2d_bias_var, width=10).grid(
        row=2, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="平均:").grid(row=2, column=2, sticky="w", padx=(10, 0))
    ttk.Entry(lg, textvariable=self.scan2d_avg_var, width=6).grid(
        row=2, column=3, sticky="w", pady=2)

    ttk.Label(lg, text="延迟 (s):").grid(row=3, column=0, sticky="w")
    ttk.Entry(lg, textvariable=self.scan2d_delay_var, width=10).grid(
        row=3, column=1, sticky="w", padx=(6, 0), pady=2)
    ttk.Label(lg, text="DP通道:").grid(row=3, column=2, sticky="w", padx=(10, 0))
    ttk.Combobox(lg, textvariable=self.scan2d_dp_ch_var,
                 values=("CH1","CH2","CH3"), width=6, state="readonly").grid(
                     row=3, column=3, sticky="w", pady=2)

    # ========== 操作按钮 ==========
    btn_frame = ttk.Frame(left)
    btn_frame.grid(row=5, column=0, sticky="ew", pady=(6, 0))
    btn_frame.columnconfigure(0, weight=1)
    btn_frame.columnconfigure(1, weight=1)
    btn_frame.columnconfigure(2, weight=1)
    btn_frame.columnconfigure(3, weight=1)
    btn_frame.columnconfigure(4, weight=1)
    self.scan2d_start_btn = ttk.Button(btn_frame, text="开始扫描", command=self._start_scan2d)
    self.scan2d_start_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2))
    self.scan2d_stop_btn = ttk.Button(btn_frame, text="停止", command=self._stop_scan2d, state="disabled")
    self.scan2d_stop_btn.grid(row=0, column=1, sticky="ew", padx=(2, 0))
    ttk.Button(btn_frame, text="清空", command=self._clear_scan2d).grid(
        row=0, column=2, sticky="ew", padx=(2, 0))
    ttk.Button(btn_frame, text="导出TXT", command=self._export_scan2d_txt).grid(
        row=0, column=3, sticky="ew", padx=(2, 0))
    ttk.Button(btn_frame, text="图像预览", command=self._preview_scan2d_plot).grid(
        row=0, column=4, sticky="ew", padx=(2, 0))

    # ========== 进度条 ==========
    self.scan2d_progress = ttk.Progressbar(left, mode="indeterminate")
    self.scan2d_progress.grid(row=6, column=0, sticky="ew", pady=(6, 0))

    # ========== 状态信息 ==========
    self.scan2d_info_var = tk.StringVar(value="")
    ttk.Label(left, textvariable=self.scan2d_info_var,
              foreground="blue").grid(row=7, column=0, sticky="w", pady=(4, 0))

    # ========== 右侧：表格 ==========
    right = ttk.Frame(parent, padding=8)
    right.grid(row=0, column=1, sticky="nsew")
    right.columnconfigure(0, weight=1)
    right.rowconfigure(0, weight=1)

    self.scan2d_table = ScanTable(right, columns=["#", "参数1", "参数2", "主参数", "副参数"])
    self.scan2d_table.grid(row=0, column=0, sticky="nsew")
