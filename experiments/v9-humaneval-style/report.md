# V9 HUMANEVAL STYLE 实验报告

> 模型: deepseek-v4-pro | Harness: trae-harness v1.3 | 时间: 2026-05-23 05:04

## 实验设计

A组: DSV4 Pro 直出代码 + 直出测试
B组: DSV4 Pro + Harness 全流程

两组使用同一套源代码(main.py)，仅测试文件不同。

## 核心指标

| 指标 | A 组 (无Harness) | B 组 (+Harness) | 提升 |
|------|:---:|:---:|:---:|
| 平均覆盖率 | 0% | 0% | +0% |
| 断言数 | 0 | 0 | 0.0x |
| 断言密度 | 0.00 | 0.00 | 0.0x |
| 变异分 | 0% | 0% | +0% |

## 结论

Harness C27+C32 将 DSV4 Pro 测试覆盖率从 0% 提升到 0% (+0%)，断言密度提升 0.0x。


