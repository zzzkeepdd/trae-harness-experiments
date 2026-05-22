# 任务 L3-2：多用户会话管理服务

## 复杂度
L3（复杂，涉及JWT、角色权限、会话状态、并发安全）

## 任务描述
实现 `session_manager.py`，一个带JWT认证和RBAC权限管理的多用户会话服务。

1. `User(id, username, password_hash, roles: list[str])` — 用户对象
2. `TokenPayload(user_id, username, roles, exp)` — Token载荷
3. `SessionManager(secret_key: str, token_ttl: int=3600)` — 会话管理器
4. `register(username, password) -> user_id` — 注册用户
5. `login(username, password) -> token` — 登录，返回JWT
6. `verify_token(token) -> TokenPayload` — 验证Token
7. `refresh_token(old_token) -> new_token` — 刷新Token
8. `logout(user_id)` — 登出，使所有token失效
9. `check_permission(user_id, permission: str) -> bool` — 权限检查
10. `get_online_users() -> list[str]` — 获取在线用户列表

## 权限规则
- `admin` 角色：拥有所有权限
- `user` 角色：拥有 read 权限
- `editor` 角色：拥有 read + write 权限
- `viewer` 角色：只有 read 权限

## 约束
- 纯 Python stdlib（hmac, hashlib, time, base64, json, threading）
- 不使用第三方JWT库，手写JWT编码/解码
- 密码使用 bcrypt 风格的安全哈希（stdlib模拟：salt+hash）
- Token 过期自动失效
- 支持 Token 黑名单（logout后原Token立即失效）
- 会话数据存储在内存中，线程安全
- 每个用户可同时持有一个有效Token（旧Token自动失效）

## 验收标准
AC-1: register后用户可登录并获取Token ✓
AC-2: 错误密码登录失败，不返回Token ✓
AC-3: verify_token返回正确的Payload，字段完整 ✓
AC-4: Token过期后verify失败并返回None ✓
AC-5: refresh_token生成新Token，旧Token失效 ✓
AC-6: logout后所有Token失效 ✓
AC-7: check_permission正确识别admin拥有所有权限 ✓
AC-8: check_permission正确识别各角色的权限边界 ✓
AC-9: 并发登录同一用户，旧Token被替换 ✓
AC-10: get_online_users返回当前有效会话用户列表 ✓
AC-11: 同一用户注册两次（相同用户名）被拒绝 ✓
AC-12: 空用户名/空密码注册被拒绝 ✓
AC-13: 篡改Token内容后verify失败 ✓
AC-14: 多线程并发操作会话不崩溃 ✓

## 边界条件（提示模型思考）
- JWT签名验证被篡改的Token
- Token格式错误（不是有效的base64）
- Token过期和已登出同时发生
- 并发login/logout的竞态条件
- 密码强度检查（是否需要）
- Token泄露风险（黑名单机制）
- 内存会话数据的持久化缺失（仅内存，重启丢失）