# trae-harness-experiments

> Trae Harness 框架的 A/B 对照实验——量化多 Agent 辩论流程对模型代码产出质量的提升。

## 实验模型

**DeepSeek V4 Pro** — 所有实验均使用同一模型，对照组（无 Harness）与实验组（含 Harness）的差异纯粹来自 Harness 流程。

## 实验总览

| 版本 | 实验维度 | A 组 | B 组 | Δ | 结论 |
|:---:|------|------|------|:---:|:---:|
| v1 | 原始 A/B 对照 | 0/6 audit | 6/6 audit | - | 无法量化 |
| v2 | 独立测试驱动 | 92% | 99% | **+7%** | WIN |
| v3 | 编排器强制执行 | 90% | **100%** | **+10%** | WIN |
| v4 | 测试质量 | 断言 28 | 断言 124 | **×4.4** | WIN |
| v5 | 代码规范 | flake8=13.0 | flake8=5.3 | **↓59%** | WIN |
| v6 | 安全防御 | CWE=0.5 | CWE=2.2 | **↑340%** | WIN |
| v7 | Module 3 长期学习 | 复发 20 | 复发 2 | **↓91.7%** | WIN |
| v8 | 性能优化 | 1.0x | 4.61x | **×4.61** | WIN |
| v9 | HumanEval 函数补全 | 84.6% | 88.5% | **+3.9%** | WIN |
| v10 | SWE-bench 修 bug | bugs=2 | bugs=0 | **↓100%** | PARTIAL |
| v11 | LiveCodeBench 竞赛 | 59.1% | 59.1% | 0 | PARTIAL |
| v12 | 错误弹性 | 8.3% | **100%** | **+91.7%** | WIN |
| v13 | API 设计规范 | 12.5% | **95.8%** | **+83.3%** | WIN |
| v14 | 文档完整度 | 4.2% | **85.8%** | **+81.7%** | WIN |
| v15 | 可维护性 | 16.2% | **75.0%** | **+58.8%** | WIN |
| v16 | 链式任务 | 23.6% | **65.3%** | **+41.7%** | WIN |

> v10 bug 注入力度不足（待改进），v11 基准题库对两组无差异（待重新设计）。所有实验 orchestrator 100% 完成率。

## 能力提升矩阵

```
                    正确性  规范  安全  学习  性能  流程  弹性  API  文档  维护  链式
v1 原始对照            ⬜    ⬜    ⬜    ⬜    ⬜   ❌   ⬜   ⬜   ⬜   ⬜   ⬜
v2 独立测试            ✅   ⬜    ⬜    ⬜    ⬜   ❌   ⬜   ⬜   ⬜   ⬜   ⬜
v3 编排器              ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v4 测试质量            ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v5 代码规范            ✅   ✅    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v6 安全防御            ✅   ⬜    ✅    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v7 Module 3 学习       ✅   ⬜    ⬜    ✅    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v8 性能优化            ✅   ⬜    ⬜    ⬜    ✅   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v9 HumanEval           ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v10 SWE-bench          ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v11 LiveCodeBench      ⬜   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ⬜
v12 错误弹性            ✅   ⬜    ⬜    ⬜    ⬜   ✅   ✅   ⬜   ⬜   ⬜   ⬜
v13 API 设计            ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ✅   ⬜   ⬜   ⬜
v14 文档完整度          ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ✅   ⬜   ⬜
v15 可维护性            ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ✅   ⬜
v16 链式任务            ✅   ⬜    ⬜    ⬜    ⬜   ✅   ⬜   ⬜   ⬜   ⬜   ✅
```

## 各实验详细结果

### v2 独立测试驱动（6 个任务，同一套测试套件）
| 任务 | 级别 | A 组 | B 组 | A 失败原因 |
|------|:--:|:--:|:--:|------|
| l1-1-string-utils | L1 | 7/8 (88%) | 8/8 (100%) | `word_count` 返回空 dict |
| l1-2-list-utils | L1 | 7/7 (100%) | 7/7 (100%) | — |
| l2-1-cache | L2 | 7/7 (100%) | 7/7 (100%) | — |
| l2-2-csv-processor | L2 | 4/4 (100%) | 4/4 (100%) | — |
| l3-1-task-queue | L3 | 3/4 (75%) | 4/4 (100%) | `timeout` 未实现 |
| l3-2-session-manager | L3 | 8/10 (80%) | 10/10 (100%) | token 黑名单缺失 |
| **总计** | | **36/40 (90%)** | **40/40 (100%)** | — |

### v3 编排器强制执行（流程完整性验证）
| 指标 | 结果 |
|------|------|
| B 组流程完成率 | **90/90 步骤 (100%)** |
| 4 道质量门全部激活 | ✓ (GATE_1 + GATE_2 + TEST_GATE + AUDIT_GATE) |
| A 组通过率 | 36/40 (90%) |
| B 组通过率 | **40/40 (100%)** |
| 质量差 Δ | **+10%** |

### v4 测试质量（断言密度 + 覆盖率）
| 任务 | 级别 | A 覆盖 | B 覆盖 | A 断言 | B 断言 | A 密度 | B 密度 |
|------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| l1-1-string-utils | L1 | 100% | 100% | 7 | 34 | 1.75 | 8.5 |
| l1-2-list-utils | L1 | 100% | 100% | 5 | 24 | 1.25 | 6.0 |
| l2-1-cache | L2 | 25% | 75% | 6 | 22 | 0.75 | 2.75 |
| l2-2-csv-processor | L2 | 40% | 100% | 3 | 18 | 0.6 | 3.6 |
| l3-1-task-queue | L3 | 71% | 71% | 2 | 7 | 0.29 | 1.0 |
| l3-2-session-manager | L3 | 36% | 64% | 5 | 19 | 0.45 | 1.73 |
| **总计** | | **62%** | **85%** | **28** | **124** | **0.72** | **3.18** |

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

### v12 错误弹性（retry / circuit-breaker / input-validation / graceful-degrade）

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| retry-handler | 33.3% | 100% | +66.7% |
| circuit-breaker | 0% | 100% | +100% |
| input-validator | 0% | 100% | +100% |
| graceful-degrade | 0% | 100% | +100% |
| **平均** | **8.3%** | **100%** | **+91.7%** |

> A 组在 3/4 任务中完全未实现错误处理逻辑（0%），Harness 通过辩论引导出完整的容错模式。

### v13 API 设计规范（REST / pagination / versioning / error-format）

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| rest-api | 50.0% | 100% | +50.0% |
| pagination | 0% | 100% | +100% |
| versioning | 0% | 83.3% | +83.3% |
| error-format | 0% | 100% | +100% |
| **平均** | **12.5%** | **95.8%** | **+83.3%** |

> A 组 API 设计缺少标准化，B 组在辩论中自动对齐 RESTful 最佳实践。

### v14 文档完整度（docstrings / type-hints / readme / examples）

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| docstrings | 0% | 100% | +100% |
| type-hints | 0% | 100% | +100% |
| readme | 16.7% | 83.3% | +66.7% |
| examples | 0% | 60.0% | +60.0% |
| **平均** | **4.2%** | **85.8%** | **+81.7%** |

> A 组几乎零文档产出。Harness 辩论后自动补全 docstrings、类型注解和 README。

### v15 可维护性（DRY / circular-deps / deep-nesting / god-class）

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| dry-violation | 0% | 0% | 0 |
| circular-deps | 25.0% | 100% | +75.0% |
| deep-nesting | 20.0% | 100% | +80.0% |
| god-class | 20.0% | 100% | +80.0% |
| **平均** | **16.2%** | **75.0%** | **+58.8%** |

> DRY 任务两组均为 0%（模型在这一维度天然弱）。其余 3 项 Harness 均大幅领先。

### v16 链式任务（ETL pipeline / auth-flow / build-deploy）

| 任务 | A 组 | B 组 | Δ |
|------|:---:|:---:|:---:|
| etl-pipeline | 33.3% | 83.3% | +50.0% |
| auth-flow | 12.5% | 25.0% | +12.5% |
| build-deploy | 25.0% | 87.5% | +62.5% |
| **平均** | **23.6%** | **65.3%** | **+41.7%** |

> 链式任务对流程编排要求高，Harness 提升显著但仍有余地（auth-flow 仅 25%），说明复杂多步骤任务是硬骨头。

## v12-v16 复盘 → 宪法 v2.1

v12-v16 批次实验触发了 Module 3 复盘，产出两条新宪法规则：

| 规则 | 内容 | 实验依据 |
|:--:|------|------|
| **C40** | 多维度质量门：代码异味、复杂度、dead code、安全漏洞、性能瓶颈 — 5 维度在 TEST_GATE 统一验证 | v12 错误弹性 + v13 API 设计 + v14 文档 + v15 可维护性 |
| **C41** | 攻击维度注入机制：must_fix ↔ attacks 绑定，从复盘自动提取攻击维度 | v12-v16 全批次：攻击越精准，B 组提升越大 |

宪法同时进行了工程化重构——41 条规则按阶段拆分到 8 个文件中，每阶段 ≤7 条，AI 不再一次性接收全部规则。

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
| 错误弹性 | ❌ | 8.3% | 100% | +91.7% |
| API 设计规范 | ❌ | 12.5% | 95.8% | +83.3% |
| 文档完整度 | ❌ | 4.2% | 85.8% | +81.7% |
| 可维护性 | ❌ | 16.2% | 75.0% | +58.8% |
| 链式任务 | ❌ | 23.6% | 65.3% | +41.7% |

**核心结论**：在这些公开基准不测的维度上，Harness 将 DSV4 Pro 的工程代码质量大幅提升。这些是新赛道——御三家在这些维度上没有公开数据可对比。

## Token ROI 分析

完整的 Token 节省量和 ROI 分析请见：[`analysis/token-savings-analysis.md`](analysis/token-savings-analysis.md)

核心结论：
- **单次任务 ROI +289.5%**（下限），中位数 +529.5%，上限 +779.5%
- **上下文拆分固定净赚 7,500 tokens/次**（不管有没有 bug 都省）
- **L3 复杂任务 ROI 可超过 +1000%**

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
│   ├── master-log.md                # 主实验日志
│   ├── methodology.md               # 实验方法论
│   ├── module3-retrospective-v5-v11.md  # v5-v11 Module 3 复盘
│   ├── next-experiments-plan.md     # 后续实验路线图
│   ├── token-savings-analysis.md    # Token 节省量和 ROI 分析
│   └── v1-v2-v3-comparison.md       # 早期实验对比
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
│   ├── v11-livecodebench-style/     # LiveCodeBench 风格
│   ├── v12-error-resilience/        # 错误弹性
│   ├── v13-api-design/              # API 设计规范
│   ├── v14-documentation/           # 文档完整度
│   ├── v15-maintainability/         # 可维护性
│   └── v16-chained-tasks/           # 链式任务
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
- [trae-harness](https://github.com/zzzkeepdd/trae-harness) v2.1+
