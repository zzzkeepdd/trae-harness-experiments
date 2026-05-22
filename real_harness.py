import sys
import subprocess
import json
from pathlib import Path

PYTHON_EXE = r"C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
HARNESS_SCRIPTS = Path(r"d:\harness测试\trae-harness\scripts")
HARNESS_ORCHESTRATOR = HARNESS_SCRIPTS / "harness_orchestrator.py"

PHASES = [
    "INIT", "PHASE_0", "PHASE_1", "PHASE_2", "GATE_1",
    "PHASE_3", "PHASE_4", "GATE_2", "PHASE_5",
    "MODULE_2_STEP_1", "TEST_GATE", "MODULE_2_STEP_2", "MODULE_2_STEP_3",
    "AUDIT_GATE", "DONE",
]

REQUIRED_FILES = {
    "PHASE_0": ["complexity-level.txt"],
    "PHASE_1": ["research-brief.md"],
    "PHASE_2": ["debate-output.json"],
    "PHASE_3": ["review-summary.md"],
    "PHASE_4": ["spec.md", "execution-manifest.json"],
    "PHASE_5": [".handover-complete"],
    "MODULE_2_STEP_2": ["code-qa-report.md"],
    "MODULE_2_STEP_3": ["func-qa-report.md"],
}


def init_harness(task_dir, project_name, level="L2"):
    td = Path(task_dir)
    if not td.exists():
        td.mkdir(parents=True)
    r = subprocess.run(
        [PYTHON_EXE, str(HARNESS_ORCHESTRATOR), "init", str(td), "--name", project_name],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f"init failed: {r.stderr}")
    r = subprocess.run(
        [PYTHON_EXE, str(HARNESS_ORCHESTRATOR), "set-level", str(td), "--level", level],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        raise RuntimeError(f"set-level failed: {r.stderr}")


def advance_harness(task_dir):
    r = subprocess.run(
        [PYTHON_EXE, str(HARNESS_ORCHESTRATOR), "advance", str(task_dir)],
        capture_output=True, text=True, timeout=60
    )
    ok = r.returncode == 0
    msg = (r.stdout + r.stderr).strip()
    return ok, msg


def run_harness_full(task_dir, productions):
    init_harness(task_dir, task_dir.name)

    events = []
    for i in range(20):
        state_file = task_dir / ".harness_state.json"
        if not state_file.exists():
            events.append(("ERROR", False, "no state file"))
            break

        state = json.loads(state_file.read_text(encoding="utf-8"))
        current = state["current_phase"]

        if current == "DONE":
            events.append(("DONE", True, "complete"))
            break

        phase = current
        if phase in productions:
            productions[phase]()

        ok, msg = advance_harness(task_dir)
        events.append((phase, ok, msg[:100]))

        if not ok:
            break

    passed = sum(1 for _, ok, _ in events if ok)
    total = len(events)
    return passed, total, events


def build_productions(task_dir, level, attacks, must_fix):
    def p0():
        (task_dir / "complexity-level.txt").write_text(f"complexity: {level}\n")

    def p1():
        (task_dir / "research-brief.md").write_text("# Research\n- stdlib Python 3.12\n- PEP8 compliant\n- OWASP reviewed\n")

    def p2():
        data = {
            "rounds_completed": 2 if level == "L3" else 1,
            "converged": True,
            "complexity_level": level,
            "must_fix": must_fix,
            "attacks": attacks,
            "dimensions_covered": [
                {"name": "boundary & correctness", "status": "covered"},
                {"name": "safety & security", "status": "covered"},
            ],
        }
        (task_dir / "debate-output.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def p3():
        (task_dir / "review-summary.md").write_text("# Review\n- All dimensions covered\n- PASS\n")

    def p4():
        (task_dir / "spec.md").write_text(f"# Spec\n## Acceptance Criteria\n- {level} task\n- All edge cases enumerated\n")
        manifest = {"tasks": [{"id": "main", "input_schema": {}, "output_schema": {}}]}
        (task_dir / "execution-manifest.json").write_text(json.dumps(manifest, indent=2))

    def p5():
        (task_dir / ".handover-complete").write_text("confirmed\n")

    def p2_2():
        (task_dir / "code-qa-report.md").write_text("# Code QA\nTests executed: ALL PASSED\nLint: 0 errors\nCoverage: verified\n")

    def p2_3():
        (task_dir / "func-qa-report.md").write_text("# Func QA\nE2E: ALL PASSED\nRegression: 0\nSecurity: passed\n")

    return {
        "PHASE_0": p0, "PHASE_1": p1, "PHASE_2": p2,
        "PHASE_3": p3, "PHASE_4": p4, "PHASE_5": p5,
        "MODULE_2_STEP_2": p2_2, "MODULE_2_STEP_3": p2_3,
    }
