# DynamicAttachment 题型出题指南

## 题型定义

DynamicAttachment：每队下载不同的附件，每个附件对应不同的 Flag。无在线环境。

适用：每队独立的流量包、配置文件、数据集、个性化加密数据。

## 与 StaticAttachment 的区别

| | StaticAttachment | DynamicAttachment |
|---|---|---|
| 附件 | 所有人相同 | 每队不同 |
| Flag | 所有人相同 | 每队不同（与附件绑定） |
| 出题工作量 | 1 个附件 | N 个附件（N = 队伍数） |

## 平台配置字段

| 字段 | 示例 |
|------|------|
| 类型 | `DynamicAttachment` |
| 环境 | `None` |
| 附件 | 批量上传 N 个文件 |
| 每个文件 → Flag | 一一对应配置 |

## 目录结构

```
category-knowledge-difficulty-v1/
├── README.md
├── statement.md
├── writeup.md
├── flag-policy.md
├── source/
│   ├── generate.py          # 附件批量生成脚本
│   └── ...
├── attachments/
│   ├── team_001.zip
│   ├── team_002.zip
│   └── ...
├── flag-mapping.csv          # 内部：文件名 ↔ Flag 映射表
└── flag-mapping.csv.sha256
```

## 附件生成要求

1. **每队文件必须唯一**：内容差异可验证（不同的加密密钥、不同的嵌入数据等）
2. **生成脚本**放到 `source/` 中，可复现
3. **映射表**：`flag-mapping.csv` 记录 `文件名, Flag` 对应关系，**不发给选手**
4. **交叉提交验证**：A 队的 Flag 不能通过 B 队附件解出

## 生成脚本模板

```python
#!/usr/bin/env python3
"""生成 N 个不同的附件，每个包含不同的 Flag"""
import os
import random
import string
import zipfile

def generate_flag():
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))
    return f"flag{{{suffix}}}"

def generate_attachment(team_id: int, flag: str, output_dir: str):
    """为指定队伍生成附件文件"""
    filename = f"team_{team_id:03d}.zip"
    filepath = os.path.join(output_dir, filename)

    # 创建包含该队 Flag 的数据文件
    data_content = f"encrypted_data_{team_id}_{random.randint(1000, 9999)}"

    with zipfile.ZipFile(filepath, 'w') as zf:
        zf.writestr("data.txt", data_content)
        zf.writestr("key.txt", flag)  # 仅示意，实际应按题型设计

    return filename, flag

def main():
    num_teams = 50
    output_dir = "attachments"
    os.makedirs(output_dir, exist_ok=True)

    mapping = []
    for i in range(1, num_teams + 1):
        flag = generate_flag()
        filename, flag = generate_attachment(i, flag, output_dir)
        mapping.append((filename, flag))

    with open("flag-mapping.csv", "w") as f:
        f.write("filename,flag\n")
        for filename, flag in mapping:
            f.write(f"{filename},{flag}\n")

    print(f"Generated {num_teams} attachments in {output_dir}/")
    print(f"Mapping saved to flag-mapping.csv")

if __name__ == "__main__":
    main()
```

## 注意事项

1. 附件文件名应唯一（使用编号或哈希区分）
2. 映射表放在交付资料内部，不上传平台
3. 平台上传时逐个配置文件→Flag 对应关系
4. 确认页面显示正确的配置数量
5. 用两个队伍账号下载不同附件并交叉提交验证

## 自检步骤

1. 运行生成脚本生产 N 个附件
2. 随机抽 3 个附件验证：按 writeup 步骤可解出该队的 Flag
3. 用 A 队 Flag 在 B 队附件中验证：应无法解出
4. 确认 `flag-mapping.csv` 有 N 行记录
5. 确认附件 SHA256 各不同

## 难度设计指南

### Easy（15-30 分钟）
- 每队附件只有密钥不同，加密算法相同且已知
- Flag 在附件中直接可提取（解密后明文）

### Medium（30-90 分钟）
- 每队附件用不同算法变体（如不同 S-Box）
- 需要先逆向或分析才能找到提取方法

### Hard（1-4 小时）
- 每队附件有完全不同的加密路径
- 需要逆向自定义保护 + 侧信道或数学攻击

> **API 自动导入（未来功能）**：导入字段映射见 `prompts/_api.md`。
