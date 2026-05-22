# trae-harness-experiments

> Trae Harness 框架的 A/B 对照实验——量化多 Agent 辩论流程对模型代码产出质量的提升。

## 实验模型

**deepseek-v4-pro** — 所有实验均使用同一模型，对照组（无 Harness）与实验组（含 Harness）的差异纯粹来自 Harness 流程。

## 实验总览

| 版本 | 名称 | Harness 版本 | A 组通过率 | B 组通过率 | 质量差值 |
|:---:|------|:---:|:---:|:---:|:---:|
| v1 | 原始 A/B 对照 | v1.1 | N/A (0/6 audit) | N/A (6/6 audit) | 无法量化 |
| v2 | 独立测试驱动 | v1.2 | 92% (72/78) | 99% (77/78) | **+6%** |
| v3 | 编排器强制执行 | v1.2+编排器 | 90% (36/40) | **100% (40/40)** | **+10%** |

## 能力提升矩阵

| 能力维度 | v1 | v2 | v3 | 说明 |
|----------|:--:|:--:|:--:|------|
| 代码正确性 | - | ✅ +6% | ✅ +10% | 独立测试套件量化 |
| 边界处理 | - | ✅ | ✅ | None/空值边界修复 |
| 安全防护 | - | ✅ | ✅ | JWT none-attack, token blacklist |
| 核心需求落地 | - | ✅ | ✅ | AC-6 timeout, AC-7 shutdown |
| 流程完整性 | ❌ 12% | ❌ 12% | ✅ 100% | 编排器 4 道质量门 |
| 测试质量 | ❌ | ❌ | ❌ | 待测 (C32 已堵 assert True) |
| 代码规范 | ❌ | ❌ | ❌ | 待测 |
| Module 3 复盘 | ❌ | ❌ | ❌ | 待测 (C31 已纳入编排器) |

## 目录结构

```
trae-harness-experiments/
├── README.md                       # 本文件
├── tasks/                          # 测试任务定义（跨版本复用）
│   ├── l1/
│   ├── l2/
│   └── l3/
├── experiments/
│   ├── v1-baseline/                # v1: A/B 原始比对
│   ├── v2-independent-tests/       # v2: 独立测试套件
│   └── v3-orchestrator/            # v3: 编排器强制执行
├── analysis/
│   ├── ability-matrix.md           # 能力提升全矩阵
│   ├── v1-v2-v3-comparison.md      # 三版横向对比
│   └── methodology.md              # 实验方法论
└── scripts/
    └── test_suite.py               # 独立测试套件
```

## 快速开始

```bash
# 克隆实验库
git clone https://github.com/zzzkeepdd/trae-harness-experiments.git
cd trae-harness-experiments

# 运行 v3 实验
cd experiments/v3-orchestrator
python experiment_v3.py
```

## 依赖

- Python 3.12+
- [trae-harness](https://github.com/zzzkeepdd/trae-harness) (git submodule)
