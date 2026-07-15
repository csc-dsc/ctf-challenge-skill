# CTF Challenge Creator Skill

为 [隐域安全综合演练平台](https://github.com/GZTimeWalker/GZCTF) 创建符合规范的 CTF/AWDP/理论题目。

一个 Claude Code Skill，通过自然语言描述需求，自动生成完整题目交付包，Docker 端到端测试通过后才交付。

## 前置要求

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装并登录
- [Docker](https://docs.docker.com/get-docker/) 已安装并运行
- Git

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
├── README.md                  # 完整部署说明 + Checker/Exp 脚本
├── statement.md               # 选手题面
├── writeup.md                 # 标准解法（内部，不发给选手）
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

## v2: 平台 API 自动导入

v2 在 reviewer 通过后增加了自动导入阶段。设置凭据后，Skill 会自动将镜像推送到平台 Registry 并通过 Open API 创建题目。

### 配置凭据

三种方式（优先级从高到低）：

1. **CLI 参数**：在对话中告知 `--host platform.example.com --token gzctf_pat_xxx`
2. **环境变量**（推荐）：`GZCTF_HOST` + `GZCTF_TOKEN`
3. **配置文件**：`~/.gzctf/config.json` — `{"host": "...", "token": "..."}`

Token 需在平台 "账户 → API Token" 创建，scope 选择 `challenges:read/write/delete`、`operations:read`、`images:read/write/delete`，并授权对应比赛的 `game:{id}` 资源。

### 导入流程

```
Reviewer PASS
  → 检查凭据是否配置
  → 有凭据：
      → 方案A（Registry 可达）：docker tag + push + register-reference
      → 方案B（离线）：docker save + upload-archive
      → 轮询镜像 Ready
      → 生成 challenge-def.json
      → 调用 import API
      → 输出 challenge ID + URL
  → 无凭据：输出手动操作步骤（v1 行为）
```

### 镜像推送

- **内网可用**：Tag 并推送到 `10.24.0.28:5000/challenges/{name}:{version}`，然后 `register-reference`
- **离线/外网**：`docker save` 导出 tar，用 `upload-archive` 上传

详细 API 规范见 `prompts/_api.md`。

## 质量保证

- **Reviewer agent**: 独立运行 50+ 项规范检查 + Docker 测试
- **最多 3 轮修订**: CRITICAL 必须修复，HIGH 应该修复
- **validate-package.sh**: 提交前可手动运行 `bash scripts/validate-package.sh {题目目录}` 快速检查

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
│   └── validate-package.sh    # 包校验脚本
└── spec/
    └── 出题规范.md            # 完整规范参考文档
```

## License

MIT
