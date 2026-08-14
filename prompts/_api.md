# GZCTF Open API v1 协议（AI 可执行版）

只能在 reviewer PASS 后导入。真实前缀是 `${GZCTF_HOST}/api/open/v1`，认证使用
`Authorization: Bearer ${GZCTF_TOKEN}`。不要调用内部 `/api/...` 页面接口，也不要
把 Token 写入题包、日志、Git、命令参数或输出 JSON。

## 身份、权限和责任

Token 由管理员/教师在 API Token 页面创建，明文只显示一次。为每个 AI、CI 或
操作者创建独立 Token。平台记录 token ID、创建者用户 ID、资源、路由、operation、
trace 和 IP 摘要，可明确追责上传者。

在接受 Token 或发送任何请求前，Skill 必须先向用户声明本次导入所需的最小 scope、resource
grant 和阶段。容器题必须单列镜像发布阶段；没有新镜像、只引用已 Ready 且已授权模板时才不需要
`images:write`。不得用一个宽泛管理员 Token 代替该声明。

| 目标 | Scope | Resource grant | 最低角色 |
|---|---|---|---|
| 公共练习 | `exercises:read/write` | `exercise:*` | Teacher |
| 附件资产 | `assets:write`（读取/删除分别为 `assets:read` / `assets:delete`） | 所有者或 `asset:{sha256}` / `asset:*` | Teacher |
| Docker 镜像归档/引用 | `images:write` | 无额外资源授权 | Teacher |
| 培训课程 | `training:write` | `training-course:*` | Teacher |
| 理论题库 | `theory:write` | `theory-bank:*` | Teacher |
| 比赛理论试卷 | `theory:write` | `game:{gameId}` | Teacher/比赛管理者 |
| 比赛题目（含 AWDP） | `challenges:read/write/delete` | `game:{gameId}` | Teacher/比赛管理者 |
| 战队 | `teams:write` | `team:*` | Admin |

轮询还需要 `operations:read`；删除练习才增加 `exercises:delete`。Token 创建者角色被
降低、禁用或 Token 被撤销后，权限立即失效。

容器题分两阶段最小授权：先使用镜像发布 Token（`images:write`、`operations:read`）上传
archive 或登记用户提供的 Registry 引用并等待镜像 Ready；再使用练习导入 Token
（附件为 `assets:write`；练习为 `exercises:read`、`exercises:write`、`operations:read`、`exercise:*`）导入题目。可以由
同一位教师创建两个短期 Token，但不得以缺少 `images:write` 的练习 Token 上传镜像，也不得
把任一 Token 写入题目文件、命令行、日志或导入结果。

## 路由与幂等

```text
GET    /exercises
GET    /exercises/{exerciseId}
POST   /assets
GET    /assets/{hash}
DELETE /assets/{hash}
POST   /exercises
POST   /exercises/import
PUT    /exercises/{exerciseId}
DELETE /exercises/{exerciseId}
POST   /training/courses/import
POST   /theory/questions/import
PUT    /theory/games/{gameId}/paper
POST   /teams/import
GET    /games/{gameId}/awdp-services
GET    /games/{gameId}/awdp-services/{serviceId}
POST   /games/{gameId}/awdp-services
POST   /games/{gameId}/awdp-services/batch
DELETE /games/{gameId}/awdp-services/{serviceId}
POST   /games/{gameId}/awdp-services/batch-delete
GET    /operations/{operationId}
```

所有写请求都必须带唯一、稳定的 `Idempotency-Key`（ASCII，1-128 字符）。响应为
`202 Accepted` 和 operation；轮询到 `Succeeded` 或 `Failed`。相同 token、路由、
key 和请求体复用 operation；相同 key 但请求体不同返回 `409 idempotency_conflict`。
未知结果先查询原 operation，不要换 key 重复创建。

## 公共练习

公共 Exercise 支持独立直接导入，不要求先创建比赛或培训资源。Reverse 等附件题进入题目池
的标准方式就是 `exercise import`：静态附件带 `attachment` 与 `flags`，动态附件带附件与
动态 Flag 规则。当前运行中的 `/exercises/import` 契约不包含容器运行字段；容器题必须先将
镜像上传/登记并等待 Ready，再逐题调用 `exercise create`。所有题型都必须同时提供
`category`、`difficulty`、`tags`、题面和稳定 `externalId`；这些字段由 Skill 自动填充。

`POST /exercises/import`（附件/无运行时字段的批量导入）：

```json
{"items":[{
  "externalId":"web-ssti-001",
  "title":"SSTI 入门",
  "content":"Markdown 题面",
  "category":"Web",
  "type":"StaticAttachment",
  "difficulty":"Normal",
  "isEnabled":true,
  "tags":["web"],
  "flags":[{"flag":"flag{attachment_example}","orderIndex":0}],
  "attachment":{"remoteUrl":"https://assets.example/ssti.zip"}
}]}
```

批量 1-100 题。静态附件题提供 `flags`；动态附件提供 `flagTemplate`。附件只支持绝对
HTTP/HTTPS URL；`exercise import` 本身不接收 multipart，附件必须先通过 `/assets` 上传。

`POST /exercises`（容器练习单题创建）使用 `ExerciseCreateModel`，不含 `externalId`，但可以
传入 `containerImage` 或 `imageTemplateId`、资源限制、端口、网络和 `flagTemplate`。为每个
容器题使用稳定、唯一的 Idempotency-Key，并将题目包中的 `externalId` 与 operation 返回的
`exerciseId` 写入不含凭据的 `batch-result.json`。

直接导入成功即创建 Exercise 题目池资源，来源标记为 `Exercise`；它与比赛、培训和 AWDP
资源满足运行资格后自动深复制到题库的来源收录流程相互独立。

## Exercise pool collection

New or updated game, training, and AWDP resources are collected into the
practice pool only when they are independently runnable and verifiable. Before
creating a source resource intended for the pool, satisfy these prerequisites:

| Source | Required for collection | Pool result |
|---|---|---|
| Game or training challenge | Container challenge type; `containerImage` or `imageTemplateId`; at least one `flags` entry or `flagTemplate` | Clones statement, metadata, attachment, flags, and runtime settings with source tracing |
| AWDP service | Non-empty `imageName`; matching Ready Docker image template; non-empty `flagTemplate` | Clones as an isolated dynamic-container practice exercise |
| Theory or resource without attachment/image and Flag | Does not meet the above conditions | Intentionally not collected |
| Attachment challenge with a valid attachment and Flag | Independently solvable | Collected as an attachment exercise |

Collection never reuses a live competition instance. It deep-copies the source
definition and preserves provenance (`Game`, `Training`, or AWDP source ID).

## 培训课程

`POST /training/courses/import` 的 `items` 为 1-50 门课程。每门课程可携带：

```json
{"items":[{
  "externalId":"course-web-001",
  "title":"Web 安全基础",
  "publish":false,
  "chapters":[{"externalId":"chapter-1","title":"HTTP","order":1}],
  "exercises":[{
    "externalId":"lab-1","chapterExternalId":"chapter-1",
    "title":"HTTP Lab","content":"题面","category":"Web",
    "type":"StaticContainer","environment":"Docker",
    "containerImage":"registry.example/labs/http:v1","exposePort":8080,
    "flags":[{"flag":"flag{http}","orderIndex":0}]
  }],
  "theoryQuestions":[],
  "theoryPapers":[]
}]}
```

`parentExternalId` 建章节树；`chapterExternalId` 绑定实验/章节试卷；
`sourceQuestionExternalId` 引用本批课程题。Docker/VM 模板必须已在平台 Ready。
Token 创建者成为课程 Owner。

## 比赛与 AWDP 题目

普通比赛题目使用 `/games/{gameId}/challenges`；AWDP 服务使用同一比赛资源授权和
`challenges:*` scope，但独立路径 `/games/{gameId}/awdp-services`。AWDP 导入字段：

```json
{
  "externalId":"awdp-web-001", "name":"AWDP SSTI", "content":"服务题面",
  "category":"Web", "difficulty":"Hard", "tags":["AWDP","web"],
  "flagTemplate":"flag{[GUID]}", "imageName":"registry.example/awdp/ssti:v1",
  "exposePort":8080, "checkerScript":"...", "checkerEntrypoint":"python3 checker.py",
  "expScript":"...", "expEntrypoint":"python3 exp.py",
  "originalScore":1000, "attackPoints":50, "slaPoints":20,
  "patchPoints":100, "serviceAbnormalPenalty":200,
  "maxAttackPerRound":3, "attackPhaseMinutes":15,
  "patchPhaseMinutes":10, "totalRounds":20,
  "maxResetCount":10, "maxRecoveryCount":5
}
```

镜像必须是平台 Ready 的 Docker 模板，`flagTemplate` 必须有效。导入成功后，平台
自动创建/更新 AWDP 服务，并以动态容器模式深复制到公共题目池，使用独立的
`SourceAwdpServiceId` 溯源；不会复用赛事容器、Flag 或附件。重复 `externalId` 是
幂等更新，题目池收录结果可在 operation result 的 `awdpImported` 中查看。

## 理论题库和试卷

`POST /theory/questions/import`：

```json
{"items":[{
  "externalId":"theory-http-001","type":"SingleChoice","bankName":"Web",
  "title":"资源不存在状态码","content":"请选择","options":["200","404"],
  "answerIndexes":[1],"tags":["HTTP"]
}]}
```

题库批量 1-1000 题，答案下标从 0 开始。`PUT /theory/games/{gameId}/paper` 请求体包含
`title`、`description`、`publish`、`questions`；每题含上述题目字段及 `score`、
`order`，可带 `sourceQuestionId`。目标必须是 Theory/Mixed 比赛；已有已提交答卷时
不能替换。

## 战队

`POST /teams/import`：

```json
{"items":[{
  "externalId":"team-red-001","name":"Red Team","locked":false,
  "captain":{"userName":"captain"},
  "members":[{"userName":"member1"}]
}]}
```

批量 1-200 支，只能引用现有用户，不创建账号。用户引用可给 `userId`、`userName`
或两者；同时给出时必须匹配。仅管理员 Token 可调用。

## 操作顺序

1. 本地生成并通过 reviewer，确认所需镜像 Ready。
2. 从环境变量读取 Token，提交导入并保存 operation ID。
3. 轮询 `/operations/{id}`；成功后保存 `result.items` 中的
   `externalId/resourceType/resourceId/action` 映射。
4. 失败时读取 `errorCode/errorDetail/traceId`；修正请求后使用新 key。
5. 完成后撤销短期 Token。

```text
python scripts/ctf_client.py exercise import --file exercise-import.json
python scripts/ctf_client.py training import-courses --file course-import.json
python scripts/ctf_client.py theory import-questions --file theory-bank.json
python scripts/ctf_client.py theory import-paper --game-id 42 --file theory-paper.json
python scripts/ctf_client.py team import --file teams.json
python scripts/ctf_client.py awdp import --game-id 42 --file awdp-service.json
python scripts/ctf_client.py awdp import-batch --game-id 42 --file awdp-services.json
```

客户端自动轮询且不打印 Token。`401` 表示 Token 无效，`403` 表示 scope/resource
不足，`404` 表示资源不可见，`409` 表示幂等或状态冲突，`422` 表示业务校验失败，
`429` 表示配额限制，`503` 表示依赖不可用。错误体为 `application/problem+json`，
按稳定 `code` 分支。
### 容器题实际导入顺序

1. 完成本地 Docker Compose 健康检查、非 root 检查和题目专用 solver 验收。
2. 使用 `asset upload` 上传附件，保存返回的 `remoteUrl`、Hash 和 `creatorUserName`。
3. 使用 `image upload-archive` 或 Registry 引用登记镜像，并轮询 operation 直到镜像 `Ready`。
4. 使用 `exercise create` 提交包含 `containerImage`、端口、`flagTemplate` 和附件 URL 的单题 JSON。
5. 轮询练习 operation，再用 `exercise get` 回读题目、镜像、附件和创建者。
6. 失败时按练习、镜像、附件逆序清理；已引用附件删除返回 409 时不得强删。

附件上传是 Token Open API，不依赖浏览器会话。平台审计记录 Token、账户、路由和时间。
