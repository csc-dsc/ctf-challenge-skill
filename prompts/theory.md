# Theory 题型出题指南

## 题型定义

Theory：理论知识题，支持单选、多选、判断题。通过 JSON 文件导入平台。

适用：安全基础、网络知识、密码学基础、法律法规、各类知识考核。

## 目录结构

```
theory-topic/
├── README.md
├── theory-bank.json        # 题库文件
├── theory-paper.json       # 试卷文件
└── answers.md              # 标准答案（内部资料）
```

## 题库 JSON 格式

```json
{
  "questions": [
    {
      "type": "SingleChoice",
      "bankName": "Web基础-单选",
      "title": "HTTP 默认端口是？",
      "content": "请选择 HTTP 协议默认端口。",
      "options": ["21", "22", "80", "443"],
      "answerIndexes": [2]
    },
    {
      "type": "MultipleChoice",
      "bankName": "Web基础-多选",
      "title": "以下哪些属于 HTTP 请求方法？",
      "content": "多选题必须完全一致才得分。",
      "options": ["GET", "POST", "SELECT", "PUT"],
      "answerIndexes": [0, 1, 3]
    },
    {
      "type": "TrueFalse",
      "bankName": "Web基础-判断",
      "title": "HTTPS 一定使用 443 端口。",
      "content": "端口可以自定义，443 只是默认值。",
      "options": ["正确", "错误"],
      "answerIndexes": [1]
    }
  ]
}
```

## 字段规则（严格）

| 字段 | 规则 |
|------|------|
| `type` | `SingleChoice` / `MultipleChoice` / `TrueFalse` |
| `bankName` | 题库名称，最长 128 字符 |
| `title` | 必填，题目题干 |
| `content` | 解析、补充材料或 Markdown 内容 |
| `options` | 单选/多选至少 2 个；判断固定 2 个 |
| `answerIndexes` | 必填、去重、**从 0 开始** |

**关键约束**：
- 单选和判断只有 1 个正确下标
- 多选可以有多个正确下标
- 多选必须**完全一致**才得分（选多/选少/选错都不得分）
- 每题分值 > 0

## 试卷 JSON 格式

```json
{
  "title": "Web 安全基础测验",
  "description": "共 10 题，提交后不可修改。每题 5 分，满分 50 分。",
  "questions": [
    {
      "type": "SingleChoice",
      "bankName": "Web基础-单选",
      "title": "HTTP 默认端口是？",
      "content": "请选择 HTTP 协议默认端口。",
      "options": ["21", "22", "80", "443"],
      "answerIndexes": [2],
      "score": 5,
      "order": 1
    },
    {
      "type": "MultipleChoice",
      "bankName": "Web基础-多选",
      "title": "以下哪些属于 HTTP 请求方法？",
      "content": "多选题必须完全一致才得分。",
      "options": ["GET", "POST", "SELECT", "PUT"],
      "answerIndexes": [0, 1, 3],
      "score": 5,
      "order": 2
    },
    {
      "type": "TrueFalse",
      "bankName": "Web基础-判断",
      "title": "HTTPS 一定使用 443 端口。",
      "content": "端口可以自定义。",
      "options": ["正确", "错误"],
      "answerIndexes": [1],
      "score": 5,
      "order": 3
    }
  ]
}
```

试卷中的 `questions` 比题库多了：
- `score`：每题分值
- `order`：题目序号

## 出题规范

### 单选题
- 4 个选项最标准
- 干扰项要有一定合理性（不能明显荒谬）
- 正确答案分布均匀（不要全是 C）
- 题干清晰，无歧义

### 多选题
- 至少 4 个选项，2-3 个正确答案
- 明确告知"多选完全一致才得分"
- 不要出现"以上都是"这种模糊选项

### 判断题
- 选项固定为 `["正确", "错误"]`
- 命题必须明确无误（或有公认答案）
- answerIndexes: [0] 表示"正确"，[1] 表示"错误"

### 通用规则
- 每套试卷的题目不要全部来自同一个知识点
- 难度递进：简单题在前，难题在后
- `content` 可以放详细解析（学生交卷后可以看到）
- bankName 用于平台内分类管理，建议格式：`分类-子类-题型`

## 导入和验证流程

1. 管理员进入 `管理 → 理论题库`
2. 点击 "JSON 导入"
3. 选择文件或粘贴 JSON
4. 预览三种题型和答案
5. 创建 Theory 比赛
6. 进入比赛后台 "理论试卷"
7. 从题库选择或随机抽题
8. 设置每题分值
9. 保存试卷
10. 发放试卷

发放后验证：
- 学生可保存草稿
- 刷新后草稿不丢失
- 最终提交后禁止二次修改
- 自动判分
- 理论榜单正确

## 自检步骤

1. JSON 文件用 `python3 -m json.tool theory-bank.json` 验证格式
2. 逐题检查 `answerIndexes` 从 0 开始
3. 单选/判断题只有一个答案下标
4. 所有 `type` 值拼写正确（区分大小写）
5. 判断的 `options` 固定为 `["正确", "错误"]`
6. 每道题至少 2 个 `options`
7. 每题 `score > 0`
8. 在干净环境中导入平台测试：草稿→提交→判分→榜单

## 常见错误及避免

| 错误 | 正确做法 |
|------|----------|
| `answerIndexes: [1]` 但 index 1 是第 2 个选项 | 从 0 开始计数：第 1 个 = 0, 第 2 个 = 1 |
| `"type": "singlechoice"` | 大写驼峰：`"SingleChoice"` |
| 判断的 options 写了 3 个 | 固定 `["正确", "错误"]` |
| 多选只有 1 个正确答案 | 多选至少 2 个正确答案，否则改成单选 |
| `"answerIndexes": [0, 0]` | 去重：`"answerIndexes": [0]` |
