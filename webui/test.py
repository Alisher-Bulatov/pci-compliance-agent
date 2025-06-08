import httpx
import asyncio


async def test_mock_full():
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "GET", "http://localhost:8000/ask_mock_full"
        ) as response:
            async for line in response.aiter_lines():
                if line.strip():
                    print("📥", line)


if __name__ == "__main__":
    asyncio.run(test_mock_full())
