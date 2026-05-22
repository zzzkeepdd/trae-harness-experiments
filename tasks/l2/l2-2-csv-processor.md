# 任务 L2-2：CSV数据处理器

## 复杂度
L2（中等复杂度，涉及文件IO、数据转换、错误处理）

## 任务描述
实现 `csv_processor.py`，读取 CSV 文件，按条件过滤、聚合后输出。

1. `read_csv(path: str, encoding: str = "utf-8") -> list[dict]` — 读取CSV为字典列表
2. `filter_rows(data: list[dict], conditions: dict) -> list[dict]` — 按条件过滤
3. `aggregate(data: list[dict], group_by: str, agg_fn: dict) -> list[dict]` — 分组聚合
4. `write_csv(data: list[dict], path: str) -> None` — 写入CSV
5. `process_pipeline(input_path, output_path, filter_cond, group_by_col, agg_col, agg_op) -> None` — 完整流程

## 约束
- 纯 Python stdlib（csv 模块）
- 不使用 pandas
- 读取不存在的文件返回空列表（不抛异常）
- 写入时自动创建父目录
- 空数据文件处理不崩
- CSV 列名大小写敏感
- 聚合操作支持: sum, count, avg, min, max

## 验收标准
AC-1: 读取存在的CSV返回正确的字典列表 ✓
AC-2: 读取不存在的CSV返回空列表不抛异常 ✓
AC-3: filter_rows按单条件过滤正确 ✓
AC-4: filter_rows支持多条件AND过滤 ✓
AC-5: aggregate按列分组并求和(sum)正确 ✓
AC-6: aggregate支持count/avg/min/max ✓
AC-7: write_csv写入的文件可重新读取（往返一致性）✓
AC-8: 写入到不存在目录时自动创建目录 ✓
AC-9: 空CSV文件处理不抛异常 ✓
AC-10: 列名不存在时聚合返回空列表不崩 ✓
AC-11: process_pipeline端到端正确 ✓
AC-12: CSV含特殊字符(如逗号、换行、引号)正确处理 ✓

## 边界条件（提示模型思考）
- CSV文件不存在
- CSV文件为空
- CSV含有引号包裹的逗号字段
- 列名不存在
- 聚合列包含非数字值
- 多进程同时写入同一文件
- 文件编码问题（latin-1、gbk）