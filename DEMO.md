# MediFlow 3 分钟演示脚本

## 0. 开场（20 秒）

打开 GitHub：

```text
https://github.com/LVGE-CMD/MediFlow
```

说：

> 这是一个医疗预约微服务项目，包含预约、支付、消息通知，以及接口、数据库、契约、并发、UI、CI 六层测试。

---

## 1. 架构（30 秒）

打开 README 的架构图：

```text
gateway → schedule
appointment → SQLite
payment → appointment
payment → RabbitMQ → notification
appointment → Redis
notification → Redis
```

说：

> 五个服务用 Docker Compose 编排，Redis 做分布式锁和通知去重，RabbitMQ 做支付成功事件。

---

## 2. 启动（30 秒）

```powershell
Set-Location D:\Projects\MediFlow
docker compose up -d --build
docker compose ps
```

说：

> 一条命令启动全部容器，SQLite 数据挂载到宿主机。

---

## 3. 创建预约（30 秒）

```powershell
$body = @{
    doctor_id = 7
    slot = "2026-12-10 09:00"
    patient_name = "Demo"
} | ConvertTo-Json

$created = Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8002/appointments `
    -ContentType "application/json" `
    -Body $body

$created
```

说：

> 创建前先抢 Redis 锁，数据库还有部分唯一索引兜底。

---

## 4. 支付（30 秒）

```powershell
$payment = @{
    appointment_id = $created.appointment_id
    amount = 49900
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri http://127.0.0.1:8003/payments `
    -ContentType "application/json" `
    -Headers @{ "Idempotency-Key" = "demo-001" } `
    -Body $payment
```

说：

> payment 先查 appointment 状态，再创建支付；同一个 Idempotency-Key 重复提交不会重复创建。

---

## 5. 通知（20 秒）

```powershell
docker compose logs notification --tail 20
```

说：

> payment 发布 payment.paid，notification 异步消费；Redis 按 payment_id 去重。

---

## 6. 测试与 CI（30 秒）

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

说：

> 14 条测试，覆盖 CRUD、404/409/422、数据库落库、JSON Schema、10 线程并发和 Playwright UI。

打开 Actions：

```text
https://github.com/LVGE-CMD/MediFlow/actions
```

说：

> 每次 push 自动跑测试并上传 Allure 报告。

---

## 7. 收尾（10 秒）

说：

> 项目当前是测试项目，不是生产系统；支付和幂等数据在内存，消息没有 outbox，这些是后续可以继续完善的点。
