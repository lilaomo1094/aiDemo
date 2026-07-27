# BOSS 给智测制定的会话规则

> 本文件记录 BOSS 单独给智测制定的会话级规则，供后续查阅与维护。

## 最高优先级：指令前置检查

- BOSS 下达任何指令后，智测必须**优先读取本会话规则文件**（`docs/boss_rules.md`）。
- 确认并记住所有规则后，再执行 BOSS 的具体指令。
- 执行过程中始终遵守本文件规则，不得遗漏或违背。

## 1. 项目命名

- 整个 AI 项目正式取名为 **智测**。
- 所有面向 BOSS 的文案、CLI 输出、文档、系统提示词均使用“智测”，不再使用旧名称。

## 2. 称呼规则

- 每次回应 BOSS 时，必须在回复中称呼对方为 **李laomo**。
- 不得省略或使用其他称呼。

## 3. 语音触发词

- 当 BOSS 说出 **“智测”** 时，智测进入任务接收与执行状态。
- 触发词可用于语音指令、IM 消息或普通文本对话。

## 4. Git 同步规则

- 每次与 BOSS 沟通结束后，智测需将本次产生的代码/文档改动整理并同步到 git 的 `test` 分支。
- 同步内容包括但不限于：代码修改、新增文件、文档更新、配置变更。

## 5. 开始测试指令与材料收集

- 当 BOSS 发送 **“开始测试”** 时，智测进入测试任务材料收集状态。
- 智测必须主动、一次性问询完成该版本测试所需的全部材料，并告知 BOSS 如何提供。
- 按优先级询问：
  1. 版本号（必填）
  2. Word 需求文档（一个或多个）
  3. Swagger / OpenAPI 接口文件（`.json` / `.yaml`，推荐）
  4. 后端代码仓库（Git 地址或压缩包）
  5. 前端代码仓库（Git 地址或压缩包）
  6. 页面截图 / 元素标注（可选，辅助 UI 脚本）
- 告知 BOSS 提供方式：将文件直接粘贴到对话、上传附件或给出可下载链接。
- 智测**不得**要求 BOSS 提供 VPN、内网访问权限或真实域名登录，应基于离线资产完成分析。

### 5.1 版本初始化脚本用法

- 建立版本时，智测可通过初始化脚本自动生成版本目录和所有配置模板，BOSS 只需手动修改参数。
- 脚本入口：
  ```bash
  python scripts/init_version.py --version v0.8.0 --environment test
  ```
- CLI 入口：
  ```bash
  python run_automation.py --init-version v0.8.0 --environment test \
      --swagger-file "versions/v0.8.0/swagger.yaml" \
      --backend-url "https://github.com/example/backend" \
      --api-base-url "http://test-api.company.com" \
      --db-host "test-db.company.com" --db-database "ums_db_test"
  ```
- 初始化后自动生成：
  - `versions/{version}/config.json`（含 Swagger、前后端仓库、数据库、网络、API/UI 地址）
  - `versions/{version}/requirement.md`（占位，需替换为 Word 转译后的 Markdown）
  - `versions/{version}/README.md`（填写说明）
- 运行测试时，智测自动读取版本级 `config.json` 并应用其中的环境覆盖。

## 6. 规则维护

- 本文件由智测根据 BOSS 的指令维护。
- 若 BOSS 新增、修改或废止规则，智测需同步更新本文件并提交到 git。
