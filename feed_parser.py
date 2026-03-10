import requests
import xml.etree.ElementTree as ET

FEED_URL = "https://media.chp.ca.gov/sa_xml/sa.xml"


def _clean_text(value):
    if value is None:
        return None
    return value.strip().strip('"')


def _normalize_coord(value):
    if value is None:
        return None
    try:
        n = float(str(value).strip())
    except ValueError:
        return None
    # Current CHP LATLON often uses scaled integers (e.g., 38643122 => 38.643122).
    if abs(n) > 180:
        n = n / 1_000_000.0
    return n


def _parse_latlon(raw_latlon):
    text = _clean_text(raw_latlon)
    if not text:
        return (None, None)

    if ":" in text:
        parts = text.split(":", 1)
    elif "," in text:
        parts = text.split(",", 1)
    else:
        parts = text.split()
        if len(parts) < 2:
            return (None, None)
        parts = [parts[0], parts[1]]

    lat = _normalize_coord(parts[0])
    lon = _normalize_coord(parts[1])
    if lat is None or lon is None:
        return (None, None)

    # Feed usually sends west longitudes as positive numbers.
    if lon > 0:
        lon = -lon

    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return (None, None)
    return (lat, lon)


def _parse_legacy_incidents(root):
    incidents = []
    for inc in root.iter("Incident"):
        try:
            center = inc.findtext("CommCenter")
            if not (center and "BORDER" in center.upper()):
                continue

            incident = {
                "id": _clean_text(inc.findtext("IncidentNumber")),
                "time": _clean_text(inc.findtext("StartTime")),
                "type": _clean_text(inc.findtext("IncidentType")),
                "location": _clean_text(inc.findtext("Location")),
                "desc": _clean_text(inc.findtext("LocationDesc")),
                "area": _clean_text(inc.findtext("Area")),
                "lat": None,
                "lon": None,
                "details": [],
            }
            lat, lon = _parse_latlon(inc.findtext("LATLON"))
            incident["lat"] = lat
            incident["lon"] = lon

            for d in inc.iter("IncidentDetail"):
                incident["details"].append(
                    {
                        "time": _clean_text(d.findtext("DetailTime")),
                        "text": _clean_text(d.findtext("Detail")),
                    }
                )

            incidents.append(incident)
        except Exception:
            continue
    return incidents


def _parse_current_logs(root):
    incidents = []
    # Current CHP schema: <Dispatch ID="BCCC"><Log ...>
    border_dispatches = root.findall(".//Dispatch[@ID='BCCC']")
    for dispatch in border_dispatches:
        for log in dispatch.findall("Log"):
            try:
                incident = {
                    "id": _clean_text(log.attrib.get("ID")),
                    "time": _clean_text(log.findtext("LogTime")),
                    "type": _clean_text(log.findtext("LogType")),
                    "location": _clean_text(log.findtext("Location")),
                    "desc": _clean_text(log.findtext("LocationDesc")),
                    "area": _clean_text(log.findtext("Area")),
                    "lat": None,
                    "lon": None,
                    "details": [],
                }
                lat, lon = _parse_latlon(log.findtext("LATLON"))
                incident["lat"] = lat
                incident["lon"] = lon

                for d in log.findall(".//details"):
                    detail_time = _clean_text(d.findtext("DetailTime"))
                    detail_text = _clean_text(d.findtext("IncidentDetail"))
                    if detail_time or detail_text:
                        incident["details"].append(
                            {
                                "time": detail_time,
                                "text": detail_text,
                            }
                        )

                incidents.append(incident)
            except Exception:
                continue
    return incidents


def get_border_incidents():
    r = requests.get(FEED_URL, timeout=10)
    r.raise_for_status()

    root = ET.fromstring(r.content)
    incidents = _parse_current_logs(root)
    if incidents:
        return incidents

    # Backward compatibility with older feed shape.
    return _parse_legacy_incidents(root)
