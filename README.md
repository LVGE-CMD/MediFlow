# MediFlow 医疗预约微服务自动化测试

![tests](https://github.com/LVGE-CMD/MediFlow/actions/workflows/tests.yml/badge.svg)

MediFlow 是一个面向医疗预约场景的微服务项目，用于练习接口自动化、数据库断言、契约测试、并发、幂等、消息队列、UI 自动化和 CI。

## 技术栈

- Python 3.12、FastAPI、Uvicorn
- Pytest、Requests、JSON Schema、Allure
- SQLite、Redis、RabbitMQ
- Playwright、pytest-playwright
- Docker、Docker Compose、GitHub Actions

## 架构

```text
gateway:8080 ──> schedule:8001
appointment:8002 ──> SQLite
payment:8003 ──> appointment:8002
payment:8003 ──> RabbitMQ ──> notification
appointment:8002 ──> Redis（分布式锁）
notification ──> Redis（重复消费去重）
```

## 服务与端口

| 服务 | 端口 | 说明 |
|---|---:|---|
| schedule | 8001 | 排班健康检查 |
| appointment | 8002 | 预约创建、查询、取消 |
| payment | 8003 | 支付、幂等、发消息 |
| gateway | 8080 | 健康检查聚合 |
| Redis | 6379 | 锁、通知去重 |
| RabbitMQ | 5672 / 15672 | 消息队列、管理界面 |
| notification | 无 | 消费支付成功消息 |

## 快速开始

前置：Docker Desktop 已启动。

```powershell
docker compose up -d --build
docker compose ps
```

健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:8001/health
Invoke-RestMethod http://127.0.0.1:8002/health
Invoke-RestMethod http://127.0.0.1:8003/health
Invoke-RestMethod http://127.0.0.1:8080/health
```

## 主要接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| POST | `/appointments` | 创建预约 |
| GET | `/appointments/{id}` | 按 ID 查询 |
| GET | `/appointments` | 预约列表 |
| PATCH | `/appointments/{id}/cancel` | 取消预约 |
| POST | `/payments` | 创建支付 |
| GET | `/` | 预约页面（appointment） |

创建预约：

```powershell
$body = @{
    doctor_id = 7
    slot = "2026-12-01 09:00"
    patient_name = "Demo"
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8002/appointments `
    -ContentType "application/json" `
    -Body $body
```

支付：

```powershell
$payment = @{
    appointment_id = 1001
    amount = 49900
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8003/payments `
    -ContentType "application/json" `
    -Body $payment
```

## 测试

当前 14 条：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

覆盖：

| 类型 | 内容 |
|---|---|
| 健康检查 | appointment `/health` |
| 创建 | 201、字段回显、默认状态 |
| 查询 | 200、404 |
| 取消 | 200、重复取消 409 |
| 参数化 | 非法 ID：422/404 |
| 数据库 | POST 后直接查 SQLite，finally 清理 |
| 契约 | JSON Schema 校验字段、类型、枚举 |
| 并发 | 10 线程抢同一时段，1 个 201、9 个 409 |
| UI | Playwright 填表、提交、断言 201 |

`conftest.py` 会自动启动 appointment 服务、分配空闲端口、测试结束关闭。

运行 UI：

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m pytest tests/test_ui.py -v
```

运行并发：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_concurrency.py -v
```

## Allure

```powershell
.\.venv\Scripts\python.exe -m pytest --alluredir=allure-results -q
npm install --prefix .tools allure-commandline
.\.tools\node_modules\.bin\allure.cmd generate allure-results -o allure-report --clean
.\.tools\node_modules\.bin\allure.cmd open allure-report
```

## CI

GitHub Actions 在每次 push / pull_request 时：

```text
启动 Redis
安装 Python 依赖
安装 Chromium
运行 pytest
生成 Allure
上传 allure-report
```

Workflow：

```text
.github/workflows/tests.yml
```

## 性能 smoke

Locust，20 并发、20 秒：

```powershell
.\.venv\Scripts\python.exe -m locust -f locustfile.py `
    --headless -u 20 -r 5 -t 20s `
    --host http://127.0.0.1:8002 --only-summary
```

本机结果：

```text
800 请求
0 失败
平均 235 ms
P50 81 ms
P95 1200 ms
41.43 req/s
```

仅用于 smoke，不代表生产容量。

## 目录结构

```text
MediFlow
├── services
│   ├── appointment
│   ├── gateway
│   ├── notification
│   ├── payment
│   ├── schedule
│   └── common
├── tests
│   ├── conftest.py
│   ├── db_helpers.py
│   ├── schemas.py
│   ├── test_appointment.py
│   ├── test_concurrency.py
│   ├── test_health.py
│   └── test_ui.py
├── Dockerfile
├── docker-compose.yml
├── locustfile.py
├── requirements.txt
└── .github/workflows/tests.yml
```

## 已知限制

- payment 和幂等键在内存，重启丢失
- notification 只打印，不真正发送短信/邮件
- 没有 outbox，RabbitMQ 发送失败时消息会丢
- gateway 只聚合 health，没有代理业务接口
- 取消预约不发送消息
- 性能数据仅本机 smoke

## 作者

吕品邑  
GitHub：https://github.com/LVGE-CMD/MediFlow
