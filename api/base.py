from tenacity import retry, stop_after_attempt, wait_exponential

class BaseAPI:
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _request(self, url, **kwargs):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()