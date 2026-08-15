---
name: ctf-challenge-creator
description: >
  为隐域安全综合演练平台创建高质量 CTF/AWDP/理论 题目。
  支持 StaticAttachment, StaticContainer, DynamicAttachment, DynamicContainer,
  AWDP, Windows VM, Theory 七种题型。
  支持批量题目计划、平台 Open API 导入和 Exercise 题目池收录。
  采用 Reviewer agent 做质量门禁，最多 3 轮修订，端到端 Docker 测试通过才交付。
---

# CTF Challenge Creator

为隐域安全综合演练平台创建高质量题目。你作为 planner+builder，负责生成题目文件；
ctf-reviewer agent 作为质量门禁，负责规范检查和 Docker 端到端测试。

## 工作流程

```
用户描述题目需求
  → 你分析需求，确定题型
  → 批量需求先建立 batch-manifest.json，再逐题创建完整交付包
  → 你创建完整题目交付包（所有文件）
  → 你本地 docker build + test（容器题）
  → 你 spawn ctf-reviewer agent（独立验证）
  → review.md 返回结果
  → 如 CRITICAL/HIGH 问题：修复 → 重新 spawn reviewer（最多 3 轮）
  → 如 PASS：导出镜像、运行 solve.py，并交付到本次用户指定的题目根目录
```

> **API 自动导入**：`scripts/ctf_client.py` 支持当前 Open API v1 的公共 Exercise、培训课程、理论题库/试卷、战队、比赛题目和 AWDP 导入及 operation 轮询。仅在 reviewer PASS 后导入；AWDP 成功后会自动收录到题目池。

每次导入前必须先要求**本次用户**显式提供平台地址 `GZCTF_HOST`。平台地址不得写死在
Skill、题目包、脚本默认值或示例中；也不得从历史上下文、SSH 主机、题目文件或其他环境信息
猜测。用户未提供本次地址时停止导入。地址确认后再检查 Token。AI 可以指导用户在该平台的
API Token 页面创建“独立、短期、最小权限” Token，但不得代用户生成、索取、回显或保存 Token。
用户应通过 `GZCTF_TOKEN` 或其本地受控配置提供它，然后 AI 才能运行 CLI。

容器题还必须要求本次用户提供或确认所有调度节点可访问的镜像 Registry 地址。不得假定某个
内网 Registry 存在、可达或允许推送；Registry 不可达时使用平台的 Docker archive 上传流程。

### 导入前权限声明（强制）

用户提出题目需求后、生成 Token 前，必须先根据目标资源和题型向用户列出本次任务所需的
最小权限，说明每项权限对应的动作，并明确是一个 Token 还是两个阶段的独立 Token。不得只说
“需要管理员权限”，不得先索取 Token 再补充权限，也不得使用权限范围大于本次操作所需的 Token。

| 本次目标 | 题型/动作 | 最小 scope | Resource grant | Token 阶段 |
|---|---|---|---|---|
| 附件资产 | 任意题目附件 | `assets:write`（读取/删除分别为 `assets:read` / `assets:delete`） | 所有者或 `asset:{sha256}` / `asset:*` | `asset upload` 后使用返回的 `remoteUrl` |
| 公共练习 | StaticAttachment / DynamicAttachment | `assets:write`, `exercises:read`, `exercises:write`, `operations:read` | `exercise:*` | 先上传附件，再练习导入 |
| 公共练习 | StaticContainer / DynamicContainer / Web 练习题 | `images:write`, `operations:read` | 无额外资源授权 | 镜像发布 |
| 公共练习 | StaticContainer / DynamicContainer / Web 练习题 | `exercises:read`, `exercises:write`, `operations:read` | `exercise:*` | 练习导入 |
| 培训课程 | 课程、章节、实验导入 | `training:write`, `operations:read` | `training-course:*` | 课程导入 |
| 培训课程容器实验 | 镜像上传/登记 | `images:write`, `operations:read` | 无额外资源授权 | 镜像发布 |
| 比赛题目 / AWDP | 题目、服务导入 | `challenges:read`, `challenges:write`, `operations:read` | `game:{gameId}` | 比赛导入 |
| 比赛/AWDP 容器 | 镜像上传/登记 | `images:write`, `operations:read` | 无额外资源授权 | 镜像发布 |
| 理论题库 | 题库题目导入 | `theory:write`, `operations:read` | `theory-bank:*` | 题库导入 |
| 理论试卷 | 比赛试卷编排 | `theory:write`, `operations:read` | `game:{gameId}` | 试卷导入 |
| 战队 | 战队导入 | `teams:write`, `operations:read` | `team:*` | 战队导入 |

删除已有资源时，只额外声明对应的删除 scope：公共练习为 `exercises:delete`，镜像为
`images:delete`，比赛题目为 `challenges:delete`。读取已有资源时才补充相应 `*:read`，不为
未执行的操作预先扩大权限。

对“Web 练习题”这类容器题，必须先向用户说明：需要一个镜像发布 Token
（`images:write`、`operations:read`）和一个练习导入 Token（`exercises:read`、
`exercises:write`、`operations:read`、`exercise:*`）；两个 Token 可以由同一教师创建，但应
独立、短期且不共享。仅当用户明确选择使用同一个 Token 且该 Token 精确包含这两阶段权限时，
才可合并使用。

### 独立练习题导入

不要把题目池收录理解为必须从比赛或培训复制。对没有来源资源的题目，附件题生成 Exercise
导入包并调用 `exercise import` 即可进入练习题池。Reverse、Crypto、Forensics 等附件题
只要有附件、有效静态 `flags` 和通过 Reviewer 的 `solve.py`，同样直接收录；容器题改用
`exercise create`，并必须提供 Ready 镜像/模板、运行端口和 `flagTemplate`（动态题）或
`flags`（静态题）。当前
`/exercises/import` 只用于附件/无运行时字段的批量导入；容器练习必须在镜像 Ready 后逐题调用
`exercise create`，并将稳定 `externalId` 保留在题目包和导入结果映射中。

生成每个 Exercise 项时同步填写 `externalId`、`title`、`content`、`category`、
`difficulty`、`tags`、`type` 及题型所需的 `attachment`/`containerImage`/`imageTemplateId`
和 Flag 字段。导入成功后记录 Exercise resource ID，不伪造比赛或培训来源。

### 容器题导入闭环

固定顺序：本地 Docker E2E/solver → `asset upload` → 镜像上传并轮询 Ready → `exercise create` →
operation 和 `exercise get` 回读。回读核对镜像、附件 URL、Flag 模板、端口、题型和
`creatorUserName`。导入完成后，使用 Teacher/Admin 会话在 `/admin/exercises` 核对题目列表
“提交”和“操作”之间的“出题人”列，并在编辑抽屉的“题目内容”上方核对同一账户名；镜像在
`/admin/images` 的“登记时间”后核对“上传者”。账户名必须是本次 Token 所属操作者，不能由
CLI 请求体伪造。历史资源可能显示“未记录”，只能由平台管理员按明确范围补录，不能在导入脚本
中批量改写。PWN 等原始 TCP 题必须用 `nc` 或 solver 验收；端口可达但无首屏时发送协议首行后
再判定，不能仅凭空白终端断言失败。失败清理按练习、镜像、附件逆序执行；被引用附件的 409 是保护，
不得强删。

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

确定题型后，**你必须 Read 对应的 prompt 文件**，它包含该题型的详细要求、常见陷阱和难度设计指南。

---

## 题目质量与难度设计原则（CRITICAL）

### 质量分层

| 层级 | 标准 | 说明 |
|------|------|------|
| **基础合规** | Docker 规则（C1-C10）、文件规范、Flag 格式 | 违反直接打回 |
| **可解性** | Writeup 步骤可复现、Flag 可稳定获取 | Reviewer 独立验证 |
| **难度匹配** | 实际难度与声明的 Easy/Medium/Hard 一致 | 见下方难度标准 |
| **防作弊** | 无意外解法、无信息泄露、无竞态条件 | 见防作弊章节 |
| **教学价值** | 考点明确、选手有收获、不靠猜测 | 高质量题目标志 |

### 难度标准

| 难度 | 预期解题时间 | 步骤数 | 技术要求 | 示例 |
|------|-------------|--------|---------|------|
| **Easy** | 15-30 分钟 | 1-2 步 | 单一基础技术 | SQL 注入（无 WAF）、简单 RCE、凯撒密码 |
| **Medium** | 30-90 分钟 | 2-4 步 | 组合技术或绕过基础防护 | SSTI + 沙箱逃逸、格式化字符串 + ROP |
| **Hard** | 1-4 小时 | 4+ 步 | 多阶段利用、自定义利用链 | 内核利用、VM 逃逸、多层密码学 |

**难度自检**：
- Easy: 一个熟悉该方向的 CTF 选手应能在 30 分钟内独立完成
- Medium: 需要组合多个知识点，但不涉及 0day 或偏门技术
- Hard: 需要深度理解底层机制，多阶段利用链

### 考点设计原则

1. **一个题目一个核心考点**：不要堆砌无关技术
2. **考点应有现实映射**：最好是真实漏洞的简化版，不是纯脑洞
3. **线索清晰但不明显**：选手知道目标但不知路径
4. **避免纯猜测**：Flag 获取不依赖暴力枚举、非理性试错
5. **有学习价值**：做完后选手能带走一个新知识点

---

## 防作弊与题目完整性（CRITICAL）

### 解法唯一性

1. **预期解法是唯一或最优路径**：不应存在比预期解法简单得多的非预期解法
2. **自测非预期解法**：构建完成后，从以下角度尝试绕过：
   - 能否直接读取 Flag 文件而不触发漏洞？
   - 能否通过报错信息推断 Flag？
   - 能否通过时序侧信道猜测 Flag？
   - 能否绕过认证直接访问功能？

### 信息泄露防护

| 泄露源 | 防护措施 |
|--------|---------|
| Docker 镜像 layer | Flag 不在 Dockerfile 中 `ENV`/`COPY`；用启动脚本从环境变量注入 |
| 报错信息 | 生产模式关闭 debug；不暴露绝对路径和源码片段 |
| 题面 | 不暗示解法、不泄露 Flag 格式特例 |
| Writeup（内部） | 明确标注"内部资料，不发给选手" |
| 附件元数据 | 删除作者名、绝对路径、编辑器缓存 |

### 动态容器专用
- Flag 通过 `GZCTF_FLAG` 环境变量注入
- 每个实例独立 Flag
- Flag 不跨实例复用

---

## 题目交付包目录（必须严格遵守）

```
challenge-name/
├── challenge.yaml            # 可机读元数据：类型、资源、考点、导入字段
├── README.md                 # 人工阅读的题目说明、部署参数、验收步骤
├── statement.md              # 选手看到的题面
├── writeup.md                # 标准解法（内部资料，不发给选手）
├── solve.py                  # 可执行标准解法；成功时打印 Flag 并以 0 退出
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

`challenge.yaml`、`solve.py` 与 `README.md` 必须相互一致。`challenge.yaml` 用于
批量审计和导入前复核，不得写入 Token、真实生产 Flag、平台密码或内部地址。

## 批量出题

当用户要求多题、专题或题库时，先在输出根目录建立 `batch-manifest.json`，再逐题执行
完整 Builder/Reviewer 流程；不得只生成题面或以未测试样例凑数量。

```json
{
  "batchId": "web-foundation-20260812",
  "target": "exercise",
  "items": [
    {"id": "web-ssti-easy-v1", "type": "DynamicContainer", "category": "Web", "difficulty": "Easy", "knowledge": ["Server-side Template Injection"]}
  ]
}
```

每个 `id` 对应一个题目目录。完成时写 `batch-result.json`，记录每题的 reviewer verdict、
镜像 digest/附件 SHA256、导入 operation ID 与平台 resource ID；绝不记录 Token 或 Flag。
批次失败时只重试失败项，并沿用原 Idempotency-Key 查询 operation，不重复创建资源。

README.md 必须包含：
```markdown
# 题目名称
- 赛制：CTF / AWDP / 理论 / 培训
- 分类：Web / Pwn / Forensics / IR 等
- 难度：Easy / Medium / Hard
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

## 输出目录

每次任务开始前必须要求用户提供题目输出根目录。不得复用先前任务的目录，也不得假定
`D:\TASK` 或任何其他路径存在。每道题在该根目录下创建独立目录：

```
<user-provided-output-root>\<challenge-name>\
```

批量任务的每个 `id` 对应一个独立目录；不要把多个题目混放在同一目录。

## 命名规范

- 题目名：`分类-知识点-难度-版本`，如 `Web-SSTI-Medium-v1`
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

创建文件后，必须执行完整的端到端测试：

### 通用测试（所有 Docker 题）

```bash
# 1. 构建
docker build -t challenge-test docker/

# 2. 启动
docker compose -f docker/docker-compose.test.yml up -d

# 3. 等待 healthy
sleep 10

# 4. 非 root 检查
docker compose -f docker/docker-compose.test.yml exec challenge id
# 应显示 uid=10001

# 5. 停止（应快速退出，10 秒内）
time docker compose -f docker/docker-compose.test.yml down

# 6. 导出镜像 tar 包（平台上传用）
docker save <image-name> -o <challenge-name>.tar
```

### AWDP 额外测试（Checker → Exp → Patch → 验证）

```bash
# 1-3 同上（build, up, wait healthy）

# 4. 运行 Checker
AWDP_TARGET_HOST=127.0.0.1 AWDP_TARGET_PORT=<host_port> AWDP_FLAG=flag{test} python checker.py
# 期望输出 OK，exit 0

# 5. 运行 Exp
AWDP_TARGET_HOST=127.0.0.1 AWDP_TARGET_PORT=<host_port> AWDP_FLAG=flag{test} python exp.py
# 期望 exit 0（漏洞存在，flag 拿到）

# 6. 制作修补包并验证
# 将修补包打包为 .tgz → docker cp 到容器 → 执行 update.sh
# 再次运行 Checker → 应仍输出 OK（exit 0）
# 再次运行 Exp → 应 exit 非 0（漏洞已修复）

# 7. down + docker save
```

### 关键验证点

| 检查项 | 方法 | 通过标准 |
|--------|------|----------|
| 非 root 用户 | `id` | uid=10001 |
| SIGTERM | `time docker compose down` | < 10 秒 |
| Checker 正常 | 设好环境变量运行 | 输出 OK, exit 0 |
| Exp 可用 | 设好环境变量运行 | exit 0, 拿到 flag |
| 修补后 Checker | 应用补丁后运行 | 仍输出 OK, exit 0 |
| 修补后 Exp | 应用补丁后运行 | exit 非 0, 漏洞已修复 |
| 镜像 tar | `docker save` | 文件在题目根目录 |
| README 完整性 | 读 README.md | 包含 Checker/Exp 完整脚本 + 暴露端口 + 平台配置表 |

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
- [ ] 无非预期解法（参见防作弊章节）

### 附件（如有）
- [ ] 附件可下载
- [ ] SHA256 一致
- [ ] 无作者隐私和答案文件
- [ ] 大小在平台限制内

### Docker（如有）
- [ ] 本地镜像使用可追溯 tag；平台归档引用由平台生成
- [ ] 服务监听 0.0.0.0
- [ ] 内部端口正确
- [ ] 动态 Flag 读取 GZCTF_FLAG
- [ ] docker build 成功
- [ ] docker compose up + curl 可达
- [ ] 非 root 用户运行
- [ ] SIGTERM 后 10 秒内退出
- [ ] `docker save` 镜像 tar 包已导出到题目根目录

### AWDP（如有）
- [ ] Checker 正常/异常状态均验证
- [ ] Exp 可稳定取得 Flag
- [ ] 修补包可应用
- [ ] 修补后 Checker 通过、Exp 失败
- [ ] `docker save` 镜像 tar 包已导出
- [ ] README 包含完整 Checker 和 Exp 脚本代码
- [ ] README 标注暴露端口（容器内部端口，不是宿主机映射端口）
- [ ] README 包含平台配置参数表（分数、轮次、攻击次数等）

### 理论（如有）
- [ ] JSON 可解析
- [ ] 下标从 0 开始
- [ ] 单选题只有一个答案
- [ ] 每题分值 > 0

---

## Platform API Import

`scripts/ctf_client.py` 已实现完整的 Open API v1 客户端（零外部依赖，Python stdlib only）。
API 集成协议见 `prompts/_api.md`。公共练习、培训、理论、战队和比赛（含 AWDP）分别使用独立路径与资源授权，禁止把比赛 Token 当作 Exercise Token。

Token 安全规则（使用 API 时必须遵守）：
1. Token **只能**通过环境变量 `GZCTF_TOKEN` 或 `~/.gzctf/config.json` 传入
2. **绝对禁止**将 Token 写入：Git 仓库、skill 文件、日志、`import-result.json`、shell 历史
3. 所有含 Token 的命令必须通过环境变量传递，禁止在命令行中明文写出 Token
4. 每个 AI、CI 或操作者使用独立 Token；平台审计通过 token ID 和创建者用户 ID 追溯上传责任，
   并在练习“出题人”和镜像“上传者”管理列中可视化核对
5. Exercise Token 至少需要 `exercises:write`、`exercises:read`、`operations:read`，资源授权为 `exercise:*`
6. 培训/理论使用 `training:write`/`theory:write`；战队使用仅管理员可签发的 `teams:write`
7. 比赛和 AWDP 使用 `challenges:read/write/delete` + `game:{gameId}`；AWDP 导入成功会自动深复制到题目池
8. 配置文件权限应设为 600：`chmod 600 ~/.gzctf/config.json`
9. 仅把可独立运行且可验证 Flag 的资源交给自动收录：比赛/培训题需要容器类型、镜像或模板、Flag 或 `flagTemplate`；AWDP 还需要匹配的 Ready Docker 模板和非空 `flagTemplate`
