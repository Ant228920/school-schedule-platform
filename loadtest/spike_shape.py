"""Профіль «раптовий стрибок» для пошуку точки зламу й перевірки відновлення.

    locust -f loadtest/locustfile.py,loadtest/spike_shape.py,loadtest/soak_stats.py --headless --host http://127.0.0.1:8000

0-60 с: 30 користувачів (норма); 60-180 с: різкий стрибок до 400; 180-420 с: знову 30 (відновлення).
"""

from locust import LoadTestShape


class SpikeShape(LoadTestShape):
    # (час завершення етапу, с; користувачів; швидкість спавну, користувачів/с)
    stages = [
        (60, 30, 10),
        (180, 400, 100),
        (420, 30, 100),
    ]

    def tick(self):
        run_time = self.get_run_time()
        for end, users, spawn_rate in self.stages:
            if run_time < end:
                return users, spawn_rate
        return None
