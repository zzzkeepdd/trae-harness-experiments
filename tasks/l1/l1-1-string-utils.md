# 任务 L1-1：字符串工具函数库

## 复杂度
L1（单文件，std only，无外部依赖）

## 任务描述
实现 `string_utils.py`，包含以下函数：

1. `reverse(s: str) -> str` — 反转字符串
2. `to_title_case(s: str) -> str` — 转为标题格式（每个单词首字母大写，其余小写）
3. `is_palindrome(s: str) -> bool` — 判断回文（忽略大小写和非字母数字字符）
4. `word_count(s: str) -> dict[str, int]` — 统计每个单词出现次数

## 约束
- 纯 Python stdlib
- 单文件
- 不引入外部依赖
- 函数需处理空字符串和None输入（返回空值或抛特定异常）

## 验收标准
AC-1: reverse("hello") == "olleh" ✓
AC-2: to_title_case("HELLO WORLD") == "Hello World" ✓
AC-3: is_palindrome("A man a plan a canal Panama") == True ✓
AC-4: is_palindrome("hello") == False ✓
AC-5: word_count("hello world hello") == {"hello":2,"world":1} ✓
AC-6: 空字符串输入不抛未处理异常 ✓
AC-7: None输入不抛未处理异常 ✓

## 边界条件（提示模型思考）
- 空字符串
- None 输入
- 全大写/全小写/混合大小写
- 带空格、标点的回文检测
- 单词边界（连字符、数字算不算单词？）