DOMAIN = "axium"
CONF_HOST = "host"
CONF_ZONES = "zones"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_ZONES = [1, 2, 3, 4, 5, 6, 7, 8]
DEFAULT_SCAN_INTERVAL = 3  # seconds

HTTP_URL = "http://{host}/axium.cgi"
HEADERS = {"Content-Type": "application/x-axium"}

# Command codes
CMD_POWER = "01"   # 01 {zone} {00/01}
CMD_MUTE = "02"
CMD_SOURCE = "03"
CMD_VOLUME = "04"  # 04 {zone} {00..A0}
CMD_MAXVOL = "0D"
CMD_SRCNAME = "29"
CMD_AVAILSRC = "3C"
CMD_LINKZONES = "30"

STATE_ON = "01"
STATE_OFF = "00"
