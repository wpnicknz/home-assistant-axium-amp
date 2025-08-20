from __future__ import annotations
import asyncio
import logging
from datetime import timedelta
import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AxiumApi

_LOGGER = logging.getLogger(__name__)


def encode_zone(zone: int) -> str:
    z = zone
    if z != 0xFF:
        if z >= 64:
            z = 0xC0 + (z - 64)
        elif z >= 32:
            z = 0x80 + (z - 32)
    return f"{z:02X}"


def decode_zone(z_hex: str) -> int | None:
    try:
        z = int(z_hex, 16)
    except ValueError:
        return None
    if z != 0xFF:
        z &= ~0x20
        top = z & 0xC0
        if top == 0x80:
            return 32 + (z & 0x1F)
        if top == 0xC0:
            return 64 + (z & 0x1F)
        if top == 0x40:
            return None
    return z


DECODE_SOURCE_MAP = {0: 4, 1: 5, 2: 6, 3: 3, 4: 7, 5: 0, 6: 1, 7: 2}
ENCODE_SOURCE_MAP = {v: k for k, v in DECODE_SOURCE_MAP.items()}


class AxiumCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, session: aiohttp.ClientSession, host: str, zones: list[int], scan_interval: int):
        # Long-poll only: disable periodic polling by setting update_interval=None
        super().__init__(hass, _LOGGER, name="axium", update_interval=None)
        self.hass = hass
        self.api = AxiumApi(session, host)
        self.zones = zones

        # State caches
        self.power: dict[int, str | None] = {z: None for z in zones}
        self.volume: dict[int, int | None] = {z: None for z in zones}
        self.source: dict[int, int | None] = {z: None for z in zones}
        self.max_vol: dict[int, int | None] = {z: 0xA0 for z in zones}
        self.source_names: dict[int, dict[int, str]] = {z: {} for z in zones}
        self.zone_names: dict[int, str] = {}

        self._lp_task: asyncio.Task | None = None

        # Group/linking
        self.zone_group: dict[int, int | None] = {z: None for z in zones}
        self.group_options: dict[int, int] = {}

    def _linked_peers(self, zone: int) -> list[int]:
        g = self.zone_group.get(zone)
        if g is None:
            return []
        return [z for z, gz in self.zone_group.items() if gz == g and z != zone]

    async def _async_update_data(self):
        # No polling; just return the current cache when HA asks once at startup.
        return {
            "power": self.power,
            "volume": self.volume,
            "source": self.source,
            "max_vol": self.max_vol,
            "source_names": self.source_names,
            "zone_names": self.zone_names,
        }

    async def async_config_entry_first_refresh(self):
        # 1) Initial probe (many firmwares dump a snapshot)
        try:
            text = await self.api.initial_probe()
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    _LOGGER.debug("SNAPSHOT RX (probe): %s", line)
                    self._handle_frame(line)
        except Exception as e:
            _LOGGER.debug("Initial probe failed: %s", e)

        # 2) Mimic the web UI init (triggers 1C zone-name and 2A preset-name sweeps)
        try:
            text = await self.api.webapp_init()
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    _LOGGER.debug("WEBINIT RX: %s", line)
                    self._handle_frame(line)
        except Exception as e:
            _LOGGER.debug("Web-app init burst failed: %s", e)

        # 3) Per-zone snapshots (also requests names via 1BFF inside snapshot_burst)
        for z in self.zones:
            try:
                text = await self.api.snapshot_burst(encode_zone(z))
                for line in text.split("\n"):
                    line = line.strip()
                    if line:
                        _LOGGER.debug("SNAPSHOT RX: %s", line)
                        self._handle_frame(line)
            except Exception as e:
                _LOGGER.debug("Snapshot burst failed for zone %s: %s", z, e)

        # Coordinator initial refresh (returns current cache)
        await super().async_config_entry_first_refresh()

        # 4) Start long-poll stream
        if self._lp_task is None:
            self._lp_task = self.hass.loop.create_task(self._longpoll_loop())

        # 5) Retry names for any zones still missing one (after short delay)
        self.hass.loop.create_task(self._retry_missing_names_later(delay_sec=3))

    async def _retry_missing_names_later(self, delay_sec: float = 3.0):
        await asyncio.sleep(delay_sec)
        missing = [z for z in self.zones if not self.zone_names.get(z)]
        if not missing:
            return
        _LOGGER.debug("Retrying zone-name request for zones missing names: %s", missing)
        try:
            text = await self.api.send_lines([f"1B{encode_zone(z)}" for z in missing])
            for line in text.split("\n"):
                line = line.strip()
                if line:
                    _LOGGER.debug("NAME RX (retry): %s", line)
                    self._handle_frame(line)
        except Exception as e:
            _LOGGER.debug("Zone-name retry failed: %s", e)

    async def _longpoll_loop(self):
        backoff = 1
        while True:
            try:
                if self.api._session.closed:
                    self.api._session = async_get_clientsession(self.hass)
                resp = await self.api.open_longpoll()
                backoff = 1  # reset backoff on success
                try:
                    async for chunk, _ in resp.content.iter_chunks():
                        if not chunk:
                            continue
                        text = chunk.decode(errors="ignore")
                        for line in text.replace("\r", "").split("\n"):
                            line = line.strip()
                            if line:
                                _LOGGER.debug("RX: %s", line)
                                self._handle_frame(line)
                finally:
                    await resp.release()
            except Exception as e:
                _LOGGER.debug("Long-poll error, retrying in %ss: %s", backoff, e)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 30)  # cap backoff at 30s

    def _handle_frame(self, line: str):
        # Normalize and sanity-check
        line = line.strip().upper()
        if len(line) < 4:
            return
        if any(c not in "0123456789ABCDEF" for c in line):
            _LOGGER.debug("Ignoring non-hex frame: %r", line)
            return

        cmd = line[:2]
        zone_raw = line[2:4] if len(line) >= 4 else None
        z = decode_zone(zone_raw) if zone_raw else None
        data = line[4:]

        changed = False  # only push if something actually changed

        try:
            # 0x01: Power state/events
            if cmd == "01" and len(data) >= 2:
                if z is None:
                    return
                d = data[:2]
                prev = self.power.get(z)
                if d in ("01", "07"):
                    self.power[z] = "on"
                elif d in ("00", "06"):
                    self.power[z] = "off"
                if self.power.get(z) != prev:
                    changed = True
                g = self.zone_group.get(z)
                if g is not None and (self.group_options.get(g, 0) & 0x04):
                    for peer in self._linked_peers(z):
                        if self.power.get(peer) != self.power.get(z):
                            self.power[peer] = self.power.get(z)
                            changed = True

            # 0x03: Source select (with power bit)
            elif cmd == "03" and len(data) >= 2:
                if z is None:
                    return
                val = int(data[:2], 16)
                if val & 0x80:
                    if self.power.get(z) != "on":
                        self.power[z] = "on"
                        changed = True
                    val &= 0x1F
                decoded = DECODE_SOURCE_MAP.get(val, val)
                if self.source.get(z) != decoded:
                    self.source[z] = decoded
                    changed = True
                g = self.zone_group.get(z)
                if g is not None and (self.group_options.get(g, 0) & 0x01):
                    for peer in self._linked_peers(z):
                        if self.source.get(peer) != decoded:
                            self.source[peer] = decoded
                            changed = True

            # 0x04: Volume
            elif cmd == "04" and len(data) >= 2:
                if z is None:
                    return
                vol = int(data[:2], 16)
                if self.volume.get(z) != vol:
                    self.volume[z] = vol
                    changed = True
                g = self.zone_group.get(z)
                if g is not None and (self.group_options.get(g, 0) & 0x02):
                    for peer in self._linked_peers(z):
                        if self.volume.get(peer) != vol:
                            self.volume[peer] = vol
                            changed = True

            # 0x0D: Max volume
            elif cmd == "0D" and len(data) >= 2:
                if z is None:
                    return
                mv = int(data[:2], 16)
                if self.max_vol.get(z) != mv:
                    self.max_vol[z] = mv
                    changed = True

            # 0x14: Seen in captures — ignore
            elif cmd == "14":
                pass

            # 0x1C: Zone name (reply to 1Bxx)
            elif cmd == "1C":
                # 1C <zone> <hex string, null-terminated>
                try:
                    data2 = data[:-1] if len(data) % 2 else data
                    raw = bytes.fromhex(data2)
                except Exception:
                    raw = b""
                name_bytes = raw.split(b"\x00", 1)[0]
                try:
                    name = name_bytes.decode("utf-8").strip()
                except Exception:
                    name = name_bytes.decode("latin-1", errors="ignore").strip()
                if z is not None and name:
                    prev = self.zone_names.get(z)
                    if prev != name:
                        self.zone_names[z] = name
                        _LOGGER.debug("ZONENAME parsed: zone=%s name=%s (prev=%s)", z, name, prev)
                        changed = True

            # 0x29: Source name
            elif cmd == "29" and len(data) >= 2:
                enc_src = int(data[:2], 16)
                norm = DECODE_SOURCE_MAP.get(enc_src, enc_src)
                raw_name_hex = data[8:] if len(data) >= 8 else ""
                if len(raw_name_hex) % 2 == 1:
                    raw_name_hex = raw_name_hex[:-1]
                try:
                    name = bytes.fromhex(raw_name_hex).decode(errors="ignore").strip("\x00 ").strip()
                except Exception:
                    name = None
                if name:
                    targets = (self.zones if (z == 0xFF or z is None) else [z])
                    updated_any = False
                    for _zz in targets:
                        prev = self.source_names.setdefault(_zz, {}).get(norm)
                        if prev != name:
                            self.source_names[_zz][norm] = name
                            updated_any = True
                    if updated_any:
                        _LOGGER.debug("SRCNAME parsed: zone=%s enc=%s norm=%s name=%s", z, enc_src, norm, name)
                        changed = True

            # 0x2A: Preset name (optional — produced after 2B requests)
            elif cmd == "2A" and len(data) >= 2:
                # preset number is first byte (minus 1 per web app), then UTF-8 name
                try:
                    preset = int(data[:2], 16) - 1
                except Exception:
                    preset = None
                pname_hex = data[2:]
                if len(pname_hex) % 2 == 1:
                    pname_hex = pname_hex[:-1]
                try:
                    pname = bytes.fromhex(pname_hex).decode(errors="ignore").strip("\x00 ").strip()
                except Exception:
                    pname = None
                if preset is not None and pname:
                    _LOGGER.debug("PRESETNAME parsed: preset=%s name=%s", preset, pname)
                    # Store if/when you add self.preset_names and set changed=True

            # 0x2B: Index sweep — no state change here
            elif cmd == "2B":
                pass

            # 0x30: Group options & membership
            elif cmd == "30" and len(data) >= 2:
                try:
                    opts = int(data[:2], 16)
                    preamble_bytes = 5 if (opts & 0x80) else 1
                    rest = data[2 * preamble_bytes:]
                    zones = []
                    for i in range(0, len(rest), 2):
                        zz = rest[i:i+2]
                        if len(zz) < 2:
                            break
                        dz = decode_zone(zz)
                        if dz is not None:
                            zones.append(dz)
                    for dz in zones:
                        self.zone_group[dz] = None
                    used = {g for g in self.zone_group.values() if g is not None}
                    spare = next((g for g in range(48) if g not in used), None)
                    if spare is not None and len(zones) > 1:
                        self.group_options[spare] = opts
                        for dz in zones:
                            if self.zone_group.get(dz) != spare:
                                self.zone_group[dz] = spare
                                changed = True
                except Exception:
                    pass

            # 0x38: Keepalive/refresh — ignore
            elif cmd == "38":
                pass

            else:
                # Unknown/unsupported frame; ignore quietly
                pass

        except Exception as e:
            _LOGGER.debug("Frame parse error for '%s': %s", line, e)

        if changed:
            self.async_set_updated_data({
                "power": self.power,
                "volume": self.volume,
                "source": self.source,
                "max_vol": self.max_vol,
                "source_names": self.source_names,
                "zone_names": self.zone_names,
            })
