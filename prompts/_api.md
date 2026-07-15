# Open API v1 集成指南

当用户配置了平台凭据时，reviewer 通过后可通过 Open API 自动将题目导入平台。

## Token 设置

用户在平台 "账户 → API Token" 页面创建 Token，格式为 `gzctf_pat_{tokenId}.{secret}`。

**必须选择的 scope：**
- `challenges:read`, `challenges:write`, `challenges:delete`
- `operations:read`
- `images:read`, `images:write`, `images:delete`

**必须添加资源授权：**
- `resourceType = game`, `resourceId = {比赛ID}`
- 教师只能对自己创建的比赛授权；管理员才能用 `game:*`

Token 明文只显示一次。提醒用户立即保存。

## 凭据传入

三种方式，优先级从高到低：

1. **CLI 参数**（单次使用）：`--host platform.example.com --token gzctf_pat_xxx.yyy`
2. **环境变量**（推荐）：`GZCTF_HOST` + `GZCTF_TOKEN`
3. **配置文件**（持久化）：`~/.gzctf/config.json`

```json
{"host": "platform.example.com", "token": "gzctf_pat_xxx.yyy"}
```

用 `python3 scripts/ctf_client.py configure --set KEY=VALUE` 管理配置文件。

**安全提醒：Token 不要粘贴到聊天中，不要写入 Git 仓库。**

## 题目 JSON 字段映射

### 所有类型通用字段

| README 元数据 | API JSON 字段 | 类型 | 说明 |
|---|---|---|---|
| 题目名称 | `title` | string | |
| 题面 | `content` | string | Markdown 格式 |
| 分类 | `category` | string | Misc/Crypto/Pwn/Web/Reverse/Blockchain/Forensics/Hardware/Mobile/PPC/AI/Pentest/OSINT/IR |
| 题目类型 | `type` | string | StaticAttachment/StaticContainer/DynamicAttachment/DynamicContainer |
| 难度 | `difficulty` | number | 0-10 的整数（原 difficulty 字段无用，改用此字段） |
| 初始分 | `originalScore` | number | |
| 最低分比率 | `minScoreRate` | number | 0.0-1.0，默认 0.25 |
| 是否启用 | `isEnabled` | boolean | |

### StaticAttachment / StaticContainer（非 DynamicContainer）

```json
{
  "externalId": "web-intro",
  "title": "Web Intro",
  "content": "访问附件并提交 Flag。",
  "category": "Web",
  "type": "StaticAttachment",
  "environment": "None",
  "isEnabled": true,
  "originalScore": 500,
  "minScoreRate": 0.25,
  "difficulty": 5,
  "flags": [
    {
      "flag": "flag{web_intro}",
      "orderIndex": 0,
      "scoreMode": "InheritDecay",
      "answerType": "Flag"
    }
  ],
  "attachment": {
    "remoteUrl": "https://assets.example/challenges/web-intro.zip"
  }
}
```

规则：
- `environment`: Attachment 类型只能用 `"None"`，不能填容器/VM 字段
- `flags`: 至少一个 Flag；`scoreMode` 为 `"InheritDecay"`；`answerType` 为 `"Flag"`
- `attachment.remoteUrl`: 只接受绝对 `http` 或 `https` URL

### StaticContainer (Docker)

```json
{
  "externalId": "static-web-01",
  "title": "Static Web Challenge",
  "content": "...",
  "category": "Web",
  "type": "StaticContainer",
  "environment": "Docker",
  "containerImage": "10.24.0.28:5000/challenges/static-web:v1",
  "exposePort": 80,
  "cpuCount": 1,
  "memoryLimit": 256,
  "storageLimit": 512,
  "networkMode": "Open",
  "isEnabled": true,
  "originalScore": 500,
  "difficulty": 5,
  "flags": [
    { "flag": "flag{static_web}", "orderIndex": 0,
      "scoreMode": "InheritDecay", "answerType": "Flag" }
  ]
}
```

规则：
- `containerImage`: 必须是已 Ready 的镜像模板的完整 Registry 引用
- `exposePort`: 容器内部端口号
- `environment`: Container 类型省略时默认 `"Docker"`
- 不能用 `imageTemplateId`（那是 WindowsVM 的）

### DynamicContainer

```json
{
  "externalId": "web-dynamic-01",
  "title": "Dynamic Web",
  "content": "获取环境地址并完成利用。",
  "category": "Web",
  "type": "DynamicContainer",
  "environment": "Docker",
  "containerImage": "10.24.0.28:5000/challenges/web:v1",
  "exposePort": 80,
  "flagTemplate": "flag{web_[TEAM_HASH]}",
  "cpuCount": 1,
  "memoryLimit": 256,
  "storageLimit": 512,
  "networkMode": "Isolated",
  "isEnabled": true,
  "originalScore": 500,
  "difficulty": 5
}
```

规则：
- 必须提供 `flagTemplate`，例如 `flag{web_[TEAM_HASH]}`
- **不需要** `flags` 数组（DynamicContainer 用 flagTemplate 替代）
- 必须启用

### StaticContainer (WindowsVM)

```json
{
  "externalId": "windows-ad-01",
  "title": "Windows Lab",
  "content": "通过远程桌面进入靶机。",
  "category": "Pentest",
  "type": "StaticContainer",
  "environment": "WindowsVM",
  "imageTemplateId": 42,
  "isEnabled": true,
  "originalScore": 1000,
  "difficulty": 7,
  "flags": [
    { "flag": "flag{windows_lab}", "orderIndex": 0,
      "scoreMode": "InheritDecay", "answerType": "Flag" }
  ]
}
```

规则：
- `environment`: `"WindowsVM"`
- 必须用 `imageTemplateId`（整数），不能用 `containerImage`
- 不能填 Docker 字段

## 镜像注册（两种方案）

### 方案 A：Registry 引用（推荐，内网可用 10.24.0.28:5000）

```bash
# 1. Tag 并推送
docker tag {image}:test 10.24.0.28:5000/challenges/{name}:{version}
docker push 10.24.0.28:5000/challenges/{name}:{version}

# 2. 注册引用
python3 scripts/ctf_client.py image register-reference \
    --name "{name}" \
    --registry-url "10.24.0.28:5000/challenges/{name}:{version}" \
    --os-type Linux

# 3. 等待就绪（register-reference 返回的 id）
python3 scripts/ctf_client.py image wait-ready --image-id {id}
```

**允许的引用来源：**
- 固定内部 Registry `10.24.0.28:5000`
- 无需凭据、DNS 全部解析到公网地址的公开 Registry

**禁止：回环、链路本地、私网第三方 Registry、携带 URL 凭据的引用。**

### 方案 B：Archive 上传（离线或外网环境）

```bash
# 1. 导出镜像
docker save {image}:test -o {name}.tar

# 2. 上传
python3 scripts/ctf_client.py image upload-archive \
    --path "{name}.tar" \
    --name "{name}" \
    --repository "challenges/{name}" \
    --tag "{version}" \
    --source-image "{image}:test"

# upload-archive 内部会轮询直到完成
```

## 题目导入

### 单个导入

```bash
# 1. 生成 challenge-def.json（按上面字段映射）
# 2. 导入
python3 scripts/ctf_client.py challenge import \
    --game-id {gameId} \
    --file {challenge_dir}/challenge-def.json
```

### 批量导入（1-100 题，原子操作）

```bash
python3 scripts/ctf_client.py challenge import-batch \
    --game-id {gameId} \
    --file {challenge_dir}/challenge-defs.json
```

`challenge-defs.json` 格式：
```json
{
  "items": [
    { "externalId": "web-01", "title": "...", ... },
    { "externalId": "web-02", "title": "...", ... }
  ]
}
```

批次内 `externalId` 必须唯一。任一题无效则整批不创建。

### 导入后验证

```bash
python3 scripts/ctf_client.py challenge list --game-id {gameId}
python3 scripts/ctf_client.py challenge get --game-id {gameId} --challenge-id {id}
```

## Idempotency-Key 规范

所有写操作（POST/DELETE）必须带 `Idempotency-Key` header。

格式：`{prefix}-{ISO-date}-{random-8-hex}`，如 `image-ref-web-ssti-20260715-a1b2c3d4`

规则：
- 长度 1-128，仅 ASCII 字母、数字、`-`、`_`、`.`
- 同一 Token、同一路由、相同 Key + 相同 Body → 返回原 operation
- 相同 Key 但 Body 不同 → 返回 `409 idempotency_conflict`
- operation 正在执行时重复 → 返回相同 operation ID

**重要：** 不要用新 Key 盲目重试状态未知的写操作，应先查询原 operation。
**重要：** 遇到 409 时，读取错误信息或查询已有 operation ID 进行轮询，不要放弃。

## 操作轮询

所有写操作返回 `202 Accepted` + operation JSON。`ctf_client.py` 内部自动轮询：
- 退避策略：1s → 2s → 4s → 8s → 10s 固定
- 超时：默认 300 秒（image upload 600 秒）
- Succeeded (status=2)：返回最终结果
- Failed (status=3)：抛出 `PlatformOperationError`

如果客户端轮询被中断，可用返回的 operation ID 重新查询：
```bash
curl -H "Authorization: Bearer $GZCTF_TOKEN" \
  https://{host}/api/open/v1/operations/{operation-id}
```

## 错误恢复

| HTTP | 含义 | 处理方式 |
|------|------|---------|
| 400 | JSON/Key 格式错误 | 修正请求体或 Key，不重试原请求 |
| 401 | Token 无效 | 提醒用户重新生成 Token |
| 403 | 缺少 scope 或比赛授权 | 检查 scope 和 resourceType/resourceId |
| 404 | 比赛/题目/operation 不存在 | 确认 ID 正确 |
| 409 | Idempotency-Key 冲突 | 查询已有 operation 或换 Key |
| 422 | 业务验证失败 | 根据 detail 修正 JSON，**同 Key 重试** |
| 429 | 请求配额耗尽 | 读 Retry-After 等待后重试 |
| 503 | 后端不可用 | 指数退避重试 3 次 |
