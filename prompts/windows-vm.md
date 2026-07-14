# Windows VM 题型出题指南

## 题型定义

Windows VM：提供 Windows 虚拟机镜像（QCOW2 格式），选手通过 RDP/Guacamole 远程访问进行解题。

适用：Windows 取证、IR（Incident Response）、恶意软件分析、Windows 渗透、AD 域渗透。

## 平台配置字段

| 字段 | 示例 |
|------|------|
| 类型 | `StaticContainer` |
| 环境 | `WindowsVM` |
| 模板 | 从下拉框选择 Windows 模板 |
| Flag | 静态 Flag（当前版本不支持 Windows 动态 Flag） |

## 目录结构

```
category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/                  # 题目设计素材（脚本、配置等）
│   └── ...
├── attachments/             # 给选手的参考附件（如有）
│   └── ...
└── vm/
    ├── image.sha256         # 镜像 SHA256 校验值
    └── build-notes.md       # 镜像制作记录
```

## 镜像制作规范

### 基础要求
- 输出格式：推荐 QCOW2（压缩效率高）
- 操作系统：已激活或符合授权要求
- 驱动：安装 VirtIO 网卡/磁盘驱动
- **启用 RDP**（关键！）
- 防火墙允许 RDP 和题目所需服务
- 使用专用测试账号（如 `ctf/CTFcontest2024!`），**不使用个人账号**
- 自动登录仅在确有展示需求时启用

### 安全清理（必须逐项确认）
- [ ] 删除域账号
- [ ] 清理浏览器个人 Cookie、历史、书签
- [ ] 删除 SSH 私钥
- [ ] 删除生产凭据（数据库密码、API key 等）
- [ ] 清理最近文件列表、回收站
- [ ] 关机后再上传（不要上传运行中的虚拟机磁盘）
- [ ] 清理更新缓存和临时文件

### PVE 制作流程

```bash
# 1. 创建临时 Windows VM
# 2. 磁盘控制器 → VirtIO SCSI，安装 VirtIO 驱动
# 3. 安装题目程序和素材
# 4. 创建本地用户
# 5. 开启 RDP
# 6. 清理痕迹
# 7. 完全关机
# 8. 导出磁盘
qm config <VMID>

# 9. 转换格式
qemu-img convert -p -f raw -O qcow2 /path/to/source.raw windows-ir-v1.qcow2

# 10. 验证
qemu-img info windows-ir-v1.qcow2
qemu-img check windows-ir-v1.qcow2

# 11. 计算校验值
sha256sum windows-ir-v1.qcow2 > windows-ir-v1.qcow2.sha256
```

如果源磁盘已是 QCOW2:
```bash
qemu-img convert -p -f qcow2 -O qcow2 -c source.qcow2 windows-ir-v1.qcow2
```

## Flag 放置位置选择

Flag 可以放在以下位置（根据题目设计选择）：

| 位置 | 适合题型 | 注意事项 |
|------|----------|----------|
| 桌面文本文件 `flag.txt` | 入门题 | 最容易被发现，仅适合引导型题目 |
| 注册表键值 `HKLM\SOFTWARE\CTF\Flag` | 注册表取证 | 提供 regedit 权限 |
| Windows Event Log | 日志分析 | 将 Flag 嵌入事件日志条目 |
| IIS 配置或 Web 目录 | Web+Windows | 模拟 Web 服务被入侵场景 |
| 进程内存 | 内存取证 | 需要在 VM 内导出内存镜像 |
| 删除的文件 | 磁盘取证 | 需要选手用恢复工具 |
| 浏览器历史/密码 | 取证 | 放在 Chrome/Edge 保存的密码中 |

**禁止**：Flag 出现在登录欢迎语、壁纸文字、最近文件预览等意外暴露位置。

## 常见题型设计

### Windows 取证
- 提供被"入侵"后的 Windows 环境
- 选手需分析日志、注册表、文件系统
- Flag 藏在攻击者留下的痕迹中

### Windows IR（事件响应）
- 模拟真实安全事件场景
- 预置恶意行为痕迹（进程、服务、计划任务、日志）
- 选手通过 Sysinternals 等工具分析

### 恶意软件分析
- 预置恶意样本（建议使用无害的 CTF 专用样本）
- 选手在隔离 VM 中分析
- Flag 隐藏在样本行为或配置中

## 上传平台流程

1. 管理 → 环境模板
2. 上传 `.qcow2/.ova/.vmdk/.img`
3. 文件名包含 `windows` 或 `winserver`（便于系统识别 OS）
4. 等待状态 Ready
5. 确认 OS 类型 = Windows、SHA256 存在、大小合理
6. 确认 KVM 节点在线
7. 新建题目：类型 `StaticContainer`，环境 `WindowsVM`
8. 从下拉框选择模板
9. 添加静态 Flag，启用题目
10. 用选手账号创建 VM 并通过 RDP/Guacamole 连接验证

## build-notes.md 模板

```markdown
# {题目标题} - 镜像制作记录

## 基础信息
- 制作日期：2026-07-14
- 制作人：{name}
- 基础镜像：Windows 10 Enterprise 22H2
- 输出文件：windows-ir-v1.qcow2
- SHA256：{sha256}
- 文件大小：{size}

## 安装的软件
- Sysinternals Suite
- Wireshark
- Notepad++

## 题目配置
- 管理员账号：ctf-admin / {password}
- 题目账号：ctf / {password}
- RDP：已启用（端口 3389）
- 防火墙：允许 RDP + 题目服务端口

## Flag 位置
- Flag 文件：C:\Users\ctf\Desktop\secret.txt
- Flag 值：flag{...}

## 题目服务
- 服务名：{name}
- 状态：已设置开机自启动

## Sysprep 状态
- 是否执行：{是/否}

## 制作步骤回顾
1. 创建 Windows VM，安装 VirtIO 驱动
2. 安装题目软件
3. 配置用户和凭据
4. 放置 Flag 和相关线索
5. 清理痕迹
6. 关机
7. 导出 QCOW2
8. 计算 SHA256
```

## Windows 验收标准

1. VM 能在目标 KVM 节点启动
2. IP、RDP 端口和 Guacamole 入口正确
3. 远程登录凭据有效
4. 题目服务开机自启动
5. 重启 VM 后服务仍可用
6. Flag 可按预期解出
7. 停止后 VM 和远程连接记录被清理
