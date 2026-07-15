# {题目名称}

## 题目概况

| 字段 | 值 |
|------|-----|
| 赛制 | {CTF / AWDP / 理论 / 培训} |
| 分类 | {Web / Pwn / Forensics / Crypto / Reverse / Misc / IR} |
| 难度 | {Easy / Medium / Hard} |
| 初始分 | {500} |
| 题目类型 | {StaticAttachment / StaticContainer / DynamicAttachment / DynamicContainer / AWDP} |
| 环境类型 | {None / Docker / WindowsVM} |
| 镜像 | {完整 Registry 地址或 VM 模板文件名} |
| 容器内部端口 | {80} |
| 建议资源 | CPU {2} / 内存 {256 MiB} / 存储 {512 MiB} |
| 网络模式 | {Open / Isolated} |
| Flag 规则 | {静态 / 动态 GZCTF_FLAG} |

<!-- AWDP 题型额外配置（必填） -->
<!-- 暴露端口：{容器内部端口，如 9999} -->
<!-- 攻击分：{50} / SLA分：{20} / 修补分：{100} / 异常扣分：{200} -->
<!-- 攻击阶段：{10}分钟 / 修补阶段：{10}分钟 / 总轮数：{20} -->
<!-- 每轮最大攻击：{3} -->

## 附件
- {附件文件名}
- SHA256: {sha256}

## 部署说明

```bash
# 构建
docker build -t {image-name}:{tag} docker/

# 本地测试
docker compose -f docker/docker-compose.test.yml up -d
curl -fsS http://127.0.0.1:18080/
docker compose -f docker/docker-compose.test.yml down

# 导出镜像
docker save {image-name}:{tag} -o {challenge-name}.tar
```

<!-- AWDP 题型部署说明 -->
<!-- 1. docker load -i {challenge-name}.tar -->
<!-- 2. docker tag ... 推送到平台 Registry -->
<!-- 3. 平台暴露端口填 {容器内部端口}（不是 80 也不是映射端口） -->
<!-- 4. Checker 和 Exp 脚本见下方，直接复制填入平台 -->

<!-- AWDP 题型：Checker 脚本 -->
<!-- ```python -->
<!-- ... -->
<!-- ``` -->

<!-- AWDP 题型：Exp 脚本 -->
<!-- ```python -->
<!-- ... -->
<!-- ``` -->

## 正确解法验证
1. {步骤1}
2. {步骤2}
3. {获得 Flag}

## 清理方法
```bash
docker compose -f docker/docker-compose.test.yml down -v
docker rmi {image-name}:{tag}
```
