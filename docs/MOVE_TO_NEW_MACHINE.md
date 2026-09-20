# 换电脑（迁移到新机器）

本项目已同步到 GitHub，但不会同步你的密钥与账号信息（`.env` 已在 `.gitignore` 中忽略）。

## 1) 在新电脑拉取代码

```bash
git clone https://github.com/hwxue1222/lark-team.git
cd lark-team
```

## 2) 安装 Python 与依赖

建议使用 `python3`。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) 配置环境变量（必须）

复制模板并填写真实值：

```bash
cp .env.example .env
```

最常用配置（按需启用）：

- Lark/Feishu：`LARK_APP_ID`、`LARK_APP_SECRET`、`LARK_DOMAIN`
- Kimi：`KIMI_API_KEY`（以及可选的 `KIMI_MODEL`/`KIMI_BASE_URL`）
- Accountant Agent：`ACCOUNTANT_ENABLED=true`、`BBY_ACCOUNTING_BASE_URL`、`BBY_ACCOUNTING_EMAIL`、`BBY_ACCOUNTING_PASSWORD`、`BBY_ACCOUNTING_ORG_ID`（可选）、`ACCOUNTANT_OPERATOR_IDS`（可选）

如果你不想手动编辑 `.env`，可用交互式脚本写入（不会回显密钥）：

```bash
source .venv/bin/activate
python scripts/configure_env.py
```

## 4) 启动中控

```bash
source .venv/bin/activate
python scripts/start.py
```

健康检查：`http://127.0.0.1:8000/health`

## 5) Local Agent（换电脑时要特别注意）

Local Agent 是在“本机”执行动作的服务，所以换电脑后必须在新电脑也启动它。

### 5.1 启动 Local Agent

```bash
source .venv/bin/activate
python scripts/start_local_agent.py
```

健康检查：`http://127.0.0.1:9100/health`

### 5.2 让中控转发本地指令

确保中控的 `.env` 配置与 Local Agent 一致：

- `LOCAL_AGENT_ENABLED=true`
- `LOCAL_AGENT_URL=http://127.0.0.1:9100`
- `LOCAL_AGENT_TOKEN=...`

然后重启中控 `python scripts/start.py`。

## 6) 常见问题

### 6.1 新电脑提示 `python: command not found`

用 `python3`，或直接使用虚拟环境里的解释器：

```bash
./.venv/bin/python scripts/start.py
```

### 6.2 机器人能连上但收不到消息事件

优先检查是否订阅并发布了 `im.message.receive_v1`，并确认 `LARK_DOMAIN` 与租户一致（Lark vs Feishu）。

可运行事件自检：

```bash
source .venv/bin/activate
python -u scripts/doctor_events.py
```

