## Порівняння: before_baseline, after_baseline

### Загальні метрики

| Метрика | before_baseline | after_baseline | Зміна (перший → останній) |
|---|---|---|---|
| Запитів | 4617 | 4632 | ≈0% |
| RPS | 25.7 | 25.8 | ≈0% |
| Error rate, % | 0.0 | 0.0 | - |
| avg, мс | 12.9 | 11.1 | -14% ✅ |
| p50, мс | 11.0 | 9.0 | -18% ✅ |
| p95, мс | 23.0 | 18.0 | -22% ✅ |
| p99, мс | 88.0 | 100.0 | +14% ⚠️ |
| CPU app (сер.), % | 20.7 | 18.4 | -11% ✅ |
| CPU БД (сер.), % | 0.0 | 0.0 | - |
| RAM app (сер.), МБ | 94.1 | 99.9 | +6% ⚠️ |

### По ендпоінтах

| Ендпоінт | avg/p95, мс (before_baseline) | avg/p95, мс (after_baseline) |
|---|---|---|
| GET / | 3 / 5 | 3 / 4 |
| GET /login | 3 / 6 | 3 / 5 |
| GET /student/grades | 13 / 23 | 9 / 16 |
| GET /student/home | 14 / 24 | 12 / 20 |
| GET /student/schedule | 11 / 19 | 10 / 17 |
| GET /teacher/home | 15 / 26 | 13 / 21 |
| GET /teacher/schedule | 9 / 19 | 8 / 13 |
| GET /users/me | 8 / 13 | 6 / 11 |
| POST /journal | 16 / 26 | 13 / 22 |
| POST /login | 230 / 250 | 229 / 240 |
