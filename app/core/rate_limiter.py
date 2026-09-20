import time
from collections import defaultdict
from typing import Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.config import settings


class IPRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    IP asosidagi so'rovlar tezligini nazorat qiluvchi Sliding Window Rate Limiter.
    Brute-force, botlar va DDoS hujumlariga qarshi samarali himoya.
    """

    def __init__(self, app):
        super().__init__(app)
        # {ip: [timestamps]}
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.auth_requests: Dict[str, List[float]] = defaultdict(list)
        self.last_cleanup = time.time()

        # Cheklovlar (daqiqasiga)
        self.AUTH_LIMIT = 25     # Kirish va validatsiya uchun 25 ta/daqiqa
        self.GENERAL_LIMIT = 150 # Boshqa API endpointlar uchun 150 ta/daqiqa
        self.WINDOW_SECONDS = 60

    def _get_client_ip(self, request: Request) -> str:
        """Haqiqiy mijoz IP manzilini Cloudflare yoki Nginx proksi orqali aniqlaydi."""
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        return request.client.host if request.client else "127.0.0.1"

    def _cleanup_old_records(self, now: float):
        """Xotira o'sib ketishining oldini olish uchun 60 soniyadan oshgan yozuvlarni tozalash."""
        if now - self.last_cleanup > 60:
            threshold = now - self.WINDOW_SECONDS
            for storage in [self.requests, self.auth_requests]:
                keys_to_delete = []
                for ip, timestamps in storage.items():
                    storage[ip] = [t for t in timestamps if t > threshold]
                    if not storage[ip]:
                        keys_to_delete.append(ip)
                for k in keys_to_delete:
                    del storage[k]
            self.last_cleanup = now

    async def dispatch(self, request: Request, call_next):
        # Test rejimida cheklovni chetlab o'tish
        if getattr(settings, "TESTING", False):
            return await call_next(request)

        path = request.url.path

        # Statik fayllar va monitoring so'rovlarini hisobga olmaslik
        if (
            path.startswith("/static")
            or path.startswith("/uploads")
            or path == "/health"
            or path.startswith("/docs")
            or path.startswith("/redoc")
            or path.startswith("/openapi.json")
        ):
            return await call_next(request)

        now = time.time()
        self._cleanup_old_records(now)

        client_ip = self._get_client_ip(request)
        threshold = now - self.WINDOW_SECONDS

        # Autentifikatsiya so'rovlari uchun qat'iy cheklov
        is_auth_route = path in [
            "/api/v1/auth/login",
            "/api/v1/auth/student-login",
            "/api/v1/auth/validate-phone"
        ]

        storage = self.auth_requests if is_auth_route else self.requests
        limit = self.AUTH_LIMIT if is_auth_route else self.GENERAL_LIMIT

        # Sliding window filtri
        user_timestamps = [t for t in storage[client_ip] if t > threshold]
        storage[client_ip] = user_timestamps

        if len(user_timestamps) >= limit:
            retry_after = int(self.WINDOW_SECONDS - (now - user_timestamps[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "So'rovlar soni me'yordan oshdi. Xavfsizlik nuqtai nazaridan iltimos, bir daqiqadan so'ng qayta urinib ko'ring."
                },
                headers={"Retry-After": str(max(1, retry_after))}
            )

        storage[client_ip].append(now)
        return await call_next(request)
