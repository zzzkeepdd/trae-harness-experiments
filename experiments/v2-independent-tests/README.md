# v2: 独立测试驱动实验

> **Harness 版本**: v1.2 | **模型**: deepseek-v4-pro

## 实验设计

在 v1 上改进：用独立测试套件替代 Harness 审计器作为评估手段。

每个任务基于验收条件预定义了 TestResult 用例，覆盖 normal/boundary/edge/security 场景。A、B 两组代码分别加载到独立的 namespace 中跑同一套测试。

## 结果

| | A 组 | B 组 |
|------|:--:|:--:|
| 通过率 | 72/78 (92%) | 77/78 (99%) |
| 失败 | 6 | 1 |

**质量差值: +6%**

### A 组失败
- **l1-1-string-utils**: `word_count` (3 用例) — 返回空 dict
- **l3-1-task-queue**: `timeout` — AC-6 从未实现
- **l3-2-session-manager**: `logout` + `relogin` — token 黑名单缺失

### B 组失败
- **l1-1-string-utils**: `is_palindrome` 空字符串 — 边界修复

## 经验教训

- ✅ 独立测试套件量化评估有效
- ❌ Harness 流程仍只执行 ~12%（仅部署+审计，跳过了 7 个 Phase）
- ❌ 质量门形同虚设
- ✅ L3 任务 Harness 效果显著（+13%~+17%）

## 运行

```bash
python experiment_v2.py
```

## 原始数据

参见 `results/` 目录，包含 A/B 两组所有任务的原始代码、debate-output.json 和结果。
