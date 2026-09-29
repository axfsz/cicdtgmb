# ugtesta-tgmb

Telegram 群内 Jenkins 构建面板机器人。

## 功能

- 群内 `/menu` 打开 Jenkins 构建面板
- 点击服务按钮直接触发 Jenkins 构建
- 机器人会在群里通知：谁点击了发布、触发哪个服务、触发状态、HTTP 状态、队列地址、构建地址
- 使用 Jenkins `ugadmin API Token + Jenkins-Crumb + Cookie + buildWithParameters`
- 每个服务的 Job 远程构建身份令牌规则：`job名-token`
- 默认构建参数：
  - `BRANCH_NAME=main`
  - `K8S_NAMESPACE=testa`
  - `PUSH_LATEST=true`
  - `RUN_GO_TEST=false`

## 服务列表

| 类型 | Jenkins Job |
|---|---|
| rpc | activity-rpc-testa |
| rpc | admin-rpc-testa |
| rpc | ai-rpc-testa |
| rpc | finance-rpc-testa |
| rpc | game-rpc-testa |
| rpc | member-rpc-testa |
| rpc | notification-rpc-testa |
| rpc | payment-rpc-testa |
| rpc | report-rpc-testa |
| rpc | risk-rpc-testa |
| rpc | tenant-rpc-testa |
| bff | bff-admin-testa |
| bff | bff-merchant-testa |
| bff | bff-player-testa |
| standalone | statistics-testa |

## 部署

```bash
unzip ugtesta-tgmb-v2.zip
cd ugtesta-tgmb-v2
cp .env.example .env
vim .env
```

`.env` 至少填写：

```bash
TG_BOT_TOKEN=你的Telegram机器人Token
TG_ALLOWED_CHAT_ID=-1003919548725
JENKINS_API_TOKEN=你的ugadmin Jenkins API Token
```

启动：

```bash
docker compose build
docker compose up -d
docker logs -f ugtesta-tgmb
```

## Telegram 使用

在群里发送：

```text
/menu
```

然后点击服务按钮即可发布。

## 触发通知示例

点击后机器人会先发送：

```text
🚀 Jenkins 构建触发中
触发人: 某个群成员
服务: activity-rpc-testa
类型: rpc
分支: main
命名空间: testa
触发状态: ⏳ 请求 Jenkins 中
```

Jenkins 返回后机器人会继续发送：

```text
📣 Jenkins 构建触发结果
触发人: 某个群成员
服务: activity-rpc-testa
类型: rpc
分支: main
命名空间: testa
触发状态: ✅ 已成功加入 Jenkins 构建队列
HTTP状态: 201
队列地址: https://ugjekins.ugmid888.com/queue/item/xx/
构建地址: https://ugjekins.ugmid888.com/job/activity-rpc-testa/xx/
```

## 安全控制

默认只限制群 ID，不限制具体用户。也就是授权群里的成员都可以触发。

如需限制只有指定 Telegram 用户可以触发，在 `.env` 里配置：

```bash
ALLOWED_USER_IDS=123456789,987654321
```

用户 ID 可通过点击后机器人日志或 Telegram API 获取。

## 注意

你之前已经在聊天中暴露过 Telegram Bot Token 和 Jenkins API Token。正式使用前建议重新生成：

- Telegram：BotFather 重新生成 Bot Token
- Jenkins：`ugadmin -> Security -> API Token` 重新生成 API Token

然后更新 `.env` 并重启容器：

```bash
docker compose up -d --build
```
# cicdtgmb
