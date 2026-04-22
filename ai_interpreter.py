import json
import os
import re
from datetime import datetime


def _clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip().strip('"')


def _normalize_whitespace(text):
    return re.sub(r"\s+", " ", (text or "")).strip()


def _public_sentence(text):
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return ""
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def _strip_code_prefix(text):
    cleaned = _clean_text(text)
    if not cleaned:
        return "Unknown"
    return re.sub(r"^\s*\d+[A-Za-z]?\s*-\s*", "", cleaned).strip() or cleaned


def clean_label(text):
    return _strip_code_prefix(text)


def _detail_sort_key(detail):
    raw_time = _normalize_whitespace((detail or {}).get("time"))
    for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y %I:%M %p"):
        try:
            return (0, datetime.strptime(raw_time, fmt))
        except ValueError:
            continue
    return (1, raw_time)


def _sorted_details(details):
    return sorted(details or [], key=_detail_sort_key)


def _openai_client(api_key):
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def _chat_with_openai(messages, api_key):
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    try:
        client = _openai_client(api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:
        return f"AI interpretation unavailable: {exc}"


def _fallback_incident_summary(incident):
    details = _sorted_details(incident.get("details"))
    lines = [
        f"Type: {clean_label(incident.get('type') or 'Unknown')}",
        f"Time: {_clean_text(incident.get('time')) or 'Unknown'}",
        f"Location: {_clean_text(incident.get('location')) or 'Unknown'}",
        f"Description: {_clean_text(incident.get('desc')) or 'Unknown'}",
        f"Area: {_clean_text(incident.get('area')) or 'Unknown'}",
    ]
    if details:
        lines.append("Timeline:")
        for detail in details:
            time_text = _clean_text(detail.get("time")) or "Unknown time"
            text = _normalize_whitespace(detail.get("text")) or "No detail text"
            lines.append(f"- {time_text}: {text}")
    return "\n".join(lines)


def _serialize_incident_for_prompt(incident):
    details = _sorted_details(incident.get("details"))
    lines = [
        f"Incident ID: {_clean_text(incident.get('id')) or 'Unknown'}",
        f"Type: {_clean_text(incident.get('type')) or 'Unknown'}",
        f"Time: {_clean_text(incident.get('time')) or 'Unknown'}",
        f"Location: {_clean_text(incident.get('location')) or 'Unknown'}",
        f"Description: {_clean_text(incident.get('desc')) or 'Unknown'}",
        f"Area: {_clean_text(incident.get('area')) or 'Unknown'}",
        "Raw timeline:",
    ]
    if details:
        for idx, detail in enumerate(details, start=1):
            time_text = _clean_text(detail.get("time")) or "Unknown time"
            text = _normalize_whitespace(detail.get("text")) or "No detail text"
            lines.append(f"{idx}. {time_text} | {text}")
    else:
        lines.append("No detail lines were provided.")
    return "\n".join(lines)


def _extract_json_array(content):
    if not content:
        return None
    text = content.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        pass

    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None
    return None


def interpret_incident(incident):
    if not incident:
        return "Incident not found."

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _fallback_incident_summary(incident)

    prompt = _serialize_incident_for_prompt(incident)
    messages = [
        {
            "role": "system",
            "content": (
                "You interpret raw CHP incident feed data into plain English for the public. "
                "Do not use a fixed glossary or predefined phrase table. Infer shorthand from context. "
                "Keep every statement grounded in the provided data. If something is uncertain, say so explicitly. "
                "Do not invent injuries, causes, or vehicle details."
            ),
        },
        {
            "role": "user",
            "content": (
                "Write one concise paragraph, 3 to 5 sentences, that explains what happened, "
                "what is known so far, and any key road impacts or response updates. "
                "Do not use bullets, labels, or abbreviations in the final answer.\n\n"
                f"{prompt}"
            ),
        },
    ]

    content = _chat_with_openai(messages, api_key)
    if not content or content.startswith("AI interpretation unavailable:"):
        return _fallback_incident_summary(incident)
    return content.strip()


def summarize_incident(incident):
    if not incident:
        return "Incident not found."

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _clean_text(incident.get("desc")) or "Open the incident for details."

    prompt = _serialize_incident_for_prompt(incident)
    messages = [
        {
            "role": "system",
            "content": (
                "You write short public-facing summaries of raw CHP incident feed data. "
                "Do not use a fixed glossary or predefined phrase table. Infer shorthand from context. "
                "Keep the summary grounded in the provided data and do not invent details."
            ),
        },
        {
            "role": "user",
            "content": (
                "Write a concise summary in 1 to 2 sentences, suitable for a list view under an incident. "
                "Focus on what happened and the most important impact. "
                "Do not use bullets, labels, or abbreviations in the final answer.\n\n"
                f"{prompt}"
            ),
        },
    ]

    content = _chat_with_openai(messages, api_key)
    if not content or content.startswith("AI interpretation unavailable:"):
        return _clean_text(incident.get("desc")) or "Open the incident for details."
    return content.strip()


def translate_timeline_details(details):
    translated = []
    for detail in details or []:
        translated.append(
            {
                "time": detail.get("time"),
                "text": detail.get("text"),
                "ai_text": _normalize_whitespace(detail.get("text")) or "No detail text",
            }
        )

    if not translated:
        return translated

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return translated

    numbered = []
    for idx, row in enumerate(translated, start=1):
        time_text = _clean_text(row["time"]) or "Unknown time"
        raw_text = _normalize_whitespace(row["text"]) or "No detail text"
        numbered.append(f"{idx}|||{time_text}|||{raw_text}")

    messages = [
        {
            "role": "system",
            "content": (
                "You translate raw CHP feed timeline lines into clear, natural English. "
                "Do not use a fixed glossary or predefined phrase table. Infer shorthand from context. "
                "Keep each line separate, preserve the original order, and keep every fact grounded in the input. "
                "If a detail is unclear, say that it is unclear. "
                "Do not repeat the timestamp in the translation because the page already shows it next to each line."
            ),
        },
        {
            "role": "user",
            "content": (
                "Return JSON only as an array of objects with this shape: "
                '[{"index":1,"translation":"..."}]. '
                "Provide exactly one translated sentence per input line. "
                "Do not add commentary, markdown, or extra keys.\n\n"
                + "\n".join(numbered)
            ),
        },
    ]

    content = _chat_with_openai(messages, api_key)
    if not content or content.startswith("AI interpretation unavailable:"):
        return translated

    parsed = _extract_json_array(content)
    if not isinstance(parsed, list):
        return translated

    parsed_by_index = {}
    for item in parsed:
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        translation = item.get("translation")
        if isinstance(index, int) and 1 <= index <= len(translated) and isinstance(translation, str):
            parsed_by_index[index] = _public_sentence(translation)

    for idx, row in enumerate(translated, start=1):
        candidate = parsed_by_index.get(idx)
        if candidate:
            row["ai_text"] = candidate

    return translated
