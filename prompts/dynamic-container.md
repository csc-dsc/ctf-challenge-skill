# DynamicContainer 题型出题指南

## 题型定义

DynamicContainer：Docker 容器化服务，每个队伍独立实例，Flag 通过 `GZCTF_FLAG` 注入。

适用：Web 漏洞（SSTI, SQLi, RCE, SSRF, XXE, File Upload），PWN（缓冲区溢出、格式化字符串、堆漏洞）。

## 平台配置字段

| 字段 | 示例 | 说明 |
|------|------|------|
| 类型 | `DynamicContainer` | |
| 环境 | `Docker` | |
| 镜像 | 完整 Registry 地址 | 如 `10.24.0.28:5000/gzctf/web/ssti:20260714-v1` |
| 内部端口 | `80` | 应用实际监听端口 |
| Flag 模板 | `flag{[TEAM_HASH]}` | 平台生成，不要手动添加 |

## 目录结构

```
category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/
│   ├── app.py（或 server.js / index.php）
│   └── ...
├── attachments/         # 如有（如源码包给选手）
│   └── source.zip
└── docker/
    ├── Dockerfile
    ├── docker-compose.test.yml
    └── healthcheck.sh
```

## 必遵守规则（违规直接打回）

1. **0.0.0.0 绑定**：Flask `host="0.0.0.0"`，Node `'0.0.0.0'`，PHP Apache 默认正确
2. **非 root 用户**：Dockerfile 必须有 `USER ctf`
3. **GZCTF_FLAG**：`os.getenv("GZCTF_FLAG", "flag{test_flag}")`，推荐启动时写入 `/flag`
4. **HEALTHCHECK**：curl 测试 HTTP 端点
5. **Exec CMD**：`CMD ["executable", "arg1", "arg2"]`
6. **端口映射**：`"0.0.0.0:18080:80"`

## Dockerfile 模板（Flask/Gunicorn）

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

RUN useradd -r -u 10001 ctf

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chown -R ctf:ctf /app

# 启动脚本：写入 Flag 再启动
COPY start.sh /start.sh
RUN chmod +x /start.sh

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

ENV PYTHONUNBUFFERED=1
EXPOSE 80
USER ctf
CMD ["/start.sh"]
```

## start.sh 模板

```bash
#!/bin/sh
set -eu
printf '%s' "${GZCTF_FLAG:-flag{local_development_only}}" > /flag
chmod 0400 /flag
exec gunicorn -b 0.0.0.0:80 -w 2 app:app
```

## app.py 模板（Flask SSTI 示例）

```python
import os
from flask import Flask, request, render_template_string

app = Flask(__name__)

# 在模块加载时读 Flag
FLAG = os.getenv("GZCTF_FLAG", "flag{local_development_only}")

@app.route('/')
def index():
    name = request.args.get('name', 'World')
    # 漏洞：render_template_string 接受用户输入
    template = '<h1>Hello {{ name }}!</h1>'
    # 有漏洞的版本：
    template = f'<h1>Hello {name}!</h1>'
    return render_template_string(template, name=name, flag=FLAG)
    # 安全的版本应该用：
    # return render_template_string('<h1>Hello {{ name }}!</h1>', name=name)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
```

## docker-compose.test.yml 模板

```yaml
services:
  challenge:
    build:
      context: .
      dockerfile: Dockerfile
    image: challenge-test:local
    container_name: challenge-test
    ports:
      - "0.0.0.0:18080:80"
    environment:
      - GZCTF_FLAG=flag{docker_local_test_flag_2024}
    restart: "no"
    stop_grace_period: 10s
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
```

## healthcheck.sh 模板

```bash
#!/bin/sh
curl -f -s -o /dev/null http://localhost:80/ || exit 1
exit 0
```

## 常见漏洞类型设计要点

### SSTI
- 问题代码：`render_template_string(f'<h1>Hello {name}!</h1>')`
- Flag 放入模板上下文或全局变量
- 预期 Payload：`{{ config.__class__.__init__.__globals__['os'].popen('cat /flag').read() }}`

### SQL 注入
- Flag 在数据库某张表的某个字段中
- 提供源码让选手审计 SQL 拼接点
- 注意：不要用 root 数据库账号

### 命令注入 / RCE
- `os.system()` 或 `subprocess` 接受用户输入
- Flag 在文件系统中（`/flag`）

### 文件上传
- 无后缀检查或内容类型验证缺失
- Flag 在 `/flag`，需要 getshell 后读取

### SSRF
- Flag 在内部服务（如 `http://internal-flag:8080/`）
- 需要多个容器（用 docker-compose 内网）

## 非预期解防范

以下做法是出题人不期望的解法，需在设计时避免：

- **Flag 直接暴露在 HTML 或 JS 源码中**：不要在页面注释里写 Flag
- **`/flag` 可直接通过 Web 路径访问**：检查 Nginx/Apache 配置
- **Docker inspect 可获取 Flag**：Flag 不要放在环境变量就完事，要运行时注入
- **`robots.txt` 或 `.git` 泄露所有源码**：清理构建产物

## 自检步骤

1. `docker build -t challenge-test docker/`
2. `docker compose -f docker/docker-compose.test.yml up -d`
3. 等待 healthy（`docker compose ps`）
4. `curl -s http://127.0.0.1:18080/` — 返回页面
5. 测试 SSTI: `curl -s "http://127.0.0.1:18080/?name={{7*7}}"` — 期望返回含 "49" 的页面
6. 获取 Flag: `curl -s "http://127.0.0.1:18080/?name={{config.__class__.__init__.__globals__['os'].popen('cat /flag').read()}}"`
7. 非 root: `docker compose -f docker/docker-compose.test.yml exec challenge id` — uid=10001
8. 停止: `time docker compose -f docker/docker-compose.test.yml down` — <10秒

全部通过后才交付给 Reviewer。
