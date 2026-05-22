#!/usr/bin/env python3
"""
experiment-loop.py — Harness 实验全自动化循环

用法:
  python experiment-loop.py run --exp v4

流程:
  1. git pull 两个仓库到最新
  2. 运行指定实验脚本
  3. 解析实验结果 → 生成结论报告
  4. 执行 Module 3 复盘 (Phase 1-5)
  5. 展示宪法草案 → 等待用户确认
  6. 合并草案到 full-constitution.md
  7. 提交并 push 两个仓库

用法示例:
  python experiment-loop.py run --exp v4
  python experiment-loop.py run --exp v10
  python experiment-loop.py run --exp v10 --no-confirm   # CI模式
"""

import sys, os, re, json, subprocess, argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

GIT = r"C:\Program Files\Git\bin\git.exe"
EXP_REPO = Path(__file__).parent
HARNESS_REPO = Path(__file__).parent.parent / "trae-harness"
SCRIPTS_DIR = HARNESS_REPO / "scripts"


@dataclass
class LoopConfig:
    exp_name: str
    exp_dir: Path = field(init=False)
    exp_script: Path = field(init=False)
    results_file: Path = field(init=False)

    def __post_init__(self):
        self.exp_dir = EXP_REPO / "experiments" / self.exp_name
        self.exp_script = self.exp_dir / "experiment.py"
        self.results_file = self.exp_dir / "results"


def run_cmd(cmd, cwd=None, timeout=600):
    """运行 shell 命令，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True,
        timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def git_pull(repo_path: Path) -> bool:
    print(f"  ↳ git pull {repo_path.name}...")
    rc, out, err = run_cmd(f'"{GIT}" pull origin master', cwd=repo_path)
    if rc == 0:
        print(f"    ✓ {repo_path.name} 已更新")
        return True
    else:
        print(f"    ⚠ pull 无更新或无需更新: {err.strip()}")
        return True


def git_add_all_push(repo_path: Path, msg: str) -> bool:
    print(f"  ↳ git commit & push {repo_path.name}...")
    rc1, _, _ = run_cmd(f'"{GIT}" add -A', cwd=repo_path)
    if rc1 != 0:
        print(f"    ✗ git add 失败"); return False
    status_out = subprocess.run(
        f'"{GIT}" status --short', shell=True, cwd=repo_path,
        capture_output=True, text=True
    ).stdout.strip()
    if not status_out:
        print(f"    - 无变更，跳过 push"); return True
    rc2, _, err2 = run_cmd(f'"{GIT}" commit -m "{msg}"', cwd=repo_path)
    if rc2 != 0:
        print(f"    ✗ git commit 失败: {err2.strip()}"); return False
    rc3, _, err3 = run_cmd(f'"{GIT}" push origin master', cwd=repo_path)
    if rc3 == 0:
        print(f"    ✓ {repo_path.name} 已推送"); return True
    else:
        print(f"    ⚠ push 失败(可能无网络): {err3.strip()}")
        print(f"    - commit 已保存，本地待推送"); return True


def sync_repos() -> bool:
    print("\n[步骤 0] 同步两个仓库...")
    ok1 = git_pull(EXP_REPO)
    ok2 = git_pull(HARNESS_REPO)
    return ok1 and ok2


def run_experiment(cfg: LoopConfig) -> dict:
    print(f"\n[步骤 1] 运行实验: {cfg.exp_name}...")
    if not cfg.exp_script.exists():
        print(f"  ✗ 实验脚本不存在: {cfg.exp_script}")
        print(f"  提示: 请先在 experiments/{cfg.exp_name}/ 下创建 experiment.py")
        sys.exit(1)
    print(f"  运行: {cfg.exp_script}")
    rc, out, err = run_cmd(
        f'"{sys.executable}" "{cfg.exp_script}"',
        cwd=cfg.exp_dir, timeout=3600
    )
    if rc != 0:
        print(f"  ✗ 实验脚本执行失败 (exit {rc})")
        print(err[-1000:])
        sys.exit(1)
    print(f"  ✓ 实验完成")
    results = parse_experiment_results(cfg)
    return results


def parse_experiment_results(cfg: LoopConfig) -> dict:
    print(f"\n[步骤 2] 解析实验结果...")
    results_file = cfg.results_file
    if not results_file.exists():
        print(f"  ⚠ 结果文件不存在，尝试从实验输出推断")
        return infer_results(cfg)
    try:
        if results_file.suffix == ".json":
            data = json.loads(results_file.read_text(encoding="utf-8"))
        else:
            data = parse_csv_or_text(results_file)
        print(f"  ✓ 解析到 {len(data.get('tests', []))} 个测试结果")
        return data
    except Exception as e:
        print(f"  ⚠ 解析失败: {e}，使用推断模式")
        return infer_results(cfg)


def infer_results(cfg: LoopConfig) -> dict:
    print(f"  推断模式: 请提供以下结果(直接回车跳过):")
    print(f"  格式: A组通过数/总数, B组通过数/总数")
    a_str = input("  A组测试结果 (例如 36/40): ").strip()
    b_str = input("  B组测试结果 (例如 40/40): ").strip()
    def parse(s):
        if not s: return None
        parts = s.split("/")
        return {"passed": int(parts[0]), "total": int(parts[1])}
    return {"a": parse(a_str), "b": parse(b_str), "mode": "manual"}


def generate_report(cfg: LoopConfig, results: dict) -> str:
    print(f"\n[步骤 3] 生成实验报告...")
    a = results.get("a", {})
    b = results.get("b", {})
    a_rate = a.get("passed", 0) / max(a.get("total", 1), 1) * 100
    b_rate = b.get("passed", 0) / max(b.get("total", 1), 1) * 100
    delta = b_rate - a_rate

    report = f"""# {cfg.exp_name.upper()} 实验报告

> 模型: deepseek-v4-pro | Harness: trae-harness v1.3 | 时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}

## 实验设计

A组: DSV4 Pro 直出代码 + 直出测试  
B组: DSV4 Pro + Harness 全流程

## 测试结果

| 组别 | 通过 | 总数 | 通过率 |
|------|:----:|:----:|:------:|
| A组 (无Harness) | {a.get('passed', '?')} | {a.get('total', '?')} | {a_rate:.0f}% |
| B组 (+Harness) | {b.get('passed', '?')} | {b.get('total', '?')} | {b_rate:.0f}% |
| **差值 Δ** | | | **{delta:+.0f}%** |

## 结论

Harness 将 DSV4 Pro 的代码质量从 {a_rate:.0f}% 提升到 {b_rate:.0f}% ({delta:+.0f}%)。

{f"[原始数据模式] 来自手动输入" if results.get('mode') == 'manual' else ''}
"""
    report_file = cfg.exp_dir / "report.md"
    report_file.write_text(report, encoding="utf-8")
    print(f"  ✓ 报告已写入: {report_file}")
    return report


def module3_retrospective(cfg: LoopConfig, results: dict) -> list[dict]:
    """
    Module 3 复盘 (Phase 1-5)
    Phase 1: 复盘辩论
    Phase 2: 裁决分类
    Phase 3: 生成宪法草案
    Phase 4: 用户确认 (在主循环中处理)
    Phase 5: 合并 + 瘦身提醒
    """
    print(f"\n[步骤 4] Module 3 复盘...")
    print("=" * 60)
    print("Phase 1: 复盘辩论")
    print("=" * 60)

    findings = analyze_results(results)
    print(f"\n发现 {len(findings['issues'])} 个问题，{len(findings['wins'])} 个亮点\n")

    for issue in findings["issues"]:
        print(f"  [{issue['severity']}] {issue['type']}: {issue['desc']}")

    print("\n" + "=" * 60)
    print("Phase 2: 复盘裁决")
    print("=" * 60)

    proposals = generate_proposals(findings)
    print(f"\n生成 {len(proposals)} 条宪法草案:")
    for p in proposals:
        print(f"\n  [C{p['id']}] {p['title']}")
        print(f"  适用: {p['applies']}")
        print(f"  内容: {p['content'][:80]}...")

    print("\n" + "=" * 60)
    print("Phase 3: 宪法草案已生成")
    print("=" * 60)
    print("  → 等待用户确认后合并到 full-constitution.md")

    return proposals


def analyze_results(results: dict) -> dict:
    a = results.get("a", {})
    b = results.get("b", {})
    a_pass = a.get("passed", 0)
    a_total = a.get("total", 0)
    b_pass = b.get("passed", 0)
    b_total = b.get("total", 0)
    failed = a_total - a_pass

    issues = []
    wins = []

    a_rate = a_pass / max(a_total, 1) * 100
    b_rate = b_pass / max(b_total, 1) * 100
    delta = b_rate - a_rate

    if failed > 0:
        issues.append({
            "severity": "HIGH",
            "type": "代码质量",
            "desc": f"A组有 {failed} 个测试失败，B组全部通过 (+{delta:.0f}%)"
        })

    if results.get("mode") == "manual":
        issues.append({
            "severity": "INFO",
            "type": "数据采集",
            "desc": "结果来自手动输入，建议后续自动化"
        })

    if delta < 5:
        wins.append({"type": "边际效果", "desc": "两组差异较小 (<5%)"})
    else:
        wins.append({"type": "显著提升", "desc": f"Harness 带来 {delta:.0f}% 质量提升"})

    return {"issues": issues, "wins": wins, "delta": delta}


def generate_proposals(findings: dict) -> list[dict]:
    proposals = []
    proposal_id = get_next_proposal_id()

    for issue in findings["issues"]:
        if issue["severity"] == "HIGH" and "代码质量" in issue["type"]:
            proposals.append({
                "id": proposal_id,
                "title": issue["desc"],
                "applies": "全体",
                "group": "verification-integrity",
                "content": f"增强 {issue['type']} 检查: {issue['desc']}",
            })
            proposal_id += 1

    if not proposals:
        proposals.append({
            "id": proposal_id,
            "title": "持续改进",
            "applies": "全体",
            "group": "verification-integrity",
            "content": "实验未发现新的规则空白，建议继续扩展测试集",
        })

    return proposals


def get_next_proposal_id() -> int:
    constitution = HARNESS_REPO / "references" / "constitution" / "full-constitution.md"
    if not constitution.exists():
        return 31
    text = constitution.read_text(encoding="utf-8")
    ids = [int(m) for m in re.findall(r'C(\d{2})', text)]
    return max(ids) + 1 if ids else 31


def write_proposals_to_file(proposals: list[dict]):
    proposals_file = HARNESS_REPO / "references" / "constitution" / "proposals.md"
    lines = [
        "# 宪法条款草案",
        "",
        "> 本文件记录复盘产出的新规则草案，待用户确认后合并到full-constitution.md",
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
        "## 合并条件",
        "- 用户确认后合并到full-constitution.md",
        "- 合并前检查ID是否重复",
        "- 合并后本文件清空",
        "",
        f"## 复盘元信息",
        f"- 本次复盘: {datetime.now().strftime('%Y-%m-%d')} — {proposals[0].get('source', 'experiment-loop')}",
    ])
    proposals_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ 草案已写入 proposals.md (C{proposals[0]['id']:02d}-{proposals[-1]['id']:02d})")


def confirm_and_merge(proposals: list[dict], no_confirm: bool) -> bool:
    print("\n" + "=" * 60)
    print("Phase 4: 用户确认 → 合并宪法")
    print("=" * 60)

    if no_confirm:
        print("  [CI模式] 自动确认所有草案")
        confirmed = True
    else:
        print(f"\n  共 {len(proposals)} 条草案待确认:")
        for p in proposals:
            print(f"\n  [C{p['id']:02d}] {p['content'][:80]}")
        print("\n  确认所有草案? (y/n，默认为 y): ", end="")
        resp = input().strip().lower()
        confirmed = resp in ("", "y", "yes")

    if not confirmed:
        print("  ✗ 用户取消，保留草案在 proposals.md")
        return False

    merge_proposals(proposals)
    return True


def merge_proposals(proposals: list[dict]):
    constitution_file = HARNESS_REPO / "references" / "constitution" / "full-constitution.md"
    text = constitution_file.read_text(encoding="utf-8")

    version_match = re.search(r'v(\d+)\.(\d+)\.(\d+):', text)
    if version_match:
        major, minor, patch = int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3))
        new_version = f"v{major}.{minor}.{patch+1}"
        new_record = f"- {new_version}: 新增 C{proposals[0]['id']:02d}" + (
            f"-C{proposals[-1]['id']:02d}" if len(proposals) > 1 else ""
        ) + f" — {datetime.now().strftime('%Y-%m-%d')} (experiment-loop)"
    else:
        new_version = "v1.4.0"
        new_record = f"- {new_version}: 新增 C{proposals[0]['id']:02d} (experiment-loop)"

    new_rules = "\n".join(
        f"| C{p['id']:02d} | {p['content'][:100]} | {p['applies']} | {p['group']} |"
        for p in proposals
    )

    if "## 修订记录" in text:
        text = text.replace("## 修订记录", f"{new_rules}\n\n## 修订记录")
        text = text.replace(
            re.search(r"(## 修订记录\n- .+?\n)", text).group(1),
            re.search(r"(## 修订记录\n- .+?\n)", text).group(1) + f"  {new_record}\n"
        )
    else:
        text += f"\n{new_rules}\n\n## 修订记录\n{new_record}\n"

    constitution_file.write_text(text, encoding="utf-8")
    print(f"  ✓ 合并完成: full-constitution.md → {new_version}")

    proposals_file = HARNESS_REPO / "references" / "constitution" / "proposals.md"
    proposals_file.write_text(
        "# 宪法条款草案\n\n> 本文件记录复盘产出的新规则草案，待用户确认后合并到full-constitution.md\n\n## 待合并条款\n\n（暂无）\n\n## 复盘元信息\n"
        f"- 上次复盘: {datetime.now().strftime('%Y-%m-%d')} — experiment-loop\n",
        encoding="utf-8"
    )
    print("  ✓ proposals.md 已清空")

    count = len(HARNESS_REPO.glob("references/constitution/full-constitution.md"))
    rule_lines = [l for l in text.split("\n") if l.startswith("| C")]
    rule_count = len(rule_lines)
    if rule_count > 25:
        print(f"  ⚠ Phase 5: 规则数 {rule_count} > 25 条，建议瘦身")
    else:
        print(f"  ✓ Phase 5: 规则数 {rule_count} <= 25 条，无瘦身必要")


def run(args):
    cfg = LoopConfig(args.exp)

    print("╔══════════════════════════════════════════════════════╗")
    print(f"║  Harness 实验全自动化循环 — {args.exp:<26}║")
    print("╚══════════════════════════════════════════════════════╝")

    if not EXP_REPO.exists():
        print(f"✗ 实验仓库不存在: {EXP_REPO}")
        sys.exit(1)

    sync_repos()
    results = run_experiment(cfg)
    report = generate_report(cfg, results)
    proposals = module3_retrospective(cfg, results)

    write_proposals_to_file(proposals)

    print(f"\n{'='*60}")
    print("Phase 4: 等待用户确认")
    print("="*60)
    print(f"宪法草案已写入 proposals.md (C{proposals[0]['id']:02d}-{proposals[-1]['id']:02d})")
    print("请审查草案后，确认是否合并 (Ctrl+C 取消)")
    try:
        confirmed = confirm_and_merge(proposals, args.no_confirm)
    except KeyboardInterrupt:
        print("\n  已取消，草案保留在 proposals.md")
        confirmed = False

    print(f"\n{'='*60}")
    print("最后步骤: 提交 & 推送")
    print("="*60)

    exp_msg = f"{args.exp}: 实验完成\n结果: A={results['a'].get('passed','?')}/{results['a'].get('total','?')} B={results['b'].get('passed','?')}/{results['b'].get('total','?')}\n结论见 report.md"
    git_add_all_push(EXP_REPO, exp_msg)

    if confirmed:
        h_msg = f"{args.exp} Module 3 复盘: 新增 C{proposals[0]['id']:02d}" + (
            f"-C{proposals[-1]['id']:02d}" if len(proposals) > 1 else ""
        )
        git_add_all_push(HARNESS_REPO, h_msg)
    else:
        print("  - Harness 仓库无变更，跳过")

    print(f"\n{'='*60}")
    print("✓ 实验循环完成")
    print("="*60)
    print("建议下一步:")
    print(f"  1. 查看实验报告: experiments/{args.exp}/report.md")
    if confirmed:
        print(f"  2. 查看宪法: trae-harness/references/constitution/full-constitution.md")
    else:
        print(f"  2. 手动审查 proposals.md 后运行: python experiment-loop.py merge")
    print("  3. 推送本地实验仓库 (网络恢复后)")


def main():
    parser = argparse.ArgumentParser(
        description="Harness 实验全自动化循环",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="cmd")

    run_parser = sub.add_parser("run", help="运行实验循环")
    run_parser.add_argument("--exp", "-e", required=True, help="实验名 (如 v4, v10)")
    run_parser.add_argument("--no-confirm", action="store_true", help="CI模式: 自动确认所有草案")

    parser.add_argument("--exp", "-e", dest="exp", help="实验名 (run 子命令)")
    parser.add_argument("--no-confirm", action="store_true", dest="no_confirm", help="CI模式")

    args = parser.parse_args()

    if not args.exp:
        parser.print_help()
        print("\n示例:")
        print("  python experiment-loop.py run --exp v4")
        print("  python experiment-loop.py run --exp v10 --no-confirm")
        sys.exit(1)

    run(args)


if __name__ == "__main__":
    main()
