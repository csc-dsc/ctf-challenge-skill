# {题目名称}

- **赛制**：{CTF / AWDP / 理论 / 培训}
- **分类**：{Web / Pwn / Forensics / Crypto / Reverse / Misc / IR}
- **难度**：{Easy / Medium / Hard}
- **初始分**：{500}
- **题目类型**：{StaticAttachment / StaticContainer / DynamicAttachment / DynamicContainer}
- **环境类型**：{None / Docker / WindowsVM}
- **镜像**：{完整 Registry 地址或 VM 模板文件名}
- **容器内部端口**：{80}
- **建议资源**：CPU {2} / 内存 {256 MiB} / 存储 {512 MiB}
- **网络模式**：{Open / Isolated}
- **Flag 规则**：{静态 / 动态 GZCTF_FLAG}

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
```

## 正确解法验证
1. {步骤1}
2. {步骤2}
3. {获得 Flag}

## 清理方法
```bash
docker compose -f docker/docker-compose.test.yml down -v
docker rmi {image-name}:{tag}
```
