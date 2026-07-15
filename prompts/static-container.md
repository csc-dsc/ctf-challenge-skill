# StaticContainer 题型出题指南

## 题型定义

StaticContainer：所有队伍共享同一个 Docker 容器环境或 Windows VM，Flag 相同。

适用：固定的 Web/PWN 靶场环境，Windows 取证/IR 靶机，所有人访问同一个服务。

## 与 DynamicContainer 的区别

| | StaticContainer | DynamicContainer |
|---|---|---|
| 实例 | 所有队伍共享一个 | 每队独立 |
| Flag | 静态，所有人相同 | 动态，GZCTF_FLAG 注入 |
| 环境 | Docker 或 WindowsVM | Docker only |

## 平台配置字段

| 字段 | 示例 |
|------|------|
| 类型 | `StaticContainer` |
| 环境 | `Docker` |
| 镜像 | `10.24.0.28:5000/gzctf/web/demo:20260711` |
| 内部端口 | `80` |
| 内存 | `256 MiB` |
| CPU | `2`（约 0.2 CPU） |
| 存储 | `512 MiB` |
| 网络 | `Isolated` |
| Flag | 通过 Flag 区域添加固定值 |

## 目录结构

```
category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/
│   └── ...
├── attachments/
│   └── ...
└── docker/
    ├── Dockerfile
    ├── docker-compose.test.yml
    └── healthcheck.sh
```

## 与 DynamicContainer 共享的 Docker 规则

所有 C1-C8 规则适用（见 `_shared.md` 和 `dynamic-container.md`）：
- 0.0.0.0 绑定
- 非 root 用户
- HEALTHCHECK
- Exec CMD
- 端口映射 0.0.0.0:HOST:CONTAINER

## StaticContainer 特有注意事项

1. **Flag 是静态的**：在 Dockerfile 或启动脚本中可以直接写入，但仍建议通过 `GZCTF_FLAG` 环境变量传入以便测试
2. **需要防非预期读取**：避免选手通过 `docker inspect`、环境变量泄露等方式直接拿到 Flag
3. **单实例风险**：一个队伍破坏环境会影响所有队伍，需要设计好容错和重置机制

## 常见题型

### 静态 Web 靶场
- 所有选手访问同一 URL
- 漏洞固定，Flag 固定
- 适合：代码审计类、配置漏洞类

### 静态 PWN 环境
- xinetd 暴露端口
- 所有选手连接同一端口
- Flag 放在 `/flag`，通过漏洞读取

### 工具型环境
- 提供完整的工具链（如 Kali 容器）
- 选手 SSH 进去利用工具解题
- 注意：需要限制资源使用

## 自检步骤

同 dynamic-container.md 中的 Docker 测试步骤。

## API 导入字段映射（v2）

### Docker 环境

| README 字段 | API JSON 字段 | 类型 | 说明 |
|---|---|---|---|
| 题目名称 | `title` | string | |
| 题面 | `content` | string | Markdown |
| 分类 | `category` | string | |
| 题目类型 | `type` | `"StaticContainer"` | 固定值 |
| 环境 | `environment` | `"Docker"` | 固定值 |
| 镜像 | `containerImage` | string | 完整 Registry 引用 |
| 内部端口 | `exposePort` | number | |
| CPU | `cpuCount` | number | 默认 1 |
| 内存 | `memoryLimit` | number | MiB，默认 256 |
| 存储 | `storageLimit` | number | MiB，默认 512 |
| 网络模式 | `networkMode` | `"Open"` 或 `"Isolated"` | |
| 是否启用 | `isEnabled` | boolean | |
| 初始分 | `originalScore` | number | |
| 最低分比率 | `minScoreRate` | number | 0.0-1.0 |
| 难度 | `difficulty` | number | 0-10 整数 |
| Flag | `flags` | array | `[{"flag": "...", "orderIndex": 0, "scoreMode": "InheritDecay", "answerType": "Flag"}]` |

### WindowsVM 环境

| 差异字段 | API JSON 字段 | 说明 |
|---|---|---|
| 环境 | `environment` | `"WindowsVM"` |
| 镜像模板 ID | `imageTemplateId` | number，**不能用** `containerImage` |
| 端口/CPU/内存/存储 | — | WindowsVM 不需要这些字段 |

详细 API 规范见 `prompts/_api.md`。
