# GZCTF Open API v1 协议（AI 可执行版）

只能在 reviewer PASS 后导入。真实前缀是 `${GZCTF_HOST}/api/open/v1`，认证使用
`Authorization: Bearer ${GZCTF_TOKEN}`。不要调用内部 `/api/...` 页面接口，也不要
把 Token 写入题包、日志、Git、命令参数或输出 JSON。

## 身份、权限和责任

Token 由管理员/教师在 API Token 页面创建，明文只显示一次。为每个 AI、CI 或
操作者创建独立 Token。平台记录 token ID、创建者用户 ID、资源、路由、operation、
trace 和 IP 摘要，可明确追责上传者。

| 目标 | Scope | Resource grant | 最低角色 |
|---|---|---|---|
| 公共练习 | `exercises:read/write` | `exercise:*` | Teacher |
| 培训课程 | `training:write` | `training-course:*` | Teacher |
| 理论题库 | `theory:write` | `theory-bank:*` | Teacher |
| 比赛理论试卷 | `theory:write` | `game:{gameId}` | Teacher/比赛管理者 |
| 比赛题目（含 AWDP） | `challenges:read/write/delete` | `game:{gameId}` | Teacher/比赛管理者 |
| 战队 | `teams:write` | `team:*` | Admin |

轮询还需要 `operations:read`；删除练习才增加 `exercises:delete`。Token 创建者角色被
降低、禁用或 Token 被撤销后，权限立即失效。

## 路由与幂等

```text
GET    /exercises
GET    /exercises/{exerciseId}
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

`/api/Exercise/pool/backfill` is deliberately not an Open API route. It is an
administrator/teacher browser-session maintenance action for historical data;
do not call it with an API Token, and never replace it with direct database
writes. See **Exercise pool collection** below.

所有写请求都必须带唯一、稳定的 `Idempotency-Key`（ASCII，1-128 字符）。响应为
`202 Accepted` 和 operation；轮询到 `Succeeded` 或 `Failed`。相同 token、路由、
key 和请求体复用 operation；相同 key 但请求体不同返回 `409 idempotency_conflict`。
未知结果先查询原 operation，不要换 key 重复创建。

## 公共练习

`POST /exercises/import`：

```json
{"items":[{
  "externalId":"web-ssti-001",
  "title":"SSTI 入门",
  "content":"Markdown 题面",
  "category":"Web",
  "type":"DynamicContainer",
  "difficulty":"Normal",
  "isEnabled":true,
  "tags":["web"],
  "containerImage":"registry.example/labs/ssti:v1",
  "memoryLimit":256,
  "storageLimit":512,
  "cpuCount":1,
  "exposePort":8080,
  "networkMode":"Isolated",
  "environment":"Docker",
  "flagTemplate":"flag{web_[TEAM_HASH]}",
  "flags":[],
  "attachment":{"remoteUrl":"https://assets.example/ssti.zip"}
}]}
```

批量 1-100 题。静态题提供 `flags`；动态容器提供 `flagTemplate`。附件只支持绝对
HTTP/HTTPS URL，不支持 multipart。创建单题使用相同字段但无 `externalId`；PUT 是
全量替换。

## Exercise pool collection

New or updated game, training, and AWDP resources are collected into the
practice pool only when they are independently runnable and verifiable. Before
creating a source resource intended for the pool, satisfy these prerequisites:

| Source | Required for collection | Pool result |
|---|---|---|
| Game or training challenge | Container challenge type; `containerImage` or `imageTemplateId`; at least one `flags` entry or `flagTemplate` | Clones statement, metadata, attachment, flags, and runtime settings with source tracing |
| AWDP service | Non-empty `imageName`; matching Ready Docker image template; non-empty `flagTemplate` | Clones as an isolated dynamic-container practice exercise |
| Theory, attachment-only, or incomplete container challenge | Does not meet the above conditions | Intentionally not collected |

Collection never reuses a live competition instance. It deep-copies the source
definition and preserves provenance (`Game`, `Training`, or AWDP source ID).

### Historical backfill

After deploying collection to an existing platform, historical records remain
unchanged until a Teacher+ user invokes:

```text
POST /api/Exercise/pool/backfill
```

Use the already authenticated platform browser session. The JSON response has
`gameCollected`, `trainingCollected`, `awdpCollected`, `ineligible`, and
`failed`. Treat `ineligible` as a source-data prerequisite failure, not an
import error. Correct the source image/template/Flag configuration, then invoke
the same authorized maintenance action again. Do not expose this endpoint in
`ctf_client.py` and do not use SSH credentials as platform credentials.

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
