# CTF Challenge Creator Skill

为隐域安全综合演练平台创建、验证、批量导入和运营 CTF/AWDP/理论题目。

这是一个可由 Codex 或 Claude Code 使用的本地 Skill。它将自然语言需求变成完整题目交付包，
通过 Docker 和独立 Reviewer 验收后，可选择用 Open API 导入比赛、AWDP、培训、理论或公共练习。

## 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装并登录
- [Docker](https://docs.docker.com/get-docker/) 已安装并运行
- Git

导入平台时还需要由平台账户创建的 API Token。SSH 密码、数据库口令和平台登录密码不是 API
Token，不能互相替代。历史题目池回填是例外：它只能由已登录的 Teacher+ 浏览器会话触发。

导入前的交互顺序固定为：

1. 用户提供明确的平台地址，例如 `http://10.24.0.27:8080`；未提供时不猜测、不导入。
2. AI 提示用户在该平台的 API Token 页面创建独立、短期、最小权限 Token。
3. 用户通过 `GZCTF_TOKEN` 环境变量或 `~/.gzctf/config.json` 提供 Token；AI 不生成、不索取、不回显、不保存 Token。
4. Reviewer 通过后才运行导入，并保存 operation/resource ID（不保存凭据或 Flag）。

## 安装

```bash
git clone https://github.com/csc-dsc/ctf-challenge-skill.git
cd ctf-challenge-skill
bash install.sh        # Linux/Mac
# install.bat          # Windows
```

安装后**重启 Claude Code**（退出终端重新打开），Skill 即生效。

验证安装：在 Claude Code 中输入 `/ctf-challenge-creator`，如果显示 Skill 加载成功即可。

## 支持的题型

| 题型 | 关键词 | 输出目录 |
|------|--------|---------|
| DynamicContainer | Web/PWN 动态容器 | `D:\TASK\dynamic-container\` |
| StaticContainer | 固定靶机 | `D:\TASK\static-container\` |
| StaticAttachment | Crypto/Reverse/取证附件 | `D:\TASK\static-attachment\` |
| DynamicAttachment | 每队独立附件 | `D:\TASK\dynamic-attachment\` |
| **AWDP** | 攻防对抗、Checker、Exp、修补 | `D:\TASK\awdp\` |
| Windows VM | Windows 虚拟机 | `D:\TASK\windows-vm\` |
| Theory | 单选/多选/判断 | `D:\TASK\theory\` |

## 使用方法

在 Claude Code 中用自然语言描述需求即可：

```
创建一个 Web SSTI Easy 难度的动态容器题，使用 Flask
```

```
做个 PWN 栈溢出入门题，64 位，no canary，AWDP 赛制
```

```
生成一套 Web 安全理论题库，10 道单选
```

Skill 会自动：
1. 分析需求，确定题型
2. 创建全套文件（源码、Dockerfile、题面、解法、Checker/Exp）
3. 本地 `docker build` + 启动
4. 运行 Checker、Exp、修补验证
5. 导出镜像 tar 包
6. 输出到对应目录

### 批量专题或题库

批量任务先建立 `batch-manifest.json`，每题仍必须独立经过构建、解法复现和 Reviewer 门禁。

```json
{
  "batchId": "web-foundation-20260812",
  "target": "exercise",
  "items": [
    {"id":"web-ssti-easy-v1","type":"DynamicContainer","category":"Web","difficulty":"Easy","knowledge":["Server-side Template Injection"]},
    {"id":"web-idor-easy-v1","type":"StaticAttachment","category":"Web","difficulty":"Easy","knowledge":["IDOR"]}
  ]
}
```

结束时生成不含凭据或 Flag 的 `batch-result.json`，包括 reviewer 判定、镜像 digest 或附件
SHA256、异步 operation ID 和平台资源 ID。仅重试失败项；未知写入结果应查询既有 operation，
不要用新 Idempotency-Key 盲目重复导入。

## 工作流

```
用户描述需求
  → Claude 分析并确定题型
  → 创建完整题目交付包（源码、docker/、awdp/、README 等）
  → 本地 docker build + compose up → healthy
  → Checker 测试 → OK
  → Exp 测试 → exit 0（漏洞存在）
  → 补丁测试 → Checker 仍 OK，Exp exit 非0
  → docker save 导出镜像 tar
  → spawn Reviewer agent 独立验证
  → 有问题修复（最多 3 轮），通过后交付
```

## 交付物结构

```
D:\TASK\{题型}\{题目名}      # 如 D:\TASK\awdp\awdp-pwn-bof-easy-v1
├── {题目名}.tar               # Docker 镜像 tar，上传平台用
├── challenge.yaml              # 可机读元数据与导入前复核依据
├── README.md                  # 完整部署说明 + Checker/Exp 脚本
├── statement.md               # 选手题面
├── writeup.md                 # 标准解法（内部，不发给选手）
├── solve.py                    # 内部验收解题脚本，成功时打印 Flag 并退出 0
├── flag-policy.md             # Flag 规则
├── attachments/               # 对外附件
├── source/                    # 服务源码
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   ├── start.sh
│   └── healthcheck.sh
└── awdp/                      # 仅 AWDP
    ├── checker.py
    ├── exp.py
    ├── {题目名}-fix.tgz       # 修补包
    └── patch-example/
```

`challenge.yaml` 的分类、难度、类型、端口、资源、网络和 Flag 模式必须与 README、题面和
运行环境一致。`solve.py` 必须从 `SOLVE_TARGET` 接收部署入口，不能硬编码生产 Flag。

## AWDP 题目完整流程

以 PWN Buffer Overflow 为例：

### 1. 出题
```
创建一个 AWDP PWN 栈溢出 Easy 题目，64 位 xinetd 服务
```

### 2. 本地测试（Skill 自动执行）

```
docker build → docker compose up → healthy
Checker: OK (exit 0)
Exp: 成功获取 flag (exit 0)
补丁: Checker 仍 OK，Exp 失败 (exit 1)
SIGTERM: < 1 秒退出
docker save → 镜像 tar
```

### 3. 提交到平台

打开 `README.md`，依次复制：
1. **平台配置表** → 填写服务名称、暴露端口（如 9999）
2. **Checker 脚本** → 直接粘贴到平台 Checker 框
3. **Exp 脚本** → 直接粘贴到平台 Exp 框
4. **修补包 `.tgz`** → 上传到平台

### 4. 关键避坑

| 错误 | 后果 |
|------|------|
| 暴露端口填 80（Web 默认值） | PWN 服务端口不对连不上 |
| Checker/Exp 用 Web HTTP 模板 | PWN 没有 HTTP 端点 |
| 忘导出镜像 tar | 平台没镜像可用 |
| README 没脚本 | 提交者不知道填什么 |

## 平台 API 自动导入（Open API v1）

reviewer 通过后，Skill 可直接导入公共 Exercise，也可导入培训课程、理论题库/试卷、战队、比赛题目和 AWDP；镜像注册仍使用 images API。

### 直接导入练习题（不依赖比赛或培训）

`exercise import` 是独立的一级导入流程，不要求题目先存在于比赛或培训课程中。Web、Pwn、Reverse、Crypto、Misc、Forensics 等题型都可以直接进入练习题池：

- `StaticAttachment`（例如 Reverse 二进制、流量包、压缩包）提供附件 URL/SHA256 和一个或多个静态 `flags`；Reviewer 验证 `solve.py` 能得到 Flag 后直接收录。
- `DynamicAttachment` 提供附件和动态 Flag 规则；`StaticContainer`/`DynamicContainer` 提供 Ready 镜像或模板、端口和 Flag/`flagTemplate`。
- 每项必须携带 `category`、`difficulty`、`tags`、题面 `content`、稳定 `externalId` 以及匹配题型的附件/镜像/Flag 字段。Skill 生成题目包时自动填写这些元数据。
- 直接导入成功后资源来源为 `Exercise`，与比赛/培训/AWDP 深复制到题库的来源收录流程相互独立。

### 配置凭据

两种方式（优先级从高到低）：

1. **环境变量**（推荐）：`GZCTF_HOST` + `GZCTF_TOKEN`
2. **配置文件**：`~/.gzctf/config.json` — `{"host": "...", "token": "..."}`，权限设为 600

Token 需在平台 "账户 → API Token" 创建。公共练习使用 `exercises:*` + `exercise:*`；培训使用 `training:write` + `training-course:*`；理论题库使用 `theory:write` + `theory-bank:*`；理论试卷使用 `theory:write` + `game:{id}`；战队使用管理员 Token 的 `teams:write` + `team:*`；比赛和 AWDP 使用 `challenges:read/write/delete` + `game:{id}`。异步轮询增加 `operations:read`。每个 Token 对应明确创建者，不得共享。AWDP 导入成功后会自动深复制到题目池。

### 练习池自动收录与历史回填

新建或更新的比赛、培训和 AWDP 资源只有在可独立运行、可验证 Flag 时才会进入公共练习池：

- 比赛/培训题：必须是容器题，拥有 `containerImage` 或 `imageTemplateId`，并且有 Flag 或 `flagTemplate`。
- AWDP：必须有 `flagTemplate`，且 `imageName` 必须对应平台中状态为 Ready 的 Docker 镜像模板。
- 理论题、纯附件题、没有镜像或 Flag 的容器题会被标记为不符合资格，不会伪造运行环境后收录。

平台升级前的历史资源不会自动批量写入。Teacher+ 用户应在已登录平台会话中执行
`POST /api/Exercise/pool/backfill`；响应中的 `ineligible` 表示上述前置条件缺失，`failed`
才表示处理失败。这个维护接口不是 Open API，不能用 `ctf_client.py`、API Token、SSH
密码或直接数据库写入替代。详细字段与验收步骤见 `prompts/_api.md`。

回填后在 `/practice` 按来源和分类核查题目；对容器题启动实例并确认页面显示访问入口、运行状态
和剩余时间。没有入口时先检查实例状态、调度日志、节点可达性和端口映射，不要直接改数据库。

### 导入流程

```
Reviewer PASS
  → 检查凭据是否配置
  → 有凭据：
      → 方案A（Registry 可达）：docker tag + push + register-reference
      → 方案B（离线）：docker save + upload-archive
      → 轮询镜像 Ready
      → 生成 exercise-import.json
      → 调用 POST /api/open/v1/exercises/import
      → 轮询 /api/open/v1/operations/{id}
      → 输出 externalId -> exerciseId 映射
  → 无凭据：输出手动操作步骤（v1 行为）
```

### 镜像推送

- **内网可用**：Tag 并推送到 `10.24.0.28:5000/challenges/{name}:{version}`，然后 `register-reference`
- **离线/外网**：`docker save` 导出 tar，用 `upload-archive` 上传

详细 API 规范见 `prompts/_api.md`。

其他资源命令：

```text
python scripts/ctf_client.py training import-courses --file course-import.json
python scripts/ctf_client.py awdp import --game-id 42 --file awdp-service.json
python scripts/ctf_client.py theory import-questions --file theory-bank.json
python scripts/ctf_client.py theory import-paper --game-id 42 --file theory-paper.json
python scripts/ctf_client.py team import --file teams.json
```

## 质量保证

- **Reviewer agent**: 独立运行 50+ 项规范检查 + Docker 测试
- **最多 3 轮修订**: CRITICAL 必须修复，HIGH 应该修复
- **validate-package.sh**: 提交前可手动运行 `bash scripts/validate-package.sh {题目目录}` 快速检查
- **结构化证据**：每个新题使用 `challenge.yaml` 与 `solve.py`；批量任务再保留 manifest/result
- **导入后验收**：operation 成功不等于可用。对至少一个容器题在真实权限会话中创建实例、确认访问入口并用 `solve.py` 获取 Flag

## 平台导入验收

```bash
# 1. 先检查本地包；容器题还需 Docker build/compose/solve 自测
bash scripts/validate-package.sh D:/TASK/dynamic-container/web-ssti-easy-v1
python scripts/ctf_client.py --help

# 2. 镜像 Ready 后导入。Token 仅通过环境变量或 ~/.gzctf/config.json 提供。
python scripts/ctf_client.py exercise import --file exercise-import.json
python scripts/ctf_client.py operation wait --operation-id <operation-id>

# 3. 在已登录的浏览器会话中打开 /practice，创建实例并确认入口；
#    令 SOLVE_TARGET=<displayed-url> 后运行内部 solve.py 验证 Flag。
```

CLI 在缺少平台地址时会明确报错并给出 `GZCTF_HOST` 示例；地址存在但缺少 Token 时会提示
创建最小权限 Token。提交比赛题目使用 `challenge import` 或 `challenge import-batch`，
提交公共练习使用 `exercise import`；两者均要求对应 scope 和资源授权。

外部 API 写入全部使用 `Idempotency-Key`，客户端会生成默认值。对于可审计的批量/CI 工作流，
显式传入稳定 key，并把 operation ID 保存到不含凭据的 `batch-result.json`。

## 仓库结构

```
ctf-challenge-skill/
├── SKILL.md                   # Skill 主定义（Claude Code 入口）
├── README.md                  # 本文件
├── install.sh / install.bat   # 安装脚本
├── agents/
│   └── ctf-reviewer.md        # Reviewer agent 定义
├── prompts/
│   ├── _shared.md             # 通用规范（跨平台、Flag、命名）
│   ├── awdp.md                # AWDP 题型完整指南
│   ├── dynamic-container.md
│   ├── static-container.md
│   ├── static-attachment.md
│   ├── dynamic-attachment.md
│   ├── windows-vm.md
│   └── theory.md
├── templates/
│   ├── challenge/             # 交付包目录模板
│   └── docker-variants/       # 各语言 Dockerfile（Python/Node/PHP/xinetd）
├── scripts/
│   ├── validate-package.sh    # 包校验脚本
│   └── ctf_client.py          # Open API v1 CLI（题目、AWDP、练习、operation）
└── spec/
    └── 出题规范.md            # 完整规范参考文档
```

## License

MIT
