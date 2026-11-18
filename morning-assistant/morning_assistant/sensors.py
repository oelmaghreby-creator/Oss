"""Event sources. Each one pushes (kind, value) tuples onto a queue:
("motion", None), ("door_opened", None), ("tag", item_name).
The hardware libraries are imported lazily so the app runs without them.
"""
import asyncio
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

log = logging.getLogger("sensors")


def start_gpio(events, motion_pin, door_pin):
    """PIR motion sensor, and a reed switch that is closed while the door is shut."""
    from gpiozero import Button, MotionSensor

    devices = []
    if motion_pin is not None:
        pir = MotionSensor(motion_pin)
        pir.when_motion = lambda: events.put(("motion", None))
        devices.append(pir)
    if door_pin is not None:
        door = Button(door_pin, pull_up=True, bounce_time=0.2)
        door.when_released = lambda: events.put(("door_opened", None))
        devices.append(door)
    return devices  # keep a reference or gpiozero stops listening


def start_ble(events, tags):
    """tags: {item name: BLE address}. Reports every advertisement from a known tag."""
    from bleak import BleakScanner

    by_address = {addr.upper(): item for item, addr in tags.items()}

    def on_advert(device, _adv):
        item = by_address.get(device.address.upper())
        if item:
            events.put(("tag", item))

    async def scan():
        async with BleakScanner(on_advert):
            await asyncio.Event().wait()

    threading.Thread(target=lambda: asyncio.run(scan()), daemon=True, name="ble").start()


def start_http(events, host, port, get_state):
    """GET /event/motion, /event/door_opened, /event/tag/<item>, /state.
    Lets you test without sensors, or feed events from other devices."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parts = self.path.strip("/").split("/")
            if parts == ["state"]:
                body = {"state": get_state()}
            elif parts in (["event", "motion"], ["event", "door_opened"]):
                events.put((parts[1], None))
                body = {"ok": True}
            elif len(parts) == 3 and parts[:2] == ["event", "tag"]:
                events.put(("tag", parts[2].replace("%20", " ")))
                body = {"ok": True}
            else:
                self.send_error(404)
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_POST = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True, name="http").start()
    return server
