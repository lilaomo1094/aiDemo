# 版本 v0.8.0 配置说明

本目录由 `scripts/init_version.py` 自动生成。

## 需要您手动补充的内容

1. **需求文档**
   - 替换 `requirement.md` 为您的 Word 需求转译后的 Markdown 文件
   - 也可将多个 Word 文档转义后放在 `requirements/` 目录并合并

2. **版本配置 `config.json`**
   - 在 `sources.swagger` 中填写 Swagger / OpenAPI 文件路径或 URL
   - 在 `sources.frontend_repo` / `sources.backend_repo` 中填写代码仓库地址或本地路径
   - 在 `environment_overrides` 中覆盖数据库、网络、API/UI 地址

3. **接口文档**
   - 推荐将 Swagger 文件（`.json` / `.yaml`）放入本版本目录
   - 修改 `config.json → sources.swagger.file_path` 指向该文件

## 执行测试

```bash
python run_automation.py --environment v0.8.0 --version v0.8.0 --manage run-version
```

或完整运行：

```bash
python run_automation.py --environment v0.8.0 --version v0.8.0
```
