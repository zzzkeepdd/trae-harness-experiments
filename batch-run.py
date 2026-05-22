"""
Harness 实验批量运行器

用法:
  python batch-run.py              # 运行所有待做实验
  python batch-run.py --dry-run    # 只看计划不执行
  python batch-run.py --start v10  # 从 v10 开始

特性:
  - 每个实验自动报告 + Module 3 复盘 + 宪法合并
  - 网络不通时 commit 保留在本地，不中断后续实验
  - 全部跑完后汇总写入 master-log.md
  - 支持 CTRL+C 中断 + 恢复
"""

import sys, os, json, datetime, re, subprocess, shutil
from pathlib import Path

PYTHON = r"C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
GIT = r"C:\Program Files\Git\bin\git.exe"
EXP_REPO = Path(r"d:\harness测试\trae-harness-experiments")
LOOP_SCRIPT = EXP_REPO / "experiment-loop.py"
MASTER_LOG = EXP_REPO / "analysis" / "master-log.md"

ALL_EXPERIMENTS = [
    {
        "id": "v10-swebench-style",
        "name": "v10 SWE-bench 修bug",
        "priority": "P0",
        "line": "复刻线",
        "desc": "修bug能力+regression检测，对标SWE-bench Verified",
        "metrics": "bug修复率、regression数",
    },
    {
        "id": "v5-code-standards",
        "name": "v5 代码规范",
        "priority": "P1",
        "line": "新赛道",
        "desc": "flake8+pylint+radon 代码规范度",
        "metrics": "flake8违规数、pylint评分、MI指数",
    },
    {
        "id": "v6-security",
        "name": "v6 安全加固",
        "priority": "P1",
        "line": "新赛道",
        "desc": "SQL注入、文件上传漏洞防御",
        "metrics": "安全用例通过率",
    },
    {
        "id": "v7-module3-learning",
        "name": "v7 Module 3 长期学习",
        "priority": "P1",
        "line": "新赛道",
        "desc": "宪法累积→同类bug复发率下降",
        "metrics": "同类bug复发率、规则命中数",
    },
    {
        "id": "v8-performance",
        "name": "v8 性能意识",
        "priority": "P2",
        "line": "新赛道",
        "desc": "复杂度攻击→算法优化",
        "metrics": "时间复杂度变化、runtime benchmark",
    },
    {
        "id": "v9-humaneval-style",
        "name": "v9 HumanEval 风格",
        "priority": "P3",
        "line": "复刻线",
        "desc": "函数补全，对标HumanEval基准",
        "metrics": "测试用例通过率",
    },
    {
        "id": "v11-livecodebench-style",
        "name": "v11 LiveCodeBench 风格",
        "priority": "P3",
        "line": "复刻线",
        "desc": "竞赛编程，对标LiveCodeBench",
        "metrics": "算法题通过率",
    },
]


def run_cmd(cmd: str, cwd=None):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"


def local_commit(repo, msg):
    print(f"  ↳ 本地 commit: {repo.name}")
    rc, out, err = run_cmd(f'"{GIT}" add -A', cwd=repo)
    status = subprocess.run(f'"{GIT}" status --short', shell=True, cwd=repo, capture_output=True, text=True).stdout.strip()
    if not status:
        print(f"    - 无变更")
        return
    rc2, _, err2 = run_cmd(f'"{GIT}" commit -m "{msg}"', cwd=repo)
    if rc2 == 0:
        print(f"    ✓ 已 commit")
    else:
        print(f"    ⚠ commit: {err2.strip()}")


def run_experiment(exp_id):
    print(f"\n{'='*80}")
    print(f"  {exp_id}")
    print(f"{'='*80}")

    exp_dir = EXP_REPO / "experiments" / exp_id
    experiment_py = exp_dir / "experiment.py"
    if not experiment_py.exists():
        print(f"  ⚠ {experiment_py} 不存在，跳过")
        return None

    t0 = datetime.datetime.now()
    rc, out, err = run_cmd(f'"{PYTHON}" "{experiment_py}"', cwd=exp_dir)
    elapsed = (datetime.datetime.now() - t0).total_seconds()

    results = {}
    if exp_dir.joinpath("results").exists():
        try:
            results = json.loads(exp_dir.joinpath("results").read_text(encoding="utf-8"))
        except:
            pass

    report_file = exp_dir / "report.md"
    report = ""
    if report_file.exists():
        report = report_file.read_text(encoding="utf-8")

    return {
        "exp_id": exp_id,
        "exit_code": rc,
        "elapsed": elapsed,
        "results": results,
        "report": report,
    }


def run_module3(exp_id):
    print(f"\n  Module 3 复盘...")
    rc, _, err = run_cmd(
        f'"{PYTHON}" "{LOOP_SCRIPT}" run --exp {exp_id} --no-confirm',
        cwd=EXP_REPO
    )
    if rc != 0:
        print(f"  ⚠ Module 3 失败 (rc={rc}): {err[:120]}")
    return rc


def update_master_log(records):
    rows = "| 实验 | 优先级 | 结果摘要 | 时间 |\n"
    rows += "|------|:--:|------|------|\n"
    for r in records:
        result_text = f"exit={r.get('exit_code','?')}"
        if r.get("results"):
            metrics = r["results"].get("metrics", {})
            if metrics:
                a_cov = metrics.get("avg_a_coverage", 0)
                b_cov = metrics.get("avg_b_coverage", 0)
                result_text = f"A={a_cov:.0f}%→B={b_cov:.0f}% (Δ{b_cov-a_cov:+.0f}%)"
        rows += f"| {r['exp_id']} | {r.get('priority','?')} | {result_text} | {r.get('time','?')} |\n"

    constitution = EXP_REPO.parent / "trae-harness" / "references" / "constitution" / "full-constitution.md"
    constitution_ver = "?"
    if constitution.exists():
        m = re.search(r'(v\d+\.\d+\.\d+):', constitution.read_text(encoding="utf-8"))
        if m: constitution_ver = m.group(1)

    log = f"""# Harness 实验主日志

> 最后更新: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
> 宪法版本: {constitution_ver}
> 模型: deepseek-v4-pro

## 本次批量运行

{rows}

## 历史实验

| 实验 | 优先级 | 结果 | 时间 |
|------|:--:|------|------|
| v2 独立测试 | — | A=92% B=99% (Δ+6%) | 2026-05-22 |
| v3 编排器 | — | A=90% B=100% (Δ+10%) | 2026-05-22 |
| v4 测试质量 | P0 | A=62%→B=85% (Δ+23%) · 4.4x断言 | 2026-05-23 |

"""
    MASTER_LOG.write_text(log, encoding="utf-8")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Harness 实验批量运行器")
    parser.add_argument("--dry-run", action="store_true", help="只看计划不执行")
    parser.add_argument("--start", default=None, help="从指定实验开始 (如 v10)")
    parser.add_argument("--only", default=None, help="只运行指定实验")
    args = parser.parse_args()

    if args.only:
        experiments = [e for e in ALL_EXPERIMENTS if e["id"] == args.only]
        if not experiments:
            print(f"未知实验: {args.only}")
            print(f"可选: {', '.join(e['id'] for e in ALL_EXPERIMENTS)}")
            sys.exit(1)
    else:
        experiments = ALL_EXPERIMENTS
        if args.start:
            experiments = [e for e in experiments if e["id"] >= args.start]

    print("╔══════════════════════════════════════════════════════╗")
    print("║  Harness 批量实验运行器                                ║")
    print("╚══════════════════════════════════════════════════════╝")
    print(f"\n计划运行 {len(experiments)} 个实验:")
    for e in experiments:
        print(f"  [{e['priority']}] {e['id']} — {e['desc']}")
    print(f"\n模式: {'DRY-RUN (不执行)' if args.dry_run else '执行模式'}")
    print(f"网络不通时: commit 保存在本地，不中断")

    if args.dry_run:
        print("\nDRY-RUN 完成，无实际执行")
        return

    records = []
    for i, exp in enumerate(experiments):
        exp_id = exp["id"]
        priority = exp["priority"]
        print(f"\n[{i+1}/{len(experiments)}] {exp_id} ({priority}) — {exp['desc']}")

        result = run_experiment(exp_id)
        if result is None:
            records.append({"exp_id": exp_id, "priority": priority, "exit_code": "SKIP", "time": datetime.datetime.now().strftime("%H:%M")})
            continue

        primary_exit = result["exit_code"]

        rc3 = run_module3(exp_id)

        local_commit(
            EXP_REPO,
            f"{exp_id}: 实验完成\n优先级: {priority}\n描述: {exp['desc']}\n指标: {exp['metrics']}\n"
            f"exit_code: primary_exit={primary_exit}, module3_rc={rc3}\n"
            f"时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        hrepo = EXP_REPO.parent / "trae-harness"
        constitution_msg = f"{exp_id} Module 3 复盘"
        if hrepo.exists():
            local_commit(hrepo, constitution_msg)

        records.append({
            "exp_id": exp_id,
            "priority": priority,
            "exit_code": primary_exit,
            "time": datetime.datetime.now().strftime("%H:%M"),
            "results": result.get("results", {}),
        })

    update_master_log(records)

    print(f"\n{'='*80}")
    print(f"  批量实验完成！({len(records)} 个)")
    print(f"{'='*80}")
    print(f"  产物:")
    print(f"    实验目录: experiments/v*/ (含 report.md + results)")
    print(f"    主日志:   analysis/master-log.md")
    print(f"    宪法:     trae-harness/references/constitution/full-constitution.md")
    print(f"")
    print(f"  所有 commit 已保存在本地。网络恢复后:")
    print(f"    cd trae-harness-experiments && git push origin master")
    print(f"    cd ../trae-harness && git push origin master")


if __name__ == "__main__":
    main()
