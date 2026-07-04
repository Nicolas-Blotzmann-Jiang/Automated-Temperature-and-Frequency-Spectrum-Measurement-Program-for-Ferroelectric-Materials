from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Any


class ScanTable(ttk.Frame):
    """带滚动条的扫描数据表。"""
    def __init__(self, master: tk.Widget, columns: list[str] | None = None, **kwargs: Any) -> None:
        super().__init__(master, **kwargs)
        self._columns: list[str] = columns or []
        self.tree: ttk.Treeview | None = None
        if columns:
            self.set_columns(columns)

    def set_columns(self, columns: list[str], col_width: int = 120) -> None:
        """设置列标题并重建 Treeview。"""
        for w in self.winfo_children():
            w.destroy()
        self._columns = columns

        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=8)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=col_width, minwidth=60, anchor="center")

        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def add_row(self, values: list[str]) -> None:
        """追加一行数据。"""
        if self.tree:
            self.tree.insert("", "end", values=values)

    def clear(self) -> None:
        """清空表格。"""
        if self.tree:
            for item in self.tree.get_children():
                self.tree.delete(item)