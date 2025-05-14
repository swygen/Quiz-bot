from aiohttp import web

async def keep_alive():
    app = web.Application()
    app.add_routes([web.get("/", lambda request: web.Response(text="Bot is running"))])
    runner = web.AppRunner(app)
    await runner.setup()
    return runner
