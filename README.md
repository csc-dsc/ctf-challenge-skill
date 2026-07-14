# CTF Challenge Creator Skill

为 [隐域安全综合演练平台](https://github.com/GZTimeWalker/GZCTF) 创建符合规范的 CTF 题目。

一个 Claude Code Skill，让你通过自然语言描述需求，自动生成完整的题目交付包，包含 Docker 环境、题面、解法、Flag 策略，并通过 Reviewer agent 确保质量。

## 一键安装

```bash
git clone https://github.com/csc-dsc/ctf-challenge-skill.git
cd ctf-challenge-skill
bash install.sh
```

Windows:
```cmd
git clone https://github.com/csc-dsc/ctf-challenge-skill.git
cd ctf-challenge-skill
install.bat
```

安装后重启 Claude Code 即可使用。

### 前置要求
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 已安装
- [Docker](https://docs.docker.com/get-docker/) 已安装并运行
- Git（用于克隆仓库）

## 支持的题型

| 题型 | 说明 |
|------|------|
| DynamicContainer | Web/PWN 动态独立容器环境 |
| StaticContainer | 固定 Web/PWN 环境、Windows 靶机 |
| StaticAttachment | Crypto/Reverse/取证压缩包附件 |
| DynamicAttachment | 每队独立附件 |
| AWDP | 攻防对抗服务（Checker + Exp + 修补） |
| Windows VM | Windows 虚拟机镜像 |
| Theory | 单选/多选/判断题 |

## 使用方法

直接在 Claude Code 中用自然语言描述：

```
创建一个 Web SSTI Easy 难度的题目，使用 Flask
```

```
出个 Crypto RSA 中等的静态附件题
```

```
做一个 AWDP 的 Flask SSTI 服务，Hard 难度
```

```
生成一套 Web 基础理论题库，10 道题
```

## 工作流

```
用户描述需求
  → Claude 分析并确定题型
  → 创建完整题目交付包
  → 本地 docker build + test
  → spawn Reviewer agent 独立验证
  → review.md 返回结果
  → 有问题就修复（最多 3 轮）
  → 通过后交付
```

## 交付物结构

每次出题生成标准目录：

```
challenge-name/
├── README.md                 # 题目说明、部署参数、验收步骤
├── statement.md              # 选手看到的题面
├── writeup.md                # 标准解法（内部资料）
├── flag-policy.md            # Flag 读取方式和规则
├── attachments/              # 对外附件
├── source/                   # 题目源码
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.test.yml
│   └── healthcheck.sh
├── awdp/                     # 仅 AWDP 题型
└── vm/                       # 仅 Windows VM 题型
```

## 质量保证

- **Reviewer agent**: 独立运行 50+ 项规范检查
- **Docker 端到端测试**: docker build → compose up → curl → exploit → stop
- **最多 3 轮修订**: CRITICAL 问题必须修复才能通过
- **规范合规**: 严格遵循隐域安全综合演练平台出题规范

## 文件说明

```
ctf-challenge-skill/
├── SKILL.md                   # 主 Skill 定义
├── agents/
│   └── ctf-reviewer.md        # Reviewer agent
├── prompts/                   # 各题型专属 prompt
│   ├── _shared.md             # 通用规则
│   ├── dynamic-container.md
│   ├── static-container.md
│   ├── static-attachment.md
│   ├── dynamic-attachment.md
│   ├── awdp.md
│   ├── windows-vm.md
│   └── theory.md
├── templates/                 # 模板文件
│   ├── challenge/             # 交付包目录模板
│   └── docker-variants/       # 各语言 Dockerfile 模板
├── spec/
│   └── 出题规范.md            # 完整规范文档
├── install.sh / install.bat   # 安装脚本
└── README.md                  # 本文件
```

## License

MIT
