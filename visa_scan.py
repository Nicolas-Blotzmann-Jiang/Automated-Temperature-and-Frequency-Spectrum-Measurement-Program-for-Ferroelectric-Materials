"""扫描并识别本机可见的 VISA 资源。

用法：
    python visa_scan.py
    python visa_scan.py --backend @py --timeout-ms 3000
    python visa_scan.py --no-idn

默认会先列出 `pyvisa` 能看到的资源地址，再逐个尝试读取 `*IDN?`。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class ScanResult:
    resource: str
    idn: str | None = None
    error: str | None = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="扫描 VISA 地址并尝试读取仪器 ID。",
    )
    parser.add_argument(
        "--backend",
        default=None,
        help="pyvisa 后端，例如 @py；不填则使用默认后端。",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=3000,
        help="读取 IDN 的超时时间，单位毫秒。默认 3000。",
    )
    parser.add_argument(
        "--no-idn",
        action="store_true",
        help="只列出资源地址，不发送 *IDN? 查询。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="以 JSON 格式输出结果。",
    )
    return parser


def scan_resources(backend: str | None = None, timeout_ms: int = 3000, query_idn: bool = True) -> tuple[list[str], list[ScanResult], list[str]]:
    errors: list[str] = []
    resources: list[str] = []
    results: list[ScanResult] = []

    try:
        import pyvisa  # type: ignore
    except Exception as exc:  # pragma: no cover - runtime dependency check
        return resources, results, [f"pyvisa import failed: {exc!r}"]

    rm = None
    if backend:
        try:
            rm = pyvisa.ResourceManager(backend)
        except Exception as exc:
            errors.append(f"ResourceManager({backend!r}) failed: {exc!r}")
    else:
        try:
            rm = pyvisa.ResourceManager()
        except Exception as exc:
            errors.append(f"ResourceManager() failed: {exc!r}")

    if rm is None:
        return resources, results, errors

    try:
        resources = list(rm.list_resources())
    except Exception as exc:
        errors.append(f"list_resources failed: {exc!r}")
        return resources, results, errors

    for resource in resources:
        row = ScanResult(resource=resource)
        if query_idn:
            try:
                inst = rm.open_resource(resource)
                try:
                    inst.timeout = timeout_ms
                    try:
                        inst.read_termination = "\n"
                    except Exception:
                        pass
                    try:
                        inst.write_termination = "\n"
                    except Exception:
                        pass
                    row.idn = str(inst.query("*IDN?")).strip()
                finally:
                    try:
                        inst.close()
                    except Exception:
                        pass
            except Exception as exc:
                row.error = repr(exc)
        results.append(row)

    return resources, results, errors


def classify_instruments(results: list[ScanResult]) -> dict[str, list[str]]:
    """按仪器类型对扫描结果做粗分类。"""

    classified: dict[str, list[str]] = {
        "DP800": [],
        "LCR": [],
    }

    for row in results:
        idn = (row.idn or "").upper()
        if not idn:
            continue
        if ("RIGOL" in idn or "RIGAOL" in idn) and ("DP8" in idn or "DP800" in idn):
            classified["DP800"].append(row.resource)
        if "ZM237" in idn or ("NF" in idn and "LCR" in idn):
            classified["LCR"].append(row.resource)

    return classified


def discover_instruments(backend: str | None = None, timeout_ms: int = 3000) -> dict[str, Any]:
    """扫描 VISA 资源并给出常见仪器的候选地址。"""

    resources, results, errors = scan_resources(
        backend=backend,
        timeout_ms=timeout_ms,
        query_idn=True,
    )
    classified = classify_instruments(results)
    return {
        "visa_resources": resources,
        "visa_idn": [row.__dict__ for row in results],
        "classified": classified,
        "errors": errors,
    }


def _print_text(resources: list[str], results: list[ScanResult], errors: list[str]) -> None:
    print("VISA 资源:")
    if resources:
        for resource in resources:
            print(f"  - {resource}")
    else:
        print("  (未发现)")

    print()
    print("识别结果:")
    if results:
        for row in results:
            if row.idn:
                print(f"  - {row.resource} -> {row.idn}")
            elif row.error:
                print(f"  - {row.resource} -> 失败: {row.error}")
            else:
                print(f"  - {row.resource} -> 未查询")
    else:
        print("  (无)")

    if errors:
        print()
        print("错误:")
        for error in errors:
            print(f"  - {error}")


def _to_json(resources: list[str], results: list[ScanResult], errors: list[str]) -> dict[str, Any]:
    return {
        "visa_resources": resources,
        "visa_idn": [row.__dict__ for row in results],
        "errors": errors,
    }


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    resources, results, errors = scan_resources(
        backend=args.backend,
        timeout_ms=args.timeout_ms,
        query_idn=not args.no_idn,
    )

    if args.json:
        print(json.dumps(_to_json(resources, results, errors), ensure_ascii=False, indent=2))
    else:
        _print_text(resources, results, errors)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())