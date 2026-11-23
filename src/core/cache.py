import json
import logging
import time

import redis

from src.core.config import settings

log = logging.getLogger(__name__)


class Cache:
    def __init__(self, url):
        self._c = (
            redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.25, socket_timeout=0.25, max_connections=64) if url else None
        )
        self._down_until = 0.0

    def _ok(self):
        return self._c is not None and time.monotonic() >= self._down_until

    def _fail(self, e):
        self._down_until = time.monotonic() + 5
        log.warning("Redis недоступний: %s", e)

    def get(self, key):
        if not self._ok():
            return None
        try:
            raw = self._c.get(key)
        except redis.RedisError as e:
            self._fail(e)
            return None
        return None if raw is None else json.loads(raw)

    def set(self, key, value, ttl):
        if self._ok():
            try:
                self._c.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
            except redis.RedisError as e:
                self._fail(e)

    def delete(self, *keys):
        if self._ok() and keys:
            try:
                self._c.delete(*keys)
            except redis.RedisError as e:
                self._fail(e)


cache = Cache(settings.REDIS_URL)
