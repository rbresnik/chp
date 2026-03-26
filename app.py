from flask import Flask, abort, render_template
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from ai_interpreter import interpret_incident, local_summary, translate_label, translate_timeline_details
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
    return translate_label(stripped)


@app.route("/")
def index():
    incidents = get_border_incidents()
    map_incidents = []
    ai_enabled = bool(os.getenv("OPENAI_API_KEY"))
    for incident in incidents:
        incident["type_display"] = clean_type_label(incident.get("type"))
        incident["feed_preview"] = local_summary(incident)
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
                }
            )
    return render_template(
        "index.html",
        incidents=incidents,
        count=len(incidents),
        map_incidents=map_incidents,
        ai_enabled=ai_enabled,
    )


def build_feed_summary(incident):
    details_count = len(incident.get("details", []))
    parts = [
        f"Type: {translate_label(incident.get('type') or 'Unknown')}",
        f"Time: {incident.get('time') or 'Unknown'}",
        f"Location: {incident.get('location') or 'Unknown'}",
        f"Description: {translate_label(incident.get('desc') or 'None')}",
        f"Area: {incident.get('area') or 'Unknown'}",
        f"Timeline Entries: {details_count}",
    ]
    return " | ".join(parts)


@app.route("/incident/<incident_id>")
def incident_detail(incident_id):
    incidents = get_border_incidents()
    ai_enabled = bool(os.getenv("OPENAI_API_KEY"))

    incident = next((i for i in incidents if i["id"] == incident_id), None)
    if incident is None:
        abort(404)
    incident["type_display"] = clean_type_label(incident.get("type"))

    readable = interpret_incident(incident)
    if (
        not readable
        or readable.startswith("OPENAI_API_KEY is not set")
        or readable.startswith("AI interpretation unavailable:")
    ):
        readable = build_feed_summary(incident)

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
