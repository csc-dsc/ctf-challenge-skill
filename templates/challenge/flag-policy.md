# Flag Policy - {题目标题}

## Flag 格式
`flag{[a-zA-Z0-9_\-]+}`

## Flag 类型
{静态 Flag / 动态 Flag (GZCTF_FLAG)}

## Flag 读取方式
```python
import os
FLAG = os.getenv("GZCTF_FLAG", "flag{local_development_only}")
```

## Flag 存储位置（容器内）
- 文件路径：`/flag`
- 权限：`0400` (chmod 400)
- 写入时机：容器启动时（start.sh）

## Flag 生命周期
1. **注入**：平台通过 `GZCTF_FLAG` 环境变量注入
2. **写入**：`start.sh` 将 Flag 写入 `/flag`
3. **访问**：通过预期的漏洞路径访问
4. **验证**：平台校验提交的 Flag 与 `GZCTF_FLAG` 一致

## 测试 Flag
本地测试使用: `flag{test_flag_for_local_validation_only}`

## 安全要求
- 不在 Dockerfile 中 ENV GZCTF_FLAG=真实值
- 不在源码注释、Git 历史、日志中记录 Flag
- 不在镜像 layer 中残留 Flag
- 管理员测试实例注入的测试 Flag ≠ 正式比赛 Flag
