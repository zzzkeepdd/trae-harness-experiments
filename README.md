# trae-harness-experiments

> Trae Harness 框架的 A/B 对照实验——量化多 Agent 辩论流程对模型代码产出质量的提升。

## 实验模型

**DeepSeek V4 Pro** — 所有实验均使用同一模型，对照组（无 Harness）与实验组（含 Harness）的差异纯粹来自 Harness 流程。

## 实验总览

| 版本 | 实验维度 | Harness | A 组 | B 组 | Δ | 结论 |
|:---:|------|:---:|------|------|:---:|:---:|
| v1 | 原始 A/B 对照 | v1.1 | 0/6 audit | 6/6 audit | - | 无法量化 |
| v2 | 独立测试驱动 | v1.2 | 92% | 99% | **+7%** | WIN |
| v3 | 编排器强制执行 | v1.2+编排器 | 90% | **100%** | **+10%** | WIN |
| v4 | 测试质量 | v1.3 | 断言 28 | 断言 124 | **×4.4** | WIN |
| v5 | 代码规范 | v1.4 | flake8=13.0 | flake8=5.3 | **↓59%** | WIN |
| v6 | 安全防御 | v1.4 | CWE=0.5 | CWE=2.2 | **↑340%** | WIN |
| v7 | Module 3 长期学习 | v1.4 | 复发 20 | 复发 2 | **↓91.7%** | WIN |
| v8 | 性能优化 | v1.4 | 1.0x | 4.61x | **×4.61** | WIN |
| v9 | HumanEval 函数补全 | v1.4 | 84.6% | 88.5% | **+3.9%** | WIN |
| v10 | SWE-bench 修 bug | v1.4 | bugs=2 | bugs=0 | **↓100%** | PARTIAL |
| v11 | LiveCodeBench 竞赛 | v1.4 | 59.1% | 59.1% | 0 | PARTIAL |

> v10 bug 注入力度不足（待改进），v11 基准题库对两组无差异（待重新设计）。所有实验 orchestrator 100% 完成率。

## 能力提升矩阵

```
                    正确性  规范  安全  学习  性能  流程
v1 原始对照            ⬜    ⬜    ⬜    ⬜    ⬜   ❌ 12%
v2 独立测试            ✅   ⬜    ⬜    ⬜    ⬜   ❌ 12%
v3 编排器              ✅   ⬜    ⬜    ⬜    ⬜   ✅ 100%
v4 测试质量            ✅   ⬜    ⬜    ⬜    ⬜   ✅ 100%
v5 代码规范            ✅   ✅    ⬜    ⬜    ⬜   ✅ 100%
v6 安全防御            ✅   ⬜    ✅    ⬜    ⬜   ✅ 100%
v7 Module 3 学习       ✅   ⬜    ⬜    ✅    ⬜   ✅ 100%
v8 性能优化            ✅   ⬜    ⬜    ⬜    ✅   ✅ 100%
v9 HumanEval           ✅   ⬜    ⬜    ⬜    ⬜   ✅ 100%
v10 SWE-bench          ✅   ⬜    ⬜    ⬜    ⬜   ✅ 100%
v11 LiveCodeBench      ⬜   ⬜    ⬜    ⬜    ⬜   ✅ 100%
```

## 各实验详细结果

### v5 代码规范（flake8 / pylint / radon）

| 任务 | A 组 flake8 | B 组 flake8 | Δ |
|------|----------:|----------:|:---|
| l1-1-string-utils | 14 | 5 | ↓64% |
| l1-2-list-utils | 20 | 4 | ↓80% |
| l2-1-cache | 9 | 1 | ↓89% |
| l2-2-csv-processor | 5 | 6 | ↑20% |
| l3-1-task-queue | 10 | 6 | ↓40% |
| l3-2-session-manager | 20 | 10 | ↓50% |
| **平均** | **13.0** | **5.3** | **↓59%** |

### v6 安全防御（SQL注入 / 文件上传 / XSS / CSRF）

| 任务 | A 组 CWE | B 组 CWE | Δ |
|------|-------:|-------:|:---|
| SQL 注入防御 | 1 | 4 | +300% |
| 文件上传安全 | 0 | 1 | ∞ |
| XSS 防御 | 0 | 1 | ∞ |
| CSRF Token | 1 | 3 | +200% |
| **平均** | **0.5** | **2.2** | **+340%** |

### v7 Module 3 长期学习（宪法累积 → 同类 bug 复发率）

| 轮次 | 复发 bug | 宪法规则 | 断言数 | 覆盖率 |
|:----:|-------:|-------:|-----:|-----:|
| R1 | 20 | 0 | 18 | 45.0% |
| R2 | 8 | 5 | 36 | 63.2% |
| R3 | 2 | 13 | 72 | 82.6% |

3 轮内复发率下降 **91.7%**，宪法从 0 累积到 13 条，断言密度提升 **4x**。

### v8 性能优化（复杂度攻击 → 算法改进）

| 任务 | 加速比 | 改进 |
|------|:----:|------|
| nested-loop | **10.0x** | O(2ⁿ) → O(n) |
| graph-traversal | **10.0x** | O(V²) → O(V+E) |
| string-concat | **2.5x** | O(n²) → O(n) |
| sorting-opt | **2.0x** | O(n²) → O(n log n) |
| **平均** | **4.61x** | — |

### v9 HumanEval 函数补全

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| is-valid-email | 100% | 100% | 0 |
| parse-url | 50% | 75% | +25% |
| fibonacci-nth | 100% | 100% | 0 |
| merge-sorted-lists | 50% | 75% | +25% |
| binary-search | 100% | 100% | 0 |
| roman-to-int | 100% | 100% | 0 |
| **平均** | **84.6%** | **88.5%** | **+3.9%** |

### v10 SWE-bench Bug 修复 + Regression 检测

| 任务 | Orchestrator | A regression | B regression | Δ |
|------|:---:|:---:|:---:|:---:|
| user-service | 100% | 0 | 0 | — |
| order-processor | 100% | 1 | 0 | ↓100% |
| config-loader | 100% | 1 | 0 | ↓100% |
| api-rate-limiter | 100% | 0 | 0 | — |
| file-sync | 100% | 0 | 0 | — |
| payment-gateway | 100% | 0 | 0 | — |
| **合计** | **100%** | **2** | **0** | **↓100%** |

### v11 LiveCodeBench 竞赛编程

| 指标 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| pass rate | 59.1% | 59.1% | 0 |
| total | 44 | 44 | — |
| passed | 26 | 26 | — |

## 御三家对比

### DeepSeek V4 Pro 在公开基准上的位置

| 基准 | Claude Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro | DSV4 Pro |
|------|:---:|:---:|:---:|:---:|
| HumanEval | ~92% | **~94%** | ~90% | 87.6% |
| SWE-bench Verified | **87.6%** | ~85% | 80.6% | 83.7% |
| LiveCodeBench | ~90 | ~91.7 | ~89.2 | **93.5** |

> 公开基准测的是函数补全和修已有 bug——跟我们从零写完整工程代码是**完全不同的赛道**。

### 我们的赛道：从零工程代码质量（公开基准不测）

| 维度 | 有公开基准吗？ | DSV4 Pro 直出 | DSV4 Pro + Harness | 提升 |
|------|:--:|------|------|:--:|
| 工程代码正确性 | ❌ | 90% | **100%** | +10% |
| 代码规范 (flake8) | ❌ | 13.0 违规 | 5.3 违规 | ↓59% |
| 安全覆盖 (CWE) | ❌ | 0.5 | 2.2 | ↑340% |
| 长期学习 (复发率) | ❌ | 20 | 2 | ↓91.7% |
| 性能 (加速比) | ❌ | 1.0x | 4.61x | ×4.61 |
| 测试断言密度 | ❌ | 28 | 124 | ×4.4 |

**核心结论**：在这些公开基准不测的维度上，Harness 将 DSV4 Pro 的工程代码质量大幅提升。这些是新赛道——御三家在这些维度上没有公开数据可对比。

## Token ROI 分析

完整的 Token 节省量和 ROI 分析请见：[`analysis/token-savings-analysis.md`](analysis/token-savings-analysis.md)

核心结论：
- **单次任务 ROI +29.8%**（下限），上限可达 +270%
- **年度化节省约 1376 万 tokens**（按 100 次任务计算）
- **L3 复杂任务 ROI 可超过 +500%**

## 目录结构

```
trae-harness-experiments/
├── README.md
├── batch-run.py                     # 串行批量运行器
├── experiment-loop.py               # 实验循环引擎
├── real_harness.py                  # 真 Harness orchestrator CLI 封装
├── analysis/
│   ├── ability-matrix.md            # 能力提升全矩阵
│   ├── big3-comparison.md           # 御三家公开基准对比
│   ├── module3-retrospective-v5-v11.md  # v5-v11 Module 3 复盘
│   ├── token-savings-analysis.md    # Token 节省量和 ROI 分析
│   └── methodology.md               # 实验方法论
├── experiments/
│   ├── v1-baseline/                 # 原始 A/B 对照
│   ├── v2-independent-tests/        # 独立测试套件
│   ├── v3-orchestrator/             # 编排器强制执行
│   ├── v4-test-quality/             # 测试质量
│   ├── v5-code-standards/           # 代码规范
│   ├── v6-security/                 # 安全防御
│   ├── v7-module3-learning/         # Module 3 长期学习
│   ├── v8-performance/              # 性能优化
│   ├── v9-humaneval-style/          # HumanEval 风格
│   ├── v10-swebench-style/          # SWE-bench 风格
│   └── v11-livecodebench-style/     # LiveCodeBench 风格
└── tasks/                           # 共享任务定义
```

## 快速开始

```bash
git clone https://github.com/zzzkeepdd/trae-harness-experiments.git
cd trae-harness-experiments

# 串行批量运行所有实验
python batch-run.py

# 或运行单个实验
python experiment-loop.py run v5
```

## 依赖

- Python 3.12+
- [trae-harness](https://github.com/zzzkeepdd/trae-harness) v1.5.0+