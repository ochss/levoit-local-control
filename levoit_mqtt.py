"""Local MQTT controller for Levoit air purifiers (Vesync V2 protocol).

Implements the DNS-redirect local-control approach documented in
epicRE/levoit-local-control, adapted for Levoit Core 100S / Vital 100S.

Prerequisites (from the original guide):
  * Mosquitto MQTT broker on port 1883, allow_anonymous true, TLS optional.
  * DNS rewrite: vdmpmqtt.vesync.com -> your broker; *.vesync.com and
    *.vesyncapi.com -> 127.0.0.1 (or your broker IP).
  * DHCP serves your local DNS IP to the Levoit device.
  * Device registered via the official app, then redirected to your broker.

Protocol (V2):
  * Commands   -> mqtt/<LEVOITID>/v2/bypass
  * Responses  -> mqtt/<LEVOITID>/v2/bypass/rsp
  * Status     -> mqtt/<LEVOITID>/v2/req
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from typing import Any, Callable, Optional

try:
    import paho.mqtt.client as mqtt
except ImportError as exc:  # pragma: no cover - depends on environment
    raise SystemExit(
        "paho-mqtt is required. Install it with: pip install paho-mqtt"
    ) from exc

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 1883
DEFAULT_KEEPALIVE = 60
DEFAULT_TIMEOUT = 10  # seconds to wait for a response


class LevoitClient:
    """Thin MQTT client around a Levoit air purifier using the V2 bypass API."""

    def __init__(
        self,
        device_id: str,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        client_id: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        tls: bool = False,
    ) -> None:
        self.device_id = device_id
        self.cmd_topic = f"mqtt/{device_id}/v2/bypass"
        self.rsp_topic = f"mqtt/{device_id}/v2/bypass/rsp"
        self.state_topic = f"mqtt/{device_id}/v2/req"

        self._client = mqtt.Client(client_id=client_id or f"levoit-{uuid.uuid4().hex[:8]}")
        if username:
            self._client.username_pw_set(username, password or None)
        if tls:
            self._client.tls_set()
        self._client.connect(host, port, keepalive=DEFAULT_KEEPALIVE)
        self._client.loop_start()

        self._pending: dict[str, Any] = {}
        self._responses: list[dict[str, Any]] = []
        self._states: list[dict[str, Any]] = []

        def on_message(client, userdata, message):
            try:
                payload = json.loads(message.payload.decode("utf-8", "replace"))
            except (ValueError, UnicodeDecodeError):
                return
            topic = message.topic
            if topic == self.rsp_topic:
                trace = payload.get("traceId") if isinstance(payload, dict) else None
                if trace and trace in self._pending:
                    fut = self._pending.pop(trace)
                    fut.set_result(payload)
                self._responses.append(payload)
            elif topic == self.state_topic:
                self._states.append(payload)

        self._client.on_message = on_message
        self._client.subscribe([
            (self.rsp_topic, 0),
            (self.state_topic, 0),
        ])

    def close(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass

    def _trace_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def _send(self, method: str, data: dict[str, Any], wait: bool = True, timeout: float = DEFAULT_TIMEOUT) -> Optional[dict[str, Any]]:
        trace = self._trace_id()
        payload = {
            "traceId": trace,
            "method": "bypassV2",
            "debugMode": False,
            "payload": {"data": data, "method": method, "source": "APP"},
        }
        future = None
        if wait:
            future = self._client.loop_start() if False else None
            self._pending[trace] = _Future()

        self._client.publish(self.cmd_topic, json.dumps(payload), qos=0)

        if not wait or future is None:
            return None

        fut = self._pending[trace]
        ok = fut.wait(timeout)
        return fut.result() if ok else None

    def set_level(self, level: int, fan_type: str = "wind") -> Optional[dict[str, Any]]:
        """Set fan speed level. Valid levels are device-specific (100S often 1-5)."""
        return self._send("setLevel", {"id": 0, "level": int(level), "type": fan_type})

    def set_mode(self, mode: str) -> Optional[dict[str, Any]]:
        """Set purifier mode: sleep, manual, auto."""
        return self._send("setPurifierMode", {"mode": mode})

    def set_display(self, state: bool) -> Optional[dict[str, Any]]:
        """Turn display on/off."""
        return self._send("setDisplay", {"state": bool(state)})

    def power(self, on: bool) -> Optional[dict[str, Any]]:
        """Power the device on/off via the switch channel."""
        return self._send("setSwitch", {"switch1": "on" if on else "off"})

    def add_timer(self, action: str, total_seconds: int) -> Optional[dict[str, Any]]:
        """Add a timer (e.g. action='off', total=1800 for 30 min)."""
        return self._send("addTimer", {"action": action, "total": int(total_seconds)})

    def get_timer(self) -> Optional[dict[str, Any]]:
        return self._send("getTimer", {})

    def del_timer(self, timer_id: int) -> Optional[dict[str, Any]]:
        return self._send("delTimer", {"id": int(timer_id)})

    def get_schedule(self) -> Optional[dict[str, Any]]:
        return self._send("getSchedule", {"maxId": 0})

    def latest_state(self) -> Optional[dict[str, Any]]:
        return self._states[-1] if self._states else None

    def latest_response(self) -> Optional[dict[str, Any]]:
        return self._responses[-1] if self._responses else None


class _Future:
    """Minimal future used to await an MQTT response matching a traceId."""

    def __init__(self) -> None:
        self._result: Optional[dict[str, Any]] = None
        self._done = False

    def set_result(self, result: dict[str, Any]) -> None:
        self._result = result
        self._done = True

    def result(self) -> Optional[dict[str, Any]]:
        return self._result

    def wait(self, timeout: float) -> bool:
        deadline = time.time() + timeout
        while not self._done:
            remaining = deadline - time.time()
            if remaining <= 0:
                return False
            time.sleep(min(0.05, remaining))
        return True


def discover(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT, duration: float = 30.0) -> None:
    """Listen on the wildcard Levoit topics and print every message.

    Use this to learn your device ID and inspect the status payloads it emits.
    Leave the device idle and press buttons in the official app while this runs.
    """
    client = mqtt.Client(client_id=f"levoit-discover-{uuid.uuid4().hex[:8]}")
    seen_ids: set[str] = set()

    def on_message(cli, userdata, message):
        try:
            payload = json.loads(message.payload.decode("utf-8", "replace"))
        except (ValueError, UnicodeDecodeError):
            payload = {"_raw": message.payload.decode("utf-8", "replace")}

        context = payload.get("context", {}) if isinstance(payload, dict) else {}
        cid = context.get("cid") if isinstance(context, dict) else None
        method = context.get("method") if isinstance(context, dict) else None

        line = f"[{message.topic}]"
        if cid and cid not in seen_ids:
            seen_ids.add(cid)
            line += f"  <-- NEW DEVICE ID: {cid}"
        print(line)
        print(json.dumps(payload, indent=2)[:2000])
        print("-" * 60)

    client.on_message = on_message
    client.connect(host, port, keepalive=DEFAULT_KEEPALIVE)
    client.loop_start()
    client.subscribe("mqtt/+/v2/req", 0)
    client.subscribe("mqtt/+/v2/bypass/rsp", 0)

    print(f"Discovering Levoit devices on {host}:{port} for {duration:.0f}s...")
    print("Press buttons in the VeSync app to trigger messages. Ctrl+C to stop early.\n")
    try:
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()

    if seen_ids:
        print("\nDiscovered device ID(s):")
        for cid in sorted(seen_ids):
            print(f"  {cid}")
    else:
        print("\nNo device IDs seen. Make sure DNS redirection is active and the device is online.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Control a Levoit air purifier over local MQTT (V2 protocol)."
    )
    parser.add_argument("--host", default=DEFAULT_HOST, help="MQTT broker host")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="MQTT broker port")
    parser.add_argument("--device-id", help="Levoit device ID (CID). Discover with --discover if unknown.")
    parser.add_argument("--username", default=None, help="MQTT username")
    parser.add_argument("--password", default=None, help="MQTT password")
    parser.add_argument("--tls", action="store_true", help="Enable TLS on the MQTT connection")

    sub = parser.add_subparsers(dest="command", required=True)

    p_discover = sub.add_parser("discover", help="Listen and print Levoit MQTT messages to find device IDs")
    p_discover.add_argument("--duration", type=float, default=30.0, help="Seconds to listen")

    p_level = sub.add_parser("level", help="Set fan speed level")
    p_level.add_argument("level", type=int, help="Fan level (device-specific; 100S often 1-5)")
    p_level.add_argument("--type", default="wind", dest="fan_type", help="Fan type string")

    p_mode = sub.add_parser("mode", help="Set purifier mode")
    p_mode.add_argument("mode", choices=["sleep", "manual", "auto"], help="Purifier mode")

    p_display = sub.add_parser("display", help="Set display on/off")
    p_display.add_argument("state", choices=["on", "off"], help="Display state")

    p_power = sub.add_parser("power", help="Power on/off")
    p_power.add_argument("state", choices=["on", "off"], help="Power state")

    p_timer = sub.add_parser("timer", help="Add a timer")
    p_timer.add_argument("action", choices=["on", "off"], help="Timer action")
    p_timer.add_argument("total", type=int, help="Total seconds")

    sub.add_parser("get-timer", help="Read active timers")
    sub.add_parser("del-timer", help="Delete a timer").add_argument("id", type=int, help="Timer id")
    sub.add_parser("get-schedule", help="Read schedule")
    sub.add_parser("state", help="Print the most recent status message")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "discover":
        discover(host=args.host, port=args.port, duration=args.duration)
        return 0

    if not args.device_id:
        parser.error("--device-id is required (run 'discover' to find it)")

    client = LevoitClient(
        device_id=args.device_id,
        host=args.host,
        port=args.port,
        username=args.username,
        password=args.password,
        tls=args.tls,
    )
    try:
        result: Optional[dict[str, Any]] = None
        if args.command == "level":
            result = client.set_level(args.level, args.fan_type)
        elif args.command == "mode":
            result = client.set_mode(args.mode)
        elif args.command == "display":
            result = client.set_display(args.state == "on")
        elif args.command == "power":
            result = client.power(args.state == "on")
        elif args.command == "timer":
            result = client.add_timer(args.action, args.total)
        elif args.command == "get-timer":
            result = client.get_timer()
        elif args.command == "del-timer":
            result = client.del_timer(args.id)
        elif args.command == "get-schedule":
            result = client.get_schedule()
        elif args.command == "state":
            result = client.latest_state()

        if result is not None:
            print(json.dumps(result, indent=2))
        elif args.command != "state":
            print("No response received within timeout.")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
