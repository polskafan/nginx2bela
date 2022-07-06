import aiohttp
from aiohttp import web
import asyncio
import os
from dotenv import dotenv_values
import ifcfg

cfg = {
    "belacoder": dotenv_values("belacoder.env"),
    "srtla": dotenv_values("srtla.env")
}


try:
    print(cfg['belacoder'])
    print(cfg['srtla'])
    cfg['belacoder']['LATENCY']
except KeyError:
    print("Please check your configuration at belacoder.env and srtla.env")
    exit(1)


class WebhookHandler:
    def __init__(self, config):
        self.config = config

        self.client = None
        self.session = None

        self.belacoder_tasks = dict()
        self.ports = set()

        self.webapp = None

    async def listen_web(self):
        app = web.Application()
        app.add_routes([web.post('/publish', self.on_publish),
                        web.get('/publish', self.on_publish),
                        web.post('/publish_done', self.on_publish_done),
                        web.get('/publish_done', self.on_publish_done)])

        self.session = aiohttp.ClientSession()
        self.webapp = web.AppRunner(app)
        try:
            await self.webapp.setup()
            site = web.TCPSite(self.webapp, 'localhost', 7000)
            await site.start()
            print("[aiohttp Server] Site started")

            while True:
                await asyncio.sleep(3600)  # sleep forever
        except asyncio.CancelledError:
            await self.webapp.cleanup()
            return

    async def srtla_task(self, port):
        ips_file = await self.generate_ips_file()

        process = None
        try:
            while True:
                # use symlinked binaries, so we do not interfere with belaUI and vice versa
                # Syntax: srtla_send SRT_LISTEN_PORT SRTLA_HOST SRTLA_PORT BIND_IPS_FILE
                if port is not None:
                    args = [f"{port}", f"{self.config['srtla']['HOST']}", f"{self.config['srtla']['PORT']}", ips_file]
                    process = await asyncio.create_subprocess_exec("./srtla_send_push", *args)
                    await process.wait()
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            if process is not None:
                process.terminate()
                self.ports.remove(port)

    async def generate_ips_file(self):
        with open("/tmp/push_srtla.ips", "w+") as ip_file:
            for name, interface in ifcfg.interfaces().items():
                if name == "lo":
                    continue

                for ip in interface['inet4']:
                    ip_file.write(f"{ip}\n")

        return "/tmp/push_srtla.ips"

    async def start_belacoder(self, app, name):
        if (app, name) in self.belacoder_tasks:
            await self.stop_belacoder(app, name)

        port = None
        for p in range(7001, 8000):
            if p not in self.ports:
                self.ports.add(p)
                port = p
                break

        if port is None:
            print("Cannot run srtla. No free ports available.")
        else:
            self.belacoder_tasks[(app, name)] = {
                "port": port,
                "srtla": asyncio.create_task(self.srtla_task(port)),
                "belacoder": asyncio.create_task(self.belacoder_task(port, app, name))
            }

    async def stop_belacoder(self, app, name):
        if (app, name) in self.belacoder_tasks:
            tasks = self.belacoder_tasks[(app, name)]
            await self.cancel_task(tasks['belacoder'])
            await self.cancel_task(tasks['srtla'])
            del self.belacoder_tasks[(app, name)]

    async def belacoder_task(self, port, app, name):
        pipeline_file = await self.generate_pipeline_file(app, name)
        bitrate_file = await self.generate_bitrate_file(app, name)

        process = None
        try:
            while True:
                # use symlinked binaries, so we do not interfere with belaUI and vice versa
                # Syntax: belacoder PIPELINE_FILE ADDR PORT [options]
                """   -d <delay>          Audio-video delay in milliseconds
                      -s <streamid>       SRT stream ID
                      -l <latency>        SRT latency in milliseconds
                      -b <bitrate file>   Bitrate settings file, see below"""

                # generate streamid and arguments
                args = [
                        pipeline_file, '127.0.0.1', f"{port}",
                        '-d', f"{self.config['belacoder']['DELAY']}",
                        '-b', bitrate_file,
                        '-l', f"{self.config['belacoder']['LATENCY']}",
                        '-s', self.config['belacoder']['STREAMID'].replace("###APP###", app).replace("###NAME###", name)
                        ]
                process = await asyncio.create_subprocess_exec("./belacoder_push", *args)
                await process.wait()
                # await asyncio.sleep(1)
        except asyncio.CancelledError:
            if process is not None:
                process.terminate()

    async def generate_pipeline_file(self, app, name):
        with open(self.config['belacoder']['PIPELINE']) as tpl_file, \
             open(f"/tmp/{app}.{name}.pipeline", "w") as pipeline_file:
            template = [line.replace("###APP###", app).replace("###NAME###", name) for line in tpl_file.readlines()]
            pipeline_file.writelines(template)

        return f"/tmp/{app}.{name}.pipeline"

    async def generate_bitrate_file(self, app, name):
        with open(f"/tmp/{app}.{name}.bitrate", "w") as bitrate_file:
            bitrate_file.write(f"{self.config['belacoder']['MIN_BR']}000\n{self.config['belacoder']['MAX_BR']}000\n")

        return f"/tmp/{app}.{name}.bitrate"

    async def get_args(self, request):
        if request.method == "POST":
            body = await request.post()
            app = body.get('app', None)
            name = body.get('name', None)
        else:
            app = request.query.get('app', None)
            name = request.query.get('name', None)

        return app, name

    async def on_publish(self, request):
        app, name = await self.get_args(request)
        print(f"Publish started at {app} {name}")
        await self.start_belacoder(app, name)
        return web.Response(status=200, text="OK")

    async def on_publish_done(self, request):
        app, name = await self.get_args(request)
        print(f"Publish done at {app} {name}")
        await self.stop_belacoder(app, name)
        return web.Response(status=200, text="OK")

    async def cancel_task(self, task):
        if task.done():
            return
        try:
            task.cancel()
            await task
        except asyncio.CancelledError:
            pass


async def main():
    webhook_handler = WebhookHandler(cfg)
    await asyncio.gather(webhook_handler.listen_web())


def run():
    # Change to the "Selector" event loop for Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Goodbye...")


if __name__ == '__main__':
    run()
