import unittest
import asyncio

class AsyncTestCase(unittest.TestCase):
    def run(self, result=None):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._async_run(result))

    async def _async_run(self, result=None):
        super().run(result)