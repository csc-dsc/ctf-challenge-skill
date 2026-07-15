---
name: ctf-challenge-creator
description: >
  为隐域安全综合演练平台创建符合规范的 CTF/AWDP/理论 题目。
  支持 StaticAttachment, StaticContainer, DynamicAttachment, DynamicContainer,
  AWDP, Windows VM, Theory 七种题型。
  采用 Reviewer agent 做质量门禁，最多 3 轮修订，端到端 Docker 测试通过才交付。
---

# CTF Challenge Creator

为隐域安全综合演练平台创建高质量题目。你作为 planner+builder，负责生成题目文件；
ctf-reviewer agent 作为质量门禁，负责规范检查和 Docker 端到端测试。

## 工作流程

```
用户描述题目需求
  → 你分析需求，确定题型
  → 你创建完整题目交付包（所有文件）
  → 你本地 docker build + test
  → 你 spawn ctf-reviewer agent（独立验证）
  → review.md 返回结果
  → 如 CRITICAL/HIGH 问题：修复 → 重新 spawn reviewer（最多 3 轮）
  → 如 PASS：交付完成
```

## 题型路由

根据用户需求自动匹配题型，加载对应 prompt 模板：

| 用户关键词 | 题型 | 环境 | Prompt |
|-----------|------|------|--------|
| Web/PWN 在线环境、动态实例、容器 | DynamicContainer | Docker | `prompts/dynamic-container.md` |
| 固定 Web/PWN 环境、Windows 靶机 | StaticContainer | Docker/WindowsVM | `prompts/static-container.md` |
| Crypto/Reverse/取证/压缩包/流量包 | StaticAttachment | None | `prompts/static-attachment.md` |
| 每队独立附件/配置文件 | DynamicAttachment | None | `prompts/dynamic-attachment.md` |
| AWDP/攻防/Checker/Exp/修补 | AWDP | Docker | `prompts/awdp.md` |
| Windows 镜像/QCOW2/RDP | Windows VM | WindowsVM | `prompts/windows-vm.md` |
| 单选/多选/判断/题库 | Theory | None | `prompts/theory.md` |

确定题型后，**你必须 Read 对应的 prompt 文件**，它包含该题型的详细要求和常见陷阱。

## 题目交付包目录（必须严格遵守）

```
challenge-name/
├── README.md                 # 题目说明、部署参数、验收步骤
├── statement.md              # 选手看到的题面
├── writeup.md                # 标准解法（内部资料，不发给选手）
├── flag-policy.md            # Flag 读取方式和规则
├── attachments/              # 对外附件
├── source/                   # 题目源码
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   └── healthcheck.sh
├── awdp/                     # 仅 AWDP 题型
│   ├── checker.py
│   ├── exp.py
│   └── patch-example/
│       └── update.sh
└── vm/                       # 仅 Windows VM 题型
    ├── image.sha256
    └── build-notes.md
```

README.md 必须包含：
```markdown
# 题目名称
- 赛制：CTF / AWDP / 理论 / 培训
- 分类：Web / Pwn / Forensics / IR 等
- 难度：
- 初始分：
- 题目类型：StaticAttachment / StaticContainer / DynamicAttachment / DynamicContainer
- 环境类型：None / Docker / WindowsVM
- 镜像：完整 Registry 地址或 VM 模板文件名
- 容器内部端口：
- 建议资源：CPU / 内存 / 存储
- 网络模式：Open / Isolated
- Flag 规则：
- 附件：
- 正确解法验证：
- 清理方法：
```

## 命名规范

- 题目名：`分类-知识点-难度-版本`，如 `Web-SSTI-Easy-v1`
- 文件路径和脚本用小写英文、数字、短横线
- Docker 镜像：`<registry>/<namespace>/<category>/<name>:<version>`，禁止只用 `latest`
- Flag 格式：`flag{lowercase_ascii_and_digits}`
- 动态 Flag 读取 `GZCTF_FLAG` 环境变量，不要自行生成

---

## Docker 容器题核心规则（CRITICAL - 违反即打回）

### C1: 端口绑定必须是 0.0.0.0
```python
# 正确
app.run(host="0.0.0.0", port=80)
```
```javascript
// 正确
app.listen(80, '0.0.0.0');
```
绝对不能监听 `127.0.0.1`。

### C2: 必须使用非 root 用户
```dockerfile
RUN useradd -r -u 10001 ctf && chown -R ctf:ctf /app
USER ctf
```

### C3: Flag 只能通过 GZCTF_FLAG 环境变量读取
```python
FLAG = os.getenv("GZCTF_FLAG", "flag{local_development_only}")
```
- 不要在 Dockerfile 中 `ENV GZCTF_FLAG=真实Flag`
- 不要在镜像 layer、日志中写入正式 Flag
- 推荐在启动脚本中将 Flag 写入 `/tmp/flag` 或 `/flag`

### C4: 必须有 HEALTHCHECK
```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1
```

### C5: CMD 必须用 exec 形式（处理 SIGTERM）
```dockerfile
CMD ["gunicorn", "-b", "0.0.0.0:80", "app:app"]
```
非 exec 形式会导致 SIGTERM 无法传递，容器需 10-30 秒内退出。

### C6: docker-compose.test.yml 端口映射必须用 0.0.0.0
```yaml
ports:
  - "0.0.0.0:18080:80"
```

### C7: 不依赖特权模式、Docker Socket、宿主机固定路径

### C8: 清理 apt 缓存减小镜像体积
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends pkg \
    && rm -rf /var/lib/apt/lists/*
```

### C9: Docker 构建上下文 = docker/ 目录
`docker build` 命令从 `docker/` 目录执行，Dockerfile 中的 `COPY` 只能访问 docker/ 内的文件。
**创建题目时必须把 Dockerfile 需要的文件全部复制到 docker/ 下：**
```bash
# 源码在 source/，Dockerfile 在 docker/ — 必须先复制
cp source/app.py docker/
cp source/requirements.txt docker/
# 或者：cp -r source/app/ docker/app/
```
绝对不要在 Dockerfile 里写 `COPY ../source/file .`，这会被 Docker 拒绝。

### C10: PWN 题必须装 build-essential
编译 C/C++ 源码时，只装 `gcc` 不够（缺 `libc6-dev` 头文件）。直接用 `build-essential` 包：
```dockerfile
RUN apt-get install -y build-essential  # 包含 gcc, g++, make, libc6-dev
```

---

## Dockerfile 基线模板

### Python (Flask/Gunicorn)
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 80

RUN useradd -r -u 10001 ctf && chown -R ctf:ctf /app
USER ctf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:80/ || exit 1

CMD ["gunicorn", "-b", "0.0.0.0:80", "-w", "2", "app:app"]
```

### Node.js (Express)
```dockerfile
FROM node:20-alpine

RUN addgroup -S ctf && adduser -S ctf -G ctf -u 10001
WORKDIR /app
COPY --chown=ctf:ctf package*.json ./
RUN npm ci --production
COPY --chown=ctf:ctf . .

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:3000/ || exit 1

USER ctf
CMD ["node", "server.js"]
```

### PHP (Apache)
```dockerfile
FROM php:8.2-apache

RUN groupadd -r ctf && useradd -r -g ctf -u 10001 ctf
COPY --chown=ctf:ctf ./app /var/www/html/
RUN sed -i 's/Listen 80/Listen 0.0.0.0:80/' /etc/apache2/ports.conf

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

USER ctf
EXPOSE 80
CMD ["apache2-foreground"]
```

### PWN (xinetd)
```dockerfile
FROM ubuntu:22.04

# 换清华源加速（国内必备）
RUN sed -i 's|http://archive.ubuntu.com|http://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list

RUN apt-get update && apt-get install -y --no-install-recommends \
    xinetd build-essential netcat-openbsd curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r ctf && useradd -r -g ctf -u 10001 -m -d /home/ctf ctf

# 编译源码（源码须已在 docker/ 目录下）
COPY app/ /home/ctf/app/
RUN cd /home/ctf/app && make && cp challenge /home/ctf/ && chmod 755 /home/ctf/challenge && rm -rf /home/ctf/app

COPY ctf.xinetd /etc/xinetd.d/ctf
RUN chmod 644 /etc/xinetd.d/ctf

RUN touch /flag && chown ctf:ctf /flag && chmod 644 /flag

RUN echo '#!/bin/sh\nset -eu\nprintf "%s" "${GZCTF_FLAG:-flag{test}}" > /flag\nchmod 400 /flag\nexec xinetd -dontfork' > /start.sh \
    && chmod +x /start.sh

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD nc -z localhost 9999 || exit 1

EXPOSE 9999
USER ctf
CMD ["/start.sh"]
```

---

## 题面编写规范（statement.md）

必须包含：
1. 任务背景
2. 明确目标
3. Flag 格式 `flag{...}`
4. 附件说明（如有）
5. 环境启动说明（如有）
6. 必要的连接方式和端口
7. 允许/禁止事项

禁止出现：
- "自己试试""懂的都懂" 等模糊说明
- 错误的默认端口
- 已废弃的镜像地址
- 管理端路径或后台凭据
- Flag 答案或解题提示

---

## 本地测试流程（Builder 自测）

创建文件后，必须执行完整的 Docker 测试：

```bash
# 1. 构建
docker build -t challenge-test docker/

# 2. 启动
docker compose -f docker/docker-compose.test.yml up -d

# 3. 等待 healthy
sleep 10

# 4. 服务可达
curl -fsS http://127.0.0.1:18080/

# 5. 验证 Flag 可获取（用预期漏洞路径）
curl -s "http://127.0.0.1:18080/?name={{7*7}}" | grep "49"

# 6. 非 root 检查
docker compose -f docker/docker-compose.test.yml exec challenge id
# 应显示 uid=10001

# 7. 停止（应快速退出）
time docker compose -f docker/docker-compose.test.yml down
# 应在 10 秒内完成
```

---

## Reviewer 工作流

自测通过后，spawn ctf-reviewer agent 进行独立验证：

```
Agent(
  subagent_type: "general-purpose",
  description: "Review CTF challenge",
  prompt: "Review the challenge at {challenge_dir} against the
   隐域安全综合演练平台出题规范.
   1. Read every file, check against the full compliance checklist
   2. Run independent docker build + compose up + curl test + exploit test + stop
   3. Produce review.md with CRITICAL/HIGH/MEDIUM/LOW issues
   4. Verdict: PASS / FAIL
   This is review round {N} of 3."
)
```

### 修订循环

1. 读 `review.md`
2. 如果 FAIL：
   - CRITICAL → 必须修复
   - HIGH → 应该修复
   - MEDIUM → 建议修复
3. 修复后重新本地测试
4. 重新 spawn reviewer（最多 3 轮）
5. 第 3 轮仍有 CRITICAL → 标记 REJECTED，手动介入

### 修订记录

每次修订后创建 `review-round-{N}-fixes.md`：
```markdown
# Revision Round {N} Fixes
## CRITICAL fixes
- [C1] Fixed port binding: changed 127.0.0.1 → 0.0.0.0 in app.py:25

## HIGH fixes
- [H1] Removed flag hint from statement.md:12
```

---

## 附件题规范

### StaticAttachment
- 文件名只用安全字符（无控制字符、路径分隔符）
- 压缩包无密码（或题面明确给出）
- 附件 SHA256 写入 README.md
- 先在干净环境验证解压和打开
- 删除作者用户名、绝对路径、编辑器缓存、答案文件
- 大文件提前考虑平台和浏览器限制

### DynamicAttachment
- 每队不同文件 → 每个文件对应一个 Flag
- 文件与 Flag 映射表保留在内部（不发给选手）
- A 队附件中的 Flag 不能被 B 队提交

---

## AWDP 规范

### Checker 必须
- 读取环境变量：`AWDP_TARGET_HOST`, `AWDP_TARGET_PORT`, `AWDP_FLAG`
- 最后一行首词为：`OK` / `MUMBLE` / `DOWN` / `CORRUPT`
- 5-10 秒内完成
- 所有网络请求设 timeout
- 不输出完整 Flag

### Exp 必须
- 退出码 0（漏洞存在）/ 非0（漏洞已修复）
- 稳定可重复，不依赖竞态或外部服务

### 修补包
- `.tar.gz`，最大 16 MiB，最多 512 entry
- 根目录含 `update.sh`
- 禁止绝对路径、`..`、符号链接、硬链接

---

## 理论题规范

### 题库 JSON 格式
```json
{
  "questions": [
    {
      "type": "SingleChoice",
      "bankName": "题库名-单选",
      "title": "题干",
      "content": "补充说明",
      "options": ["选项A", "选项B", "选项C", "选项D"],
      "answerIndexes": [2]
    }
  ]
}
```

规则：
- `type`: SingleChoice / MultipleChoice / TrueFalse
- `options`: 至少 2 个；判断固定 ["正确", "错误"]
- `answerIndexes`: 从 0 开始，去重
- 单选/判断只有 1 个正确答案
- 多选完全一致才得分
- 每题分值 > 0

---

## 自测清单（交付前逐项确认）

### 通用
- [ ] 标题、分类、难度和分值正确
- [ ] 题面无答案泄漏
- [ ] 正确答案可稳定复现
- [ ] 错误答案不得分

### 附件（如有）
- [ ] 附件可下载
- [ ] SHA256 一致
- [ ] 无作者隐私和答案文件
- [ ] 大小在平台限制内

### Docker（如有）
- [ ] 镜像使用固定 tag
- [ ] 服务监听 0.0.0.0
- [ ] 内部端口正确
- [ ] 动态 Flag 读取 GZCTF_FLAG
- [ ] docker build 成功
- [ ] docker compose up + curl 可达
- [ ] 非 root 用户运行
- [ ] SIGTERM 后 10 秒内退出

### AWDP（如有）
- [ ] Checker 正常/异常状态均验证
- [ ] Exp 可稳定取得 Flag
- [ ] 修补包可应用
- [ ] 修补后 Checker 通过、Exp 失败

### 理论（如有）
- [ ] JSON 可解析
- [ ] 下标从 0 开始
- [ ] 单选题只有一个答案
- [ ] 每题分值 > 0
