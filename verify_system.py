import asyncio
import httpx
from app.main import app


async def main():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
        # Root check
        resp = await client.get("/")
        print("Root response:", resp.status_code, resp.json())

        # Health check
        resp_health = await client.get("/health")
        print("Health check:", resp_health.status_code, resp_health.json())

        # Services check
        resp_svc = await client.get("/api/v1/services")
        print("Services count:", len(resp_svc.json()))
        print("First service:", resp_svc.json()[0]["title"], f"({resp_svc.json()[0]['kpi_points']} ball)")


if __name__ == "__main__":
    asyncio.run(main())
