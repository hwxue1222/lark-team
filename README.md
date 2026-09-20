## Lark 机器人中控服务（FastAPI + lark-oapi + Kimi）

功能：

- 通过 WebSocket 长连接接收 Lark 消息事件（`im.message.receive_v1`）
- 调用 Kimi API 做意图识别与回复生成，并直接回消息（私聊/群聊）
- 处理卡片按钮回调（`card.action.trigger`）：返回 toast 提示“直接回复模式无需确认”
- 提供 `/health` 与基础日志（用于自检与运维）

### 1) 配置

#### 1.1 创建飞书自建应用

在 `https://open.larksuite.com/` 创建「自建应用」（Internal App / 自建应用）。如果你用的是飞书中国版（Feishu），域名与后台入口是 `https://open.feishu.cn/`。

在应用后台你需要拿到并配置：

- **APP_ID / APP_SECRET**：用于启动长连接与调用开放接口（发消息、发卡片）

同时在「权限管理」中开通机器人发消息所需权限，并在「事件订阅」中：

- 接收方式选择 **长连接（WebSocket）**（无需回调 URL）
- 订阅事件：

- `im.message.receive_v1`
- `card.action.trigger`

复制环境变量样例：

```bash
cp .env.example .env
```

如果终端无法执行 `cp`，可以用 Python 脚本生成：

```bash
python scripts/init_env.py
```

如果你发现 `.env` 看起来填写了但脚本仍提示缺少变量，可以用交互式脚本重新写入（不会回显密钥）：

```bash
python scripts/configure_env.py
```

需要在 `.env` 中填写：

- `LARK_APP_ID`
- `LARK_APP_SECRET`
- `LARK_DOMAIN`（Lark: `https://open.larksuite.com`；Feishu: `https://open.feishu.cn`）
- `KIMI_API_KEY`
- `KIMI_MODEL`（例如 `k3`）

可选：

- `KIMI_BASE_URL`（默认 `https://api.kimi.ai/coding/v1`）
- `HTTP_PORT`（默认 8000）

如果你私聊/群聊发消息后终端完全没有任何新增日志，说明事件没有下发，请优先检查：

- 是否订阅并发布生效了 `im.message.receive_v1`
- `LARK_DOMAIN` 是否与你的租户匹配（Lark vs Feishu）

可以先运行鉴权自检脚本（不打印 key）：

```bash
source .venv/bin/activate
python scripts/test_moonshot_auth.py
```

如果你的 `.env` 里误用了中文引号（例如 `MODEL_NAME=“xxx”`），先修复成英文引号/不带引号：

```bash
source .venv/bin/activate
python scripts/fix_env_quotes.py
```

### 2) 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/start.py
```

启动成功后会打印：`长连接已建立`。

健康检查：`http://127.0.0.1:8000/health`

### 2.1) 换电脑（迁移到新机器）

迁移步骤见：[`docs/MOVE_TO_NEW_MACHINE.md`](docs/MOVE_TO_NEW_MACHINE.md)

### 3) Local Agent（控制本机执行简单动作）

Local Agent 是跑在你自己电脑上的本地服务，用于执行“打开网页”等本机动作。

#### 3.1 启动 Local Agent

先在 `.env` 里设置：

- `LOCAL_AGENT_TOKEN`：必须设置（相当于本机执行口令）
- `LOCAL_AGENT_ALLOWED_DOMAINS`：建议设置域名白名单（逗号分隔）

启动：

```bash
source .venv/bin/activate
python scripts/start_local_agent.py
```

健康检查：`http://127.0.0.1:9100/health`

#### 3.2 让中控转发本地指令

在 `.env` 里开启：

- `LOCAL_AGENT_ENABLED=true`
- `LOCAL_AGENT_URL=http://127.0.0.1:9100`
- `LOCAL_AGENT_TOKEN=...`（与 Local Agent 一致）

可选：

- `LOCAL_AGENT_OPERATOR_IDS`：允许执行本地指令的 sender_id（逗号分隔）。留空表示不限制。

然后重启中控：

```bash
python scripts/start.py
```

在 Lark 里发送以下格式的消息即可触发本机动作：

- `本地 打开 https://bby.today/admin`
- `local open https://bby.today/admin`

### 4) Accountant Agent（自动创建会计分录）

Accountant Agent 会通过 bbyaccounting 的 API（cookie session）创建分录。为了安全，默认走“确认卡片”二次确认。

#### 4.1 配置

在 `.env` 里设置：

- `ACCOUNTANT_ENABLED=true`
- `BBY_ACCOUNTING_BASE_URL=https://bbyaccounting.com`
- `BBY_ACCOUNTING_EMAIL=...`
- `BBY_ACCOUNTING_PASSWORD=...`
- `BBY_ACCOUNTING_ORG_ID=...`（可选；如果不填，中控会在每次分录前先询问你选择哪个公司）

可选：

- `ACCOUNTANT_OPERATOR_IDS`：允许发起/确认分录的 sender_id（逗号分隔）。留空表示不限制。

重启中控：

```bash
python scripts/start.py
```

#### 4.2 指令格式（JSON）

在 Lark 里发送：

```text
分录 {"entryDate":"2026-09-20","currency":"SGD","fxRate":1,"memo":"Office expense","lines":[{"account":"6000","debit":500,"desc":"Office"},{"account":"1000","credit":500,"desc":"Cash"}]}
```

或：

```text
je {"memo":"Office expense","lines":[{"account":"6000","debit":500},{"account":"1000","credit":500}]}
```

系统会返回一张“会计分录确认”卡片，点“确认执行”后才会真正调用 `POST /api/journals/post`。

如果科目不匹配，系统会弹出“选择科目”的卡片，给出最接近的科目供你点击选择，然后再回到确认卡片。

提示：如果你习惯用中文口述科目（如“现金”），系统会自动按常见别名（cash/bank/due to director 等）做英文科目匹配与推荐。

### 2.1 事件自检（只验证是否收到消息事件）

```bash
source .venv/bin/activate
python -u scripts/doctor_events.py
```
