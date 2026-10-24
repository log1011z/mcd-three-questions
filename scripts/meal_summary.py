"""Summarize agent-normalized MCP selections; standard library, no network calls."""

import argparse
import json
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


GRADE_PATH = Path(__file__).resolve().parents[1] / "references" / "burger-grades.json"
UNITS = {"kcal": Decimal(1), "大卡": Decimal(1), "千卡": Decimal(1),
         "kj": Decimal("4.184"), "千焦": Decimal("4.184")}


def number(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} 必须为非负数字")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(f"{field} 必须为非负数字") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"{field} 必须为非负数字")
    return result


def rounded(value):
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def money(value):
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def load_grades():
    return json.loads(GRADE_PATH.read_text(encoding="utf-8"))["entries"]


def grade_for(name, entries=None):
    for entry in load_grades() if entries is None else entries:
        if name.strip() in [entry["name"], *entry["aliases"]]:
            return entry
    return None


def summarize_selection(selection, budget=None, entries=None):
    if not selection["items"]:
        raise ValueError("选择中至少需要一个单品")
    rows, missing = [], []
    total = Decimal(0)
    for item in selection["items"]:
        quantity = item["quantity"]
        if type(quantity) is not int or quantity <= 0:
            raise ValueError("quantity 必须为正整数")
        if type(item["is_burger"]) is not bool:
            raise ValueError("is_burger 必须为布尔值")
        nutrition = item["nutrition"]
        energy = None
        if nutrition is not None:
            # A size mismatch is missing data, not zero energy or a guessed ratio.
            if nutrition["serving"] == item["spec"]:
                unit = nutrition["unit"].strip().lower()
                if unit not in UNITS:
                    raise ValueError(f"不支持的能量单位：{nutrition['unit']}")
                energy = number(nutrition["energy"], "energy") / UNITS[unit]
        if energy is None:
            missing.append(f"{item['name']}（{item['spec']}）×{quantity}")
        else:
            total += energy * quantity
        rows.append({
            "name": item["name"], "spec": item["spec"], "quantity": quantity,
            "per_kcal": None if energy is None else rounded(energy),
            "total_kcal": None if energy is None else rounded(energy * quantity),
            "is_burger": item["is_burger"],
            "grade": grade_for(item["name"], entries) if item["is_burger"] else None,
        })
    quote = selection.get("quote")
    price = None
    if quote is not None:
        if quote["source"] != "calculate-price" or not quote["queried_at"]:
            raise ValueError("quote 需要 calculate-price 来源和调用时间")
        price = number(quote["total_cny"], "total_cny")
    limit = None if budget is None else number(budget, "budget_cny")
    return {
        "label": selection["label"], "items": rows,
        "known_kcal": rounded(total), "missing": missing, "price": price,
        "quote_time": None if quote is None else quote["queried_at"],
        "over_budget": None if price is None or limit is None else max(price - limit, Decimal(0)),
        "reason": selection.get("reason", ""), "title": selection.get("title", ""),
    }


def render_report(data):
    if data["mode"] not in {"demo", "live"}:
        raise ValueError("mode 必须为 demo 或 live")
    if not data["selections"]:
        raise ValueError("至少需要一份选择")
    lines = ["# 麦麦三问局", ""]
    if data["mode"] == "demo":
        lines += ["**演示数据：门店、餐品规格、价格与热量均为测试输入，不代表实时供应。**", ""]
    lines += [f"门店：{cell(data['store'])}", "", "汉堡等级：项目自定义用料档次。", ""]
    budget = data.get("budget_cny")
    if budget is not None:
        lines += [f"预算上限：¥{money(number(budget, 'budget_cny'))}", ""]
    entries = load_grades()
    for selection in data["selections"]:
        summary = summarize_selection(selection, budget, entries)
        lines += [f"## {cell(summary['label'])}", "",
                  "| 当前选择 | 规格 | 数量 | 单份热量 | 该项合计 | 汉堡用料等级 |",
                  "|---|---|---:|---:|---:|---|"]
        for row in summary["items"]:
            grade = row["grade"]
            label = "—" if not row["is_burger"] else "待评"
            if grade:
                label = f"Lv.{grade['level']} {grade['label']}"
            per = "热量暂无数据" if row["per_kcal"] is None else f"{row['per_kcal']} kcal"
            subtotal = "未计入" if row["total_kcal"] is None else f"{row['total_kcal']} kcal"
            lines.append(f"| {cell(row['name'])} | {cell(row['spec'])} | {row['quantity']} | {per} | {subtotal} | {label} |")
        lines.append("")
        if summary["missing"]:
            lines += [f"**已知热量合计：{summary['known_kcal']} kcal（整餐数据未齐）**",
                      "", "未计入：" + "、".join(cell(name) for name in summary["missing"]), ""]
        else:
            lines += [f"**整餐总热量：{summary['known_kcal']} kcal**", ""]
        if summary["price"] is None:
            lines += ["当前应付：**待核价**", ""]
        else:
            prefix = "演示核价" if data["mode"] == "demo" else "当前核价"
            lines += [f"{prefix}：**¥{money(summary['price'])}**（calculate-price，{cell(summary['quote_time'])}）", ""]
            if summary["over_budget"]:
                lines += [f"**超预算 ¥{money(summary['over_budget'])}，不作为满足预算的推荐。**", ""]
        seen = set()
        for row in summary["items"]:
            grade = row["grade"]
            if grade and row["name"] not in seen:
                seen.add(row["name"])
                lines += [f"- {cell(row['name'])}：{grade['reason']} "
                          f"[官方依据]({grade['source_url']})（查阅：{grade['checked_on']}）"]
        if seen:
            lines.append("")
        if summary["reason"]:
            lines += ["选择理由：" + cell(summary["reason"]), ""]
        if summary["title"]:
            lines += ["本局称号：" + cell(summary["title"]), ""]
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description="汇总三问局的热量、真实核价输入和汉堡等级；不联网")
    parser.add_argument("input", type=Path, help="按 references/data-contract.md 整理的 JSON")
    parser.add_argument("--output", type=Path, help="可选 Markdown 输出路径，默认输出到终端")
    args = parser.parse_args()
    try:
        report = render_report(json.loads(args.input.read_text(encoding="utf-8-sig")))
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    if args.output:
        args.output.write_text(report, encoding="utf-8")
    else:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        print(report, end="")


if __name__ == "__main__":
    main()
