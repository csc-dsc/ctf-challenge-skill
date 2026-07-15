# 通用出题规范（所有题型共享）

以下规范适用于所有题型，无论是否涉及 Docker。

## Flag 处理

1. 动态 Flag 只能通过 `GZCTF_FLAG` 环境变量读取
2. 不要在 Dockerfile、源码注释、Git 历史、日志中写入真实 Flag
3. 推荐格式：`flag{lowercase_ascii_and_digits}`
4. 静态 Flag 不包含换行、前后空格、不可见字符
5. 不使用真实密码、手机号、身份证号等信息

## 题目命名

- 格式：`分类-知识点-难度-版本`
- 示例：`Web-SSTI-Easy-v1`, `IR-Windows-EventLog-Medium-v2`
- 文件名、脚本路径用小写英文、数字、短横线
- 平台显示名可以用中文

## 交付包必须包含

- `README.md`：完整元数据（赛制、分类、难度、初始分、类型、环境、镜像、端口、资源、网络、Flag规则、附件、验证、清理）
- `statement.md`：选手视角题面，不含任何答案或提示
- `writeup.md`：完整解题步骤（内部资料）
- `flag-policy.md`：Flag 格式、读取方式、生命周期

## 题面规范

必须包含：任务背景、明确目标、Flag 格式、附件说明（如有）、环境启动说明（如需）、端口说明、允许/禁止事项

禁止：模糊用语（"自己试试"）、错误端口、废弃镜像地址、管理端路径或凭据、任何解题提示

## 跨平台 Python 兼容性

Checker.py 和 exp.py 可能在 Windows 上运行（出题人本地测试）。**禁止使用 Windows 不支持的 API**：

| 禁止 | 替代方案 |
|------|----------|
| `socket.MSG_DONTWAIT` | `sock.settimeout(0.5)` + try/except `socket.timeout` |
| `os.kill(pid, signal.SIGKILL)` | `os.kill(pid, signal.SIGTERM)` |
| `fcntl` 模块 | `socket` 原生方法 |
| 硬编码 `/tmp/` 路径 | `tempfile.gettempdir()` 或跨平台路径 |

AWDP Checker 和 Exp 中如需非阻塞 socket 读取，使用以下模式：
```python
sock.settimeout(0.5)
try:
    data = sock.recv(4096)
except socket.timeout:
    data = b""
```

## 通用自检

- [ ] 标题、分类、难度和分值正确
- [ ] 题面无答案泄漏
- [ ] 正确答案可稳定复现
- [ ] 错误答案不得分
- [ ] 所有文件名仅用安全字符
- [ ] 无作者个人信息、绝对路径、编辑器缓存
- [ ] Checker/Exp 无 Windows 不兼容 API（MSG_DONTWAIT 等）

## API 导入（v2）

当用户配置了平台凭据（`GZCTF_HOST` + `GZCTF_TOKEN`），reviewer 通过后：

1. Read `prompts/_api.md` 了解完整的 API 规范和字段映射
2. 从 README.md 提取元数据，构造 challenge JSON（各题型字段映射见对应 prompt）
3. 根据题目类型选择正确的字段：DynamicContainer 用 `flagTemplate`，其他用 `flags` 数组
4. 先用 `ctf_client.py image` 子命令注册镜像，再用 `ctf_client.py challenge import` 导入题目
5. 保存操作结果到 `import-result.json`
6. 如导入失败，根据错误码修正（参见 `_api.md` 的"错误恢复"表）

如用户未配置凭据，按 v1 流程输出手动操作说明。
