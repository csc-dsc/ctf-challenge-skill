# GZCTF Exercise Open API v1 协议（AI 可执行版）

你只能在 reviewer PASS 后导入题目。真实接口前缀是 `${GZCTF_HOST}/api/open/v1`，
认证使用 `Authorization: Bearer ${GZCTF_TOKEN}`。不要猜测或调用内部 `/api/...`
页面接口，也不要把 Token 写入题包、日志、Git 或输出 JSON。

## 身份和责任

Token 由平台管理员/教师在 API Token 管理界面创建，明文只显示一次。为每个 AI/CI/
操作者创建独立 Token，至少授予：`exercises:write`、`exercises:read`、
`operations:read`；删除才额外授予 `exercises:delete`。公共题库授权为
`exercise:*`，单题操作可收紧为 `exercise:{exerciseId}`。平台会记录 token ID、
创建者用户 ID、资源、路由、operation、trace 和 IP 摘要，可明确追责上传者。

## 路由

```text
GET    /exercises
GET    /exercises/{exerciseId}
POST   /exercises
POST   /exercises/import
PUT    /exercises/{exerciseId}
DELETE /exercises/{exerciseId}
GET    /operations/{operationId}
```

所有写请求都必须带唯一、稳定的 `Idempotency-Key`（ASCII，1-128 字符）。响应为
`202 Accepted` 和 operation；轮询 operation 到 `Succeeded` 或 `Failed`。相同 token、
路由、key 和请求体复用 operation；相同 key 但请求体不同返回 `409 idempotency_conflict`。
未知结果先查询原 operation，不要换 key 重复创建。

## 导入请求

`POST /exercises/import` 的 JSON 必须是：

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
  "hints":[],
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

`items` 数量为 1-100；`externalId` 是调用方关联 ID，不是平台主键。静态题可以提供
多个 `flags`，每项含 `flag`、`orderIndex`、可选 `description`、`scoreMode`、
`fixedScore`、`maxAttempts`、`answerType`、`customName` 和可选 `attachment.remoteUrl`。
动态容器使用 `flagTemplate`，不要把运行时 Flag 放入 flags。附件只支持绝对 http/https
远程 URL，服务端会下载并深复制；本接口不支持 multipart 文件上传。

创建单题 `POST /exercises` 使用同一字段但没有 `externalId`；更新 `PUT` 是全量替换。
删除也需要 Idempotency-Key，并返回异步 operation。

## AI 操作顺序

1. 本地生成并通过 reviewer 的题目包和 JSON，确认镜像已 Ready。
2. 从环境变量读取 Token，提交批量导入并保存返回的 operation ID。
3. `GET /operations/{id}` 轮询；成功后记录 result 中的题目 ID 与 externalId 映射。
4. 失败时读取 `errorCode/errorDetail/traceId`，修正文档或请求后使用新 key。
5. 完成后撤销短期 Token。

命令行客户端：`python scripts/ctf_client.py exercise import --file exercise-import.json`；
也可使用 curl。客户端自动轮询且不会打印 Token。

## 错误

`401` Token 无效，`403` scope/resource grant 不足，`404` 资源不可见，`409` 幂等冲突，
`422` 字段或业务校验失败，`429` 配额限制，`503` 依赖不可用。错误体为
`application/problem+json`，客户端按稳定 `code` 分支。
