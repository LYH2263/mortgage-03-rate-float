# 15-mortgage（房贷月供）

Mortgage — 等额本息月供与逐期本金利息拆分

## 启动

```bash
docker compose up --build
```

| 入口 | 地址 |
| --- | --- |
| 前端 | http://localhost:4400 |
| API | http://localhost:9400 |

## 主链

贷额期限利率 → 等额本息还款表 → 利息合计

## 利率浮动（rate_float）

- 利率页按贷款维护浮动事件：生效期序号（>1 且 ≤ 总期数）、新年利率（≥0）、启用状态与备注；同一贷款两条启用事件生效期相同会被拒绝并点名冲突双方。
- 测算仍走等额本息：生效期之前各期用原年利率，自生效期起按余额与新年利率重算剩余月供；回包标注切换期、切换前后利率、切换前后月供与分段利息。
- 未挂启用事件时与单利率等额本息完全一致；`persist=false` 不落库；停用事件只影响后续测算，已落库记录仍保留切换标注。

| 接口 | 说明 |
| --- | --- |
| `GET /api/loans/{id}/rate-floats` | 事件列表 |
| `POST /api/loans/{id}/rate-floats` | 创建事件 |
| `PUT /api/rate-floats/{id}` | 更新事件 |
| `POST /api/rate-floats/{id}/disable` | 停用事件 |

## 技术栈

Python 3.12 + FastAPI + SQLite；Vue 3 + Vite + Nginx。
