"""Ступінчатий профіль навантаження для пошуку точки деградації.

Запуск (разом із основним сценарієм):
    locust -f loadtest/locustfile.py,loadtest/step_shape.py --headless --host http://127.0.0.1:8000

Кожен ступінь триває 60 с: 10 -> 50 -> 100 -> 200 -> 300 -> 400 -> 500 користувачів.
"""

from locust import LoadTestShape


class StepLoadShape(LoadTestShape):
    # (час завершення ступеня, с; кількість користувачів; швидкість спавну, користувачів/с)
    stages = [
        (60, 10, 5),
        (120, 50, 10),
        (180, 100, 10),
        (240, 200, 20),
        (300, 300, 20),
        (360, 400, 20),
        (420, 500, 20),
    ]

    def tick(self):
        run_time = self.get_run_time()
        for end, users, spawn_rate in self.stages:
            if run_time < end:
                return users, spawn_rate
        return None
