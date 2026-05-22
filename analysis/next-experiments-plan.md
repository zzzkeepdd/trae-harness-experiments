# 下一步实验计划

> **实测模型**: deepseek-v4-pro（所有实验只跑这一个模型）
> **框架**: trae-harness v1.3
> **实验方法**: 纯 A/B 对照 = DSV4 Pro 直出 vs DSV4 Pro + Harness 全流程

---

## 一、实验定位

### 两条实验线

| 线 | 内容 | 与公开基准的关系 |
|------|------|------|
| **新赛道** | 现有公开基准不测的维度（测试质量、代码规范、安全设计等） | 无公开对照——我们开辟新维度 |
| **复刻线** | 用我们自己的框架复刻 HumanEval/SWE-bench/LiveCodeBench 风格的实验 | 格式一致，可以和公开数据串起来 |

两条线互补：新赛道建立独占维度，复刻线搭建桥梁。

### 背景：DSV4 Pro 在公开基准上的位置

| 基准 | Claude Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro | DeepSeek V4 Pro |
|------|:----:|:----:|:----:|:----:|
| HumanEval | ~92% | **~94%** | ~90% | 87.6% |
| SWE-bench Verified | **87.6%** | ~85%* | 80.6% | 83.7% |
| LiveCodeBench | ~90* | ~91.7* | ~89.2* | **93.5** |
| Codeforces Rating | - | 3168 | 3052 | **3206** |

> 御三家数据来源：公开技术报告 + 第三方评测，仅作背景参考。

---

## 二、已完成的实验

| # | 实验 | 验证的能力 | 结果 |
|:--:|------|----------|------|
| v1 | A/B 原始对照 | 辩论产出统计 | 方法论缺陷，数据无效（已废弃） |
| v2 | 独立测试驱动 | 代码正确性、边界处理、安全防护 | A=92% B=99% Δ=+6% |
| v3 | 编排器强制执行 | 流程完整性 (15步)、质量门全激活 | A=90% B=100% Δ=+10% |

**当前结论**: Harness 将 DSV4 Pro 的工程代码通过率从 90% 提升到 100%（+10%），消灭 4 个真实 bug。

---

## 三、待做实验

---

### 🔷 新赛道线：现有基准不测的维度

---

#### v4: 测试质量实验（P0 — 最能体现工程价值）

**验证**: C27 测试闸门 + C32 有效断言 → 测试质量提升？

```
A 组: DSV4 Pro 直出代码 + 直出测试
B 组: DSV4 Pro + Harness 全流程（C27 强制写 test_*.py + C32 有效断言检查）
```

| 指标 | 工具 | 说明 |
|------|------|------|
| 测试覆盖率 | coverage.py branch coverage | 覆盖了多少分支 |
| Mutation Score | mutmut / mutpy | 注入变异后测试能否检出（真正金标准） |
| 断言密度 | 有效断言数 / 函数数 | 测试写得有多认真 |
| 测试通过率 | 直接跑测试 | 基本正确性 |

**预期**: B 组 mutation score 比 A 组高 15~25%。

**价值**: mutation score 是工程界公认的测试质量金标准——**无一商用模型公开过此数据**。

---

#### v5: 代码规范实验（P1）

**验证**: MODULE_2_STEP_2 Code QA 真实执行 → 规范等级提升？

```
A 组: DSV4 Pro 直出代码
B 组: DSV4 Pro + Harness（Code QA 实际运行 flake8+pylint）
```

| 指标 | 工具 |
|------|------|
| flake8 违规数 | flake8 |
| pylint 评分 | pylint |
| 可维护性指数 | radon MI |
| 圈复杂度 | radon cc |

**预期**: B 组 flake8 违规减少 30~50%，pylint 评分提升 2~3 分。

---

#### v6: 安全加固实验（P1）

**验证**: 辩论能否发现安全漏洞？

新增 2 个安全专项任务：

| 新任务 | 安全场景 | 级别 |
|--------|----------|:--:|
| SQL 注入防护 | 输入过滤、参数化查询 | L3 |
| 文件上传安全 | 路径穿越、类型校验 | L3 |

| 指标 | 说明 |
|------|------|
| 安全用例通过率 | 预定义攻击向量是否被防御 |
| CWE 覆盖数 | 覆盖了多少种常见弱点类型 |

---

#### v7: Module 3 长期学习实验（P1 — Harness 独有）

**验证**: Harness 能否让 DSV4 Pro 越用越好？

```
第 1 轮: 全部任务 → 产出宪法草案
第 2 轮: 同样任务 + 2 个新任务 → 宪法版本递增 → 同类 bug 是否复发
第 3 轮: 继续累积 → 测量趋势
```

| 指标 | 说明 |
|------|------|
| 同类 bug 复发率 | 第 1 轮的 bug 在第 2、3 轮是否还出现 |
| 宪法规则命中数 | 每轮被触发执行的规则数 |

**这是 Harness 独有的能力** —— 没有任何框架能做到"使用越多次产出质量越高"。

---

#### v8: 性能意识实验（P2）

**验证**: 辩论中性能维度攻击 → 是否触发算法优化？

```
给定 O(n²) 实现的任务 → B 组辩论攻击复杂度 → 看是否优化
```

| 指标 | 说明 |
|------|------|
| 时间复杂度变化 | 静态分析 |
| Runtime benchmark | 实际跑 1000/10000 规模对比 |

---

### 🔷 复刻线：对标公开基准

---

#### v9: HumanEval 风格实验（P3 — 天花板低，做完整性覆盖）

**对标**: 公开 HumanEval 基准
**优势**: 任务简单、测试用例好写、可以跟公开数据串起来
**劣势**: HumanEval 天花板本身就高（御三家 90%+），提升空间小

```
任务: 6 个函数补全任务（is_valid_email、parse_url、fibonacci 等）
A 组: DSV4 Pro 直出函数
B 组: DSV4 Pro + Harness 全流程
评估: 预定义 test case 通过率
```

**预期**: B 组提升 3~5%。目标是验证 Harness 对这个场景**至少不降低质量**。

---

#### v10: SWE-bench 风格实验（P0 — 最重要的桥梁实验）

**对标**: 公开 SWE-bench Verified 基准
**为什么最重要**: 修 bug 需要理解代码上下文、判断副作用、覆盖边界——**正是辩论的强项**。格式跟 SWE-bench 一致，可以跟各家公开数据并排对比。

```
任务: 准备 6 个含已知 bug 的小型代码库 + issue 描述
A 组: DSV4 Pro 直接修 bug
B 组: DSV4 Pro + Harness 全流程（辩论阶段攻击"你的修复有没有破坏其他功能？边界case呢？"）
评估: bug 修复率 + 是否引入新 bug（regression test）
```

| 指标 | 说明 |
|------|------|
| bug 修复率 | 正确修复的 bug / 总 bug |
| regression 数 | 修复过程中引入的新 bug |
| 修复质量分 | 修复率 - regression * 惩罚系数 |

**准备**: 6 个小型 Python 代码库，每个含 2-3 个已知 bug，参考 SWE-bench 的 issue 格式描述。

**预期**: B 组 bug 修复率比 A 组高 15~25%，regression 数减少 50%+。

**价值**: 这是唯一能把 Harness 实验和公开基准串起来的实验——结果是"DSV4 Pro + Harness 在 SWE-bench 风格修复率 = X%，对比 Claude 4.7 公开 SWE-bench = 87.6%"。不再是 ❓。

---

#### v11: LiveCodeBench 风格实验（P3 — 天花板最低）

**对标**: 公开 LiveCodeBench 基准
**劣势**: DSV4 Pro 竞赛编程已超越御三家（Codeforces 3206），Harness 能帮的有限，提升空间极小

```
任务: 6 道算法题（从 LeetCode Medium/Hard 抽取）
A 组: DSV4 Pro 直出
B 组: DSV4 Pro + Harness（辩论检查边界case、复杂度）
评估: test case 通过率
```

**预期**: B 组提升 2~3%。做完整性覆盖，但不要报太高期望。

---

## 四、实验优先级矩阵

| 优先级 | 实验 | 核心指标 | 分类 | 为什么 |
|:--:|------|------|:--:|------|
| **P0** | v4 测试质量 | mutation score | 新赛道 | 工程金标准，无人公开过 |
| **P0** | v10 SWE-bench 风格 | bug 修复率 + regression | 复刻线 | **唯一能跟公开基准串起来的实验** |
| **P1** | v5 代码规范 | flake8 + pylint + radon | 新赛道 | 长期可维护性 |
| **P1** | v7 Module 3 长期学习 | 同类 bug 复发率 | 新赛道 | **Harness 独占** |
| **P1** | v6 安全加固 | 安全用例通过率 | 新赛道 | 工程代码核心维度 |
| **P2** | v8 性能意识 | 时间复杂度 + benchmark | 新赛道 | 锦上添花 |
| **P3** | v9 HumanEval 风格 | 函数补全通过率 | 复刻线 | 天花板低，做完整性覆盖 |
| **P3** | v11 LiveCodeBench 风格 | 算法题通过率 | 复刻线 | DSV4 已领先，提升极小 |

---

## 五、实验路线图

```
已完成(新赛道)                  待做(新赛道)                   待做(复刻线)
───────────                  ────────────                   ───────────
v2: 代码正确性 (+6%)         v4: 测试质量 (mutation)        v10: SWE-bench 修bug
v3: 流程完整性 (+10%)        v5: 代码规范 (flake8/pylint)   v9: HumanEval 函数补全
                              v6: 安全加固 (OWASP)           v11: LiveCodeBench 竞赛
                              v7: 长期学习 (3轮)
                              v8: 性能意识 (benchmark)

建议顺序: v4 → v10 → v5 → v6 → v7 → v8 → v9 → v11
         (先做两个 P0，然后新赛道线，最后复刻线收尾)
```

---

## 六、核心叙事

> 现有 AI 编程基准（HumanEval / SWE-bench）测"填空"和"修 bug"——我们不仅测这些，还测他们没测过的。DSV4 Pro 直出代码通过率 90%，经 Harness 全流程后达到 100%(+10%)。下一步实验在两条线上同时推进：新赛道线量化测试质量/代码规范/安全设计的首次数据；复刻线用 SWE-bench 风格实验搭桥，让 Harness 结果可以和公开基准并排对比。

---

## 七、新对话实验清单

1. **克隆仓库**: `git clone https://github.com/zzzkeepdd/trae-harness-experiments.git`
2. **按建议顺序运行**:
   - `experiments/v4-test-quality/` — 测试质量 (mutation score + coverage)
   - `experiments/v10-swebench-style/` — 修 bug (bug 修复率 + regression)
   - `experiments/v5-code-standards/` — 代码规范 (flake8 + pylint)
   - `experiments/v6-security/` — 安全加固 (OWASP)
   - `experiments/v7-module3-learning/` — 长期学习 (3 轮)
   - `experiments/v8-performance/` — 性能意识 (benchmark)
   - `experiments/v9-humaneval-style/` — 函数补全
   - `experiments/v11-livecodebench-style/` — 竞赛编程
3. **每次实验后**更新 `analysis/ability-matrix.md`
