from __future__ import annotations
from typing import Iterable, Optional

import aiohttp

from .const import HTTP_URL, HEADERS


class AxiumApi:
    """
    Thin HTTP client for Axium's axium.cgi / axiumlong.cgi endpoints.

    Key helpers:
    - send_lines(): batch multiple opcodes in one POST
    - request_zone_names(): sends 1BFF (or 1B<zone>) to elicit 1C replies
    - snapshot_burst(..., include_names=True): prepends 1BFF so 1C frames arrive
    - webapp_init(): mimics the web UI's initial multi-command POST to trigger name sweeps
    """

    def __init__(self, session: aiohttp.ClientSession, host: str):
        self._session = session
        self._host = host
        self._url = HTTP_URL.format(host=host)

    async def initial_probe(self) -> str:
        """POST empty body to prompt a snapshot dump (common on many firmwares)."""
        async with self._session.post(
            self._url, headers=HEADERS, data=b"", timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            return (await resp.text()).replace("\r", "")

    async def send(self, code: str) -> str:
        """Send a single opcode line, e.g. '1BFF' or '03C1'."""
        payload = f"{code}\r\n"
        async with self._session.post(
            self._url, headers=HEADERS, data=payload, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            resp.raise_for_status()
            return (await resp.text()).replace("\r", "")

    async def send_lines(self, lines: Iterable[str]) -> str:
        """Send multiple opcode lines in one POST."""
        payload = "".join(f"{ln}\r\n" for ln in lines)
        async with self._session.post(
            self._url, headers=HEADERS, data=payload, timeout=aiohttp.ClientTimeout(total=20)
        ) as resp:
            resp.raise_for_status()
            return (await resp.text()).replace("\r", "")

    async def snapshot_burst(self, zone_hex: str, include_names: bool = True) -> str:
        """
        Ask the amp for a quick state burst for a zone.
        include_names=True adds a broadcast 1BFF so we receive 1C zone-name replies.
        """
        burst = [
            f"30{zone_hex}",  # group/options
            f"01{zone_hex}",  # power
            f"02{zone_hex}",  # mute (if supported by firmware)
            f"03{zone_hex}",  # source (and power bit)
            f"04{zone_hex}",  # volume
            f"29{zone_hex}",  # source names (some firmwares)
            f"3C{zone_hex}",  # model/flags (varies)
            f"0D{zone_hex}",  # max volume
        ]
        if include_names:
            # Request zone names; many models reply with multiple 1C<zone>... lines
            burst.insert(0, "1BFF")

        return await self.send_lines(burst)

    async def request_zone_names(self, zone_hex: Optional[str] = None) -> str:
        """
        Request zone-name replies (1C frames).
        - zone_hex=None or 'FF' -> broadcast 1BFF
        - otherwise per-zone 1B<zone_hex>
        """
        target = "FF" if zone_hex in (None, "FF") else zone_hex
        return await self.send(f"1B{target}")

    async def webapp_init(self) -> str:
        """
        Mimic the web UI's initial POST sequence to trigger zone/preset name sweeps:

          14FF06           (query settings / kick names)
          30FF20           (zone linking snapshot)
          2BFF02..2BFF0F   (request preset names)
          38FF             (refresh)
        """
        lines = ["14FF06", "30FF20"]
        for preset in range(1, 15):           # presets 1..14
            param = preset + 1                # web app uses preset+1 in 0x2B
            lines.append(f"2BFF{param:02X}")
        lines.append("38FF")
        return await self.send_lines(lines)

    async def open_longpoll(self) -> aiohttp.ClientResponse:
        """
        Open the long-poll stream (axiumlong.cgi). Caller must iterate chunks and release resp.
        """
        url = self._url.replace("/axium.cgi", "/axiumlong.cgi")
        resp = await self._session.get(url, headers=HEADERS, timeout=aiohttp.ClientTimeout(total=None))
        resp.raise_for_status()
        return resp
