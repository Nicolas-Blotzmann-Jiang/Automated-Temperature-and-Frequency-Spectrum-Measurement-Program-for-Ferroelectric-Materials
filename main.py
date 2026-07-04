"""仪器控制面板主入口。

使用方法：
    python main.py

需要安装：pip install matplotlib
如需连接实物仪器：pip install pyvisa pyvisa-py
如需串口温控仪：pip install pyserial
如需 Modbus：pip install pymodbus
"""

from __future__ import annotations

from gui_ui import App
from gui_build import build_ui, build_connect_page
from gui_pages import build_single_page, build_scan_page, build_scan2d_page
from gui_ops import (
    _connect_dp, _disconnect_dp, _dp_output, _dp_measure,
    _connect_lcr, _disconnect_lcr, _lcr_measure,
    _init_tc, _set_tc_target, _tc_read, _tc_wait_stable,
    _auto_connect_all,
)
from gui_scan import (
    _update_scan_params, _update_scan_hints, _update_scan_points,
    _stop_scan, _clear_plot,
    _gen_scan_values, _start_scan, _export_csv, _export_txt,
)
from gui_scan2d import (
    _update_scan2d_hints, _update_scan2d_points,
    _gen_scan2d_values, _start_scan2d, _stop_scan2d,
    _clear_scan2d, _export_scan2d_txt, _preview_scan2d_plot,
    PLOT_TYPE_INFO,
)

# 将各模块的方法混入 App 类
App._build_ui       = build_ui
App._build_connect_page = build_connect_page
App._build_single_page  = build_single_page
App._build_scan_page    = build_scan_page
App._build_scan2d_page  = build_scan2d_page

App._connect_dp      = _connect_dp
App._disconnect_dp   = _disconnect_dp
App._dp_output       = _dp_output
App._dp_measure      = _dp_measure
App._connect_lcr     = _connect_lcr
App._disconnect_lcr  = _disconnect_lcr
App._lcr_measure     = _lcr_measure
App._auto_connect_all = _auto_connect_all
App._init_tc         = _init_tc
App._set_tc_target   = _set_tc_target
App._tc_read         = _tc_read
App._tc_wait_stable  = _tc_wait_stable

App._update_scan_params = _update_scan_params
App._update_scan_hints  = _update_scan_hints
App._update_scan_points = _update_scan_points
App._stop_scan          = _stop_scan
App._clear_plot         = _clear_plot
App._gen_scan_values    = _gen_scan_values
App._start_scan         = _start_scan
App._export_csv         = _export_csv
App._export_txt         = _export_txt

# 双参数扫描方法混入
App._update_scan2d_hints  = _update_scan2d_hints
App._update_scan2d_points = _update_scan2d_points
App._gen_scan2d_values    = _gen_scan2d_values
App._start_scan2d         = _start_scan2d
App._stop_scan2d          = _stop_scan2d
App._clear_scan2d         = _clear_scan2d
App._export_scan2d_txt    = _export_scan2d_txt
App._preview_scan2d_plot  = _preview_scan2d_plot


# 双参数扫描辅助方法
def _update_scan2d_params(self) -> None:
    """切换仪器时更新参数选项。"""
    inst = self.scan2d_instrument_var.get()
    if inst == "LCR":
        self.scan2d_p1_param_combo.config(values=["频率", "电平", "偏压"])
        self.scan2d_p2_param_combo.config(values=["频率", "电平", "偏压"])
    else:
        self.scan2d_p1_param_combo.config(values=["电压", "电流"])
        self.scan2d_p2_param_combo.config(values=["电压", "电流"])
    self._update_scan2d_hints()


def _update_scan2d_plot_hint(self) -> None:
    """更新图像预览类型提示。"""
    pt = self.scan2d_plot_type_var.get()
    self.scan2d_plot_type_hint.set(PLOT_TYPE_INFO.get(pt, ""))


App._update_scan2d_params    = _update_scan2d_params
App._update_scan2d_plot_hint = _update_scan2d_plot_hint


if __name__ == "__main__":
    app = App()
    app.mainloop()