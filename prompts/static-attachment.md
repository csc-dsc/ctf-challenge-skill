# StaticAttachment 题型出题指南

## 题型定义

StaticAttachment：纯附件题，无在线环境。所有队伍拿到的附件相同，Flag 也相同。

适用：Crypto、Reverse、Forensics（流量分析、内存取证、磁盘取证）、Misc。

## 平台配置字段

| 字段 | 填写示例 |
|------|----------|
| 标题 | `流量分析-登录凭据` |
| 分类 | `Forensics` |
| 类型 | `StaticAttachment` |
| 环境 | `None` |
| 初始分 | `500` |
| 最低分率 | `0.2` |
| 题面 | `下载附件并分析 HTTP 登录流量。` |
| 附件 | `traffic.pcapng` |
| Flag | `flag{http_basic_auth}` |

## 目录结构

```
category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/              # 原始素材（构建附件的源文件、脚本）
│   ├── generate.py      # 附件生成脚本（如适用）
│   └── ...
└── attachments/         # 选手下载的文件
    ├── challenge.zip
    └── challenge.zip.sha256
```

不需要 `docker/` 目录（除非有在线辅助环境）。

## 附件制作规范

### 文件要求
1. 文件名只用安全字符（字母、数字、下划线、短横线、点），避免控制字符和路径分隔符
2. 压缩包格式优先使用 `.zip`（跨平台兼容），无密码（或题面明确给出）
3. 计算并记录 SHA256，写入 `README.md` 和 `.sha256` 文件
4. 先在干净环境解压测试，确认可正常打开

### 内容清理（必须逐项确认）
- [ ] 删除作者用户名（`/home/xxx`, `C:\Users\xxx`）
- [ ] 删除绝对路径
- [ ] 删除编辑器缓存（`.DS_Store`, `Thumbs.db`, `~` 备份文件）
- [ ] 删除答案/Flag 文件（不要在附件里包含 Flag）
- [ ] 删除 `.git` 目录
- [ ] 清理图片/PDF 元数据（Exif 中可能含作者信息）
- [ ] 大文件提前验证平台 + Nginx + 浏览器下载限制

### 附件内容设计原则
- 附件本身包含所有解题所需数据
- Flag 是从附件中分析/解密得出的结果（不应直接明文出现）
- 提供足够的线索让选手知道从哪入手
- 不要故意制造歧义（如文件名误导）

## 按分类的设计要点

### Crypto
- 提供密文（可能在附件中，可能在题面中）
- 提供加密算法线索（可加密钥文件、源码片段等）
- Flag 是解密后的明文
- 附件：密文文件、加密脚本、公钥/私钥文件
- 注意：不要用真实生产环境的密钥

### Reverse
- 提供编译好的二进制文件
- 可选：提供部分源码让选手对照
- Flag 隐藏在二进制中（字符串、算法生成、反调试后显示等）
- 附件：ELF/PE 二进制
- source/ 放编译脚本和原始源码

### Forensics - 流量分析
- 提供 `.pcapng` 或 `.pcap` 文件
- 流量中包含关键信息（登录凭据、传输文件、DNS 查询等）
- 清理 pcap 中的个人 IP 和 MAC 地址
- Flag 从流量中提取

### Forensics - 内存取证
- 提供内存镜像（`.raw`, `.mem`, `.vmem`）
- 用 Volatility 验证 Flag 可提取
- Flag 放在进程内存、剪贴板、命令行历史等位置

### Forensics - 磁盘取证
- 提供磁盘镜像（`.E01`, `.dd`, `.img`）或其压缩包
- 删除的文件、日志、注册表等包含关键信息
- 确认镜像不包含出题人的个人文件

### Misc
- 编码/隐写/逻辑题等
- 附件格式多样

## writeup.md 必须说明

1. 使用的工具和版本
2. 完整分析步骤（从打开附件到获得 Flag）
3. 关键截图或命令输出
4. Flag 值和获取方式

## 自检步骤

1. 在干净环境（新虚拟机或 Docker 容器）中下载附件
2. 解压/打开，确认文件完整
3. 按 writeup.md 步骤操作，确认能获得 Flag
4. 尝试用错误 Flag 提交，确认不会意外得分
5. 计算 `sha256sum attachments/*` 并记录
6. 搜索附件内容中是否有个人用户名、路径等痕迹

## API 导入字段映射（v2）

Reviewer 通过后，如用户配置了平台凭据，按以下映射构造 `challenge-def.json`：

| README 字段 | API JSON 字段 | 类型 | 说明 |
|---|---|---|---|
| 题目名称 | `title` | string | |
| 题面 | `content` | string | Markdown |
| 分类 | `category` | string | Crypto/Reverse/Forensics/Misc 等 |
| 题目类型 | `type` | `"StaticAttachment"` | 固定值 |
| 环境 | `environment` | `"None"` | 固定值，Attachment 类型必须用 None |
| 是否启用 | `isEnabled` | boolean | |
| 初始分 | `originalScore` | number | |
| 最低分比率 | `minScoreRate` | number | 0.0-1.0 |
| 难度 | `difficulty` | number | 0-10 整数 |
| Flag | `flags` | array | `[{"flag": "...", "orderIndex": 0, "scoreMode": "InheritDecay", "answerType": "Flag"}]` |
| 附件 URL | `attachment.remoteUrl` | string | 绝对 `http` 或 `https` URL |

**注意**：`environment` 必须为 `"None"`，不能填容器/VM 字段。`attachment.remoteUrl` 只接受绝对 http/https URL。详细 API 规范见 `prompts/_api.md`。
