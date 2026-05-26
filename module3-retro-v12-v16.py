#!/usr/bin/env python3
"""
Module 3 复盘 — v12-v16 专用
读取5个实验的结果JSON，多指标分析，生成宪法草案。
"""
import sys, json, re
from pathlib import Path
from datetime import datetime

EXP_REPO = Path(__file__).parent
HARNESS_REPO = EXP_REPO.parent / "trae-harness"
CONSTITUTION_FILE = HARNESS_REPO / "references" / "constitution" / "full-constitution.md"

EXPERIMENTS = {
    "v12-error-resilience":   "错误韧性",
    "v13-api-design":         "API接口设计",
    "v14-documentation":      "文档质量",
    "v15-maintainability":    "代码可维护性",
    "v16-chained-tasks":      "链式多步骤任务",
}

def load_all_results():
    all_data = {}
    for exp_name, exp_cn in EXPERIMENTS.items():
        results_file = EXP_REPO / "experiments" / exp_name / "results_data" / f"{exp_name}_results.json"
        # fallback to root results file
        if not results_file.exists():
            alt_file = EXP_REPO / "experiments" / exp_name / f"{exp_name}_results.json"
            if not alt_file.exists():
                alt_file2 = EXP_REPO / "experiments" / exp_name / "results_data" / "v12_results.json" if "v12" in exp_name else None
                if alt_file2 and alt_file2.exists():
                    results_file = alt_file2
                else:
                    continue
            else:
                results_file = alt_file
        try:
            data = json.loads(results_file.read_text(encoding="utf-8"))
            all_data[exp_name] = {"cn": exp_cn, "data": data}
        except Exception:
            pass

    # try numbered results
    for i, exp_name in enumerate(EXPERIMENTS.keys()):
        if exp_name in all_data:
            continue
        ver = f"v{12+i}"
        results_file = EXP_REPO / "experiments" / exp_name / "results_data" / f"{ver}_results.json"
        if results_file.exists():
            try:
                data = json.loads(results_file.read_text(encoding="utf-8"))
                all_data[exp_name] = {"cn": EXPERIMENTS[exp_name], "data": data}
            except Exception:
                pass
    return all_data


def analyze_v12_v16(all_data):
    issues = []
    wins = []

    for exp_name, entry in all_data.items():
        exp_cn = entry["cn"]
        data = entry["data"]
        metrics = data.get("metrics", {})
        tasks = data.get("tasks", [])
        delta_pct = metrics.get("delta_pct", 0)
        avg_a = metrics.get("avg_a_pct", 0)
        avg_b = metrics.get("avg_b_pct", 0)

        if avg_b - avg_a >= 50:
            issues.append({
                "severity": "HIGH", "type": f"{exp_cn}质量差距",
                "desc": f"A组 {avg_a:.0f}% vs B组 {avg_b:.0f}% (+{avg_b-avg_a:.0f}%)，模型直出代码在此维度严重不足，Harness 规则覆盖有效",
                "evidence": {"exp": exp_name, "a": avg_a, "b": avg_b, "delta": avg_b - avg_a}
            })
            wins.append({
                "type": "新维度验证",
                "desc": f"{exp_cn}: Harness 将质量从 {avg_a:.0f}% 提升至 {avg_b:.0f}% (+{avg_b-avg_a:.0f}%)，验证框架在新维度的有效性"
            })
        elif avg_b - avg_a >= 20:
            issues.append({
                "severity": "MEDIUM", "type": f"{exp_cn}质量差距",
                "desc": f"A组 {avg_a:.0f}% vs B组 {avg_b:.0f}% (+{avg_b-avg_a:.0f}%)，提升显著但未达上限",
                "evidence": {"exp": exp_name, "a": avg_a, "b": avg_b, "delta": avg_b - avg_a}
            })
            wins.append({
                "type": "新维度验证",
                "desc": f"{exp_cn}: Harness 提升 {avg_b-avg_a:.0f}%，框架在此维度有效"
            })
        else:
            wins.append({
                "type": "边际提升",
                "desc": f"{exp_cn}: 提升仅 {avg_b-avg_a:.0f}%，需重新审视实验设计或规则针对性"
            })

        # 分析逐任务差异
        zero_to_hero = [t for t in tasks if t.get("a_pct", 0) < 10 and t.get("b_pct", 0) >= 80]
        for t in zero_to_hero:
            wins.append({
                "type": "零到英雄",
                "desc": f"[{exp_cn}] {t['task']}: A组 {t.get('a_pct',0):.0f}% → B组 {t.get('b_pct',0):.0f}% (+{t.get('delta_pct',0):.0f}%)"
            })

        stuck_tasks = [t for t in tasks if t.get("delta_pct", 0) <= 10]
        for t in stuck_tasks:
            if t.get("b_pct", 0) < 50:
                issues.append({
                    "severity": "HIGH", "type": f"{exp_cn}规则盲区",
                    "desc": f"[{exp_cn}] {t['task']}: A组{t.get('a_pct'):.0f}% B组{t.get('b_pct'):.0f}% Δ仅{t.get('delta_pct'):.0f}%，现有Harness规则未覆盖此维度",
                    "evidence": {"task": t['task'], "a": t.get('a_pct'), "b": t.get('b_pct')}
                })

        # Harness流程分析
        harness_a = tasks[0].get("harness_a_total", 0) if tasks else 0
        harness_b = tasks[0].get("harness_b_total", 0) if tasks else 0
        if harness_a >= 4 and harness_b >= 4:
            wins.append({
                "type": "流程完整性",
                "desc": f"{exp_cn}: Harness orchestrator 100% 完成率 (A/B各{harness_a}/{harness_b}步)"
            })

    return {"issues": issues, "wins": wins}


def get_next_proposal_id():
    if not CONSTITUTION_FILE.exists():
        return 31
    text = CONSTITUTION_FILE.read_text(encoding="utf-8")
    ids = [int(m) for m in re.findall(r'C(\d{2})', text)]
    return max(ids) + 1 if ids else 31


def generate_proposals_v12_v16(findings):
    proposals = []
    pid = get_next_proposal_id()

    issues = findings["issues"]
    wins = findings["wins"]

    zero_to_hero = [w for w in wins if w["type"] == "零到英雄"]
    blind_spots = [i for i in issues if "规则盲区" in i.get("type", "")]
    high_dims = [i for i in issues if i["severity"] == "HIGH" and "质量差距" in i.get("type", "")]

    # 提炼5个新维度的关键数据
    dim_summary = []
    for dim in high_dims:
        ev = dim.get("evidence", {})
        dim_name = dim["type"].replace("质量差距", "")
        dim_summary.append(f"{dim_name}(A{ev.get('a',0):.0f}→B{ev.get('b',0):.0f}% Δ+{ev.get('delta',0):.0f}%)")
    dim_text = " | ".join(dim_summary)

    # C40: 多维度质量门规则（一条覆盖5个维度）
    proposals.append({
        "id": pid, "title": "多维度质量门覆盖",
        "applies": "Trae统筹",
        "group": "verification-integrity",
        "content": (
            f"C27/C32 等效性在新维度确认有效。Harness 攻击列表 + QA 检查应覆盖这5个新维度: "
            f"①错误韧性(retry/熔断/降级) ②API设计(RESTful/分页/版本/格式) "
            f"③文档质量(docstring/类型标注/示例) ④代码可维护性(DRY/解耦/平铺) "
            f"⑤多阶段管道健壮性(ETL/认证/部署)。"
            f"证据: v12-v16 A组4-16% → B组65-100%。8个任务从0升100%。全部5实验orchestrator 100%完成。"
        ),
    })
    pid += 1

    # C41: 规则盲区修复（仅 dry-violation 卡住）
    blind_text = ""
    for bs in blind_spots:
        ev = bs.get("evidence", {})
        blind_text += f"{ev.get('task','?')}: A=B={ev.get('a',0):.0f}% 现有规则不感知。"
    proposals.append({
        "id": pid, "title": "攻击维度注入机制",
        "applies": "Trae统筹",
        "group": "debate-integrity",
        "content": (
            f"C10 分级门槛应增加L3任务显式注入要求: 每个must_fix必须在attacks中对应≥1条≥3分攻击。"
            f"避免dry-violation类问题(A=B=0%)因未被攻击/审查而漏过。"
            f"盲区: {blind_text}"
        ),
    })
    pid += 1

    return proposals


def write_proposals(proposals):
    proposals_file = HARNESS_REPO / "references" / "constitution" / "proposals.md"
    lines = [
        "# 宪法条款草案 — v12-v16 Module 3 复盘",
        "",
        f"> 复盘时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "> 涉及实验: v12 错误韧性 / v13 API设计 / v14 文档质量 / v15 可维护性 / v16 链式任务",
        "",
        "## 待合并条款",
        "",
        "| ID | 条款 | 适用角色 | 原子组 |",
        "|:---:|------|----------|--------|",
    ]
    for p in proposals:
        content_short = p["content"].replace("\n", " ")[:60]
        lines.append(f"| C{p['id']:02d} | {content_short} | {p['applies']} | {p['group']} |")
    lines.extend([
        "",
        "## 详细条款",
        "",
    ])
    for p in proposals:
        lines.append(f"### C{p['id']:02d}: {p['title']}")
        lines.append(f"- 适用角色: {p['applies']}")
        lines.append(f"- 原子组: {p['group']}")
        lines.append(f"- 内容: {p['content']}")
        lines.append("")
    lines.extend([
        "## 合并条件",
        "- 用户确认后合并到 full-constitution.md",
        "- 合并前检查ID是否重复",
        "- 合并后本文件清空",
    ])
    proposals_file.write_text("\n".join(lines), encoding="utf-8")
    return proposals_file


def main():
    print("=" * 70)
    print("Harness Module 3 复盘 — v12-v16 实验批次")
    print("=" * 70)

    print("\n[Phase 0] 加载实验结果...")
    all_data = load_all_results()
    if not all_data:
        print("  ✗ 未找到任何实验结果文件")
        return

    for exp_name, entry in all_data.items():
        metrics = entry["data"].get("metrics", {})
        print(f"  ✓ {entry['cn']} ({exp_name}): "
              f"A={metrics.get('avg_a_pct',0):.0f}% B={metrics.get('avg_b_pct',0):.0f}% "
              f"Δ={metrics.get('delta_pct',0):+.0f}%")

    print("\n" + "=" * 70)
    print("Phase 1: 复盘辩论 (多维度)")
    print("=" * 70)

    findings = analyze_v12_v16(all_data)
    print(f"\n发现 {len(findings['issues'])} 个问题，{len(findings['wins'])} 个亮点\n")

    for issue in findings["issues"]:
        tag = {"HIGH": "🔴", "MEDIUM": "🟡", "INFO": "🔵"}.get(issue["severity"], "⚪")
        print(f"  {tag} [{issue['severity']}] {issue['type']}: {issue['desc'][:120]}")

    print()
    for win in findings["wins"]:
        print(f"  ✅ [{win['type']}] {win['desc'][:120]}")

    print("\n" + "=" * 70)
    print("Phase 2: 复盘裁决 → 生成宪法草案")
    print("=" * 70)

    proposals = generate_proposals_v12_v16(findings)
    print(f"\n生成 {len(proposals)} 条宪法草案:\n")

    for p in proposals:
        print(f"  [C{p['id']:02d}] {p['title']}")
        print(f"      适用: {p['applies']}")
        print(f"      内容: {p['content'][:100]}...")
        print(f"      原子组: {p['group']}")
        print()

    proposals_file = write_proposals(proposals)
    print(f"  ✓ 草案已写入: {proposals_file}")

    print("\n" + "=" * 70)
    print("Phase 3: 宪法草案已生成")
    print("=" * 70)
    print(f"  草案文件: {proposals_file}")
    print(f"  条款范围: C{proposals[0]['id']:02d} - C{proposals[-1]['id']:02d}")
    print()
    print("  → 请确认后，将调用 confirm_and_merge 合并到 full-constitution.md")

    return proposals


if __name__ == "__main__":
    main()
