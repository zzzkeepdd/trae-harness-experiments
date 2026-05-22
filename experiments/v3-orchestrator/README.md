# v3: 编排器强制执行实验

> **Harness 版本**: v1.2 + 编排器 v1.0 | **模型**: deepseek-v4-pro

## 实验设计

在 v2 上改进：将编排器 15 步状态机内联到实验脚本中，B 组必须走完全部步骤才能产出代码。4 道质量门（GATE_1 辩论验证、GATE_2 可测性、TEST_GATE 测试覆盖、AUDIT_GATE 审计）全部激活并实际执行。

## 编排器流程

```
INIT→PHASE_0→PHASE_1→PHASE_2→GATE_1→PHASE_3→PHASE_4→GATE_2
→PHASE_5→M2_STEP_1→TEST_GATE→M2_STEP_2→M2_STEP_3→AUDIT_GATE→DONE
```

## 结果

| | A 组 | B 组 |
|------|:--:|:--:|
| 通过率 | 36/40 (90%) | **40/40 (100%)** |
| 失败 | 4 | 0 |
| 流程执行 | 2 步 | **15 步 (100%)** |
| 质量门 | 0/4 | **4/4** |

**质量差值: +10%**

### B 组管线

所有 6 个任务 90/90 步骤通过，4 道门全部绿灯。

### A 组失败（同 v2）
- **l1-1-string-utils**: `word_count` 空返回
- **l3-1-task-queue**: `timeout` 未实现
- **l3-2-session-manager**: `logout` + `relogin` token 无效化缺失

## 经验教训

- ✅ 编排器 100% 保证流程执行
- ✅ C10 分级评分门槛、C27 测试闸门、C28 golden negative 全部生效
- ❌ Module 3（复盘宪法）未纳入编排器（C31 已修复）
- ❌ TEST_GATE 只检查测试文件存在，未检查断言质量（C32 已修复）
- ❌ code-qa 产出是 mock 而非真实执行（C33 已修复）

## 运行

```bash
python experiment_v3.py
```

## 原始数据

参见 `results/v3_results.json`。
