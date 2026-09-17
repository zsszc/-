"""跨境物流项目交付前验收；默认离线运行，--live 才访问本地服务。"""
import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
KB_FILES = ("shipment-faq.md", "customs-clearance.md", "exception-handling.md",
            "shipping-fees.md", "prohibited-items.md", "claims-policy.md")


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="检查本机 8000 端口接口")
    args = parser.parse_args()
    tracked = subprocess.check_output(["git", "ls-files", ".env"], cwd=ROOT, text=True).strip()
    if tracked:
        fail(".env 不得被 Git 跟踪")
    missing = [name for name in KB_FILES if not (ROOT / "data/kb" / name).exists()]
    if missing:
        fail(f"缺少知识库材料: {missing}")
    cases = [json.loads(line) for line in (ROOT / "data/evals/logistics_regression.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(cases) < 12:
        fail("回归样例少于 12 条")
    from app.core.taxonomy import TOPIC_NAMES
    from app.tools.registry import builtin_specs
    required = {"query_shipment", "estimate_shipping_fee", "classify_logistics_exception", "check_prohibited_item"}
    actual = {spec.name for spec in builtin_specs()}
    if not required <= actual:
        fail(f"物流工具未全部注册: {sorted(required - actual)}")
    if len(TOPIC_NAMES) != 17:
        fail(f"物流主题数量应为 17，实际为 {len(TOPIC_NAMES)}")
    if args.live:
        payloads = [
            ("/api/logistics/shipping-fee", {"origin":"深圳", "destination":"德国", "weight_kg":2, "transport_mode":"标准"}),
            ("/api/logistics/shipment-query", {"tracking_no":"CNDE20260917001", "user_id":"release-check"}),
            ("/api/logistics/prohibited-item-check", {"item_name":"锂电池"}),
        ]
        for path, payload in payloads:
            req = Request("http://127.0.0.1:8000" + path, data=json.dumps(payload).encode(), headers={"content-type":"application/json"})
            try:
                with urlopen(req, timeout=20) as response:
                    if response.status != 200:
                        fail(f"接口 {path} 返回 {response.status}")
            except Exception as exc:
                fail(f"接口 {path} 失败: {exc}")
    print(f"PASS: 物流项目验收通过（知识材料 {len(KB_FILES)} 份，回归样例 {len(cases)} 条，主题 {len(TOPIC_NAMES)} 类）")


if __name__ == "__main__":
    main()
