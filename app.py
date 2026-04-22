from flask import Flask, abort, render_template
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from ai_interpreter import clean_label, interpret_incident, summarize_incident, translate_timeline_details
from feed_parser import get_border_incidents

# Local dev convenience: load Cloud Run-style env file if present.
env_path = Path(__file__).with_name("cloudrun.env")
load_dotenv(env_path)
load_dotenv()
if not os.getenv("OPENAI_API_KEY") and env_path.exists():
    first_line = ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        candidate = line.strip()
        if candidate and not candidate.startswith("#"):
            first_line = candidate
            break
    if first_line and "=" not in first_line:
        os.environ["OPENAI_API_KEY"] = first_line

app = Flask(__name__)
SD_MIN_LAT = 32.53
SD_MAX_LAT = 33.51
SD_MIN_LON = -117.60
SD_MAX_LON = -116.08


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


def clean_type_label(raw_type):
    if not raw_type:
        return "Unknown"
    # Remove CHP numeric code prefix like "1125-" or "20002-".
    stripped = re.sub(r"^\s*\d+[A-Za-z]?\s*-\s*", "", raw_type).strip() or raw_type
    return clean_label(stripped)


def is_traffic_collision(text):
    normalized = re.sub(r"\s+", " ", (text or "")).strip().lower()
    if not normalized:
        return False
    return bool(
        re.search(r"\btraffic\s+collision\b", normalized)
        or re.search(r"\btrfc\b", normalized)
        or re.search(r"\btc\b", normalized)
        or "collision" in normalized
    )


@app.route("/")
def index():
    incidents = get_border_incidents()
    map_incidents = []
    ai_enabled = bool(os.getenv("OPENAI_API_KEY"))
    traffic_count = 0
    for incident in incidents:
        incident["type_display"] = clean_type_label(incident.get("type"))
        incident["feed_preview"] = summarize_incident(incident)
        incident["is_traffic_collision"] = is_traffic_collision(
            incident.get("type") or incident.get("type_display") or incident.get("desc")
        )
        if incident["is_traffic_collision"]:
            traffic_count += 1
        lat = incident.get("lat")
        lon = incident.get("lon")
        in_sd_county = (
            lat is not None
            and lon is not None
            and SD_MIN_LAT <= lat <= SD_MAX_LAT
            and SD_MIN_LON <= lon <= SD_MAX_LON
        )
        if in_sd_county:
            map_incidents.append(
                {
                    "id": incident.get("id"),
                    "lat": lat,
                    "lon": lon,
                    "location": incident.get("location"),
                    "time": incident.get("time"),
                    "type": incident.get("type_display"),
                    "is_traffic_collision": incident["is_traffic_collision"],
                }
            )
    return render_template(
        "index.html",
        incidents=incidents,
        count=len(incidents),
        traffic_count=traffic_count,
        other_count=max(len(incidents) - traffic_count, 0),
        map_count=len(map_incidents),
        map_incidents=map_incidents,
        ai_enabled=ai_enabled,
    )
@app.route("/incident/<incident_id>")
def incident_detail(incident_id):
    incidents = get_border_incidents()
    ai_enabled = bool(os.getenv("OPENAI_API_KEY"))

    incident = next((i for i in incidents if i["id"] == incident_id), None)
    if incident is None:
        abort(404)
    incident["type_display"] = clean_type_label(incident.get("type"))
    incident["is_traffic_collision"] = is_traffic_collision(
        incident.get("type") or incident.get("type_display") or incident.get("desc")
    )

    readable = interpret_incident(incident)

    timeline = translate_timeline_details(incident.get("details", []))
    # Feed details are newest-first; render oldest-first so the first event is at the top.
    timeline = list(reversed(timeline))
    return render_template(
        "incident.html",
        incident=incident,
        readable=readable,
        timeline=timeline,
        ai_enabled=ai_enabled,
    )


if __name__ == "__main__":
    app.run(debug=True)
