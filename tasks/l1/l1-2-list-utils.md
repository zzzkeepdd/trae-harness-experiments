# 任务 L1-2：列表处理工具

## 复杂度
L1（单文件，std only，无外部依赖）

## 任务描述
实现 `list_utils.py`，包含以下函数：

1. `dedup(items: list) -> list` — 去重，保持原始顺序
2. `flatten(nested: list[list]) -> list` — 展平嵌套列表
3. `group_by(items: list, key_fn: callable) -> dict` — 按 key 函数分组
4. `top_n(items: list, n: int, key_fn: callable) -> list` — 返回前 n 大/小的元素

## 约束
- 纯 Python stdlib
- 单文件
- 函数参数需处理空列表和 None 输入
- group_by 的 value 保持原始顺序
- top_n 当 n > len(items) 时返回全部

## 验收标准
AC-1: dedup([1,2,2,3,1]) == [1,2,3] ✓
AC-2: flatten([[1,2],[3,4]]) == [1,2,3,4] ✓
AC-3: flatten([[1,[2,3]],[4]]) == [1,[2,3],4]（只展平一层）✓
AC-4: group_by([1,2,3,4], lambda x: x%2) == {1:[1,3], 0:[2,4]} ✓
AC-5: top_n([5,3,8,1,9], 3) == [5,3,8]（默认降序）✓
AC-6: top_n([5,3,8,1,9], 10) == [5,3,8,1,9]（n超范围不报错）✓
AC-7: 空列表输入不抛未处理异常 ✓

## 边界条件（提示模型思考）
- 空列表
- 嵌套多层列表的展平深度
- n=0 和 n=负数 的处理
- key_fn 返回相同值时的分组行为