import os
import re
from datetime import datetime


ADMIN_DETAIL_PATTERNS = [
    re.compile(r"\bdoor code\b", re.IGNORECASE),
    re.compile(r"\bgate code\b", re.IGNORECASE),
    re.compile(r"\bphone numbers?\b", re.IGNORECASE),
    re.compile(r"\bphone\s*#s?\b", re.IGNORECASE),
    re.compile(r"\brcard\b", re.IGNORECASE),
    re.compile(r"\baccess\b", re.IGNORECASE),
]


PHRASE_REPLACEMENTS = [
    (
        re.compile(r"\bOO\s+VEH\b", re.IGNORECASE),
        "out of vehicle",
    ),
    (
        re.compile(r"\bATC\s*X?\s*(\d+)\s+NO\s+ANSWER\b", re.IGNORECASE),
        lambda m: f"Attempted to contact {m.group(1)} times with no answer",
    ),
    (
        re.compile(
            r"\bUNABLE\s+TO\s+CB\b.*\bMULT\b.*\bBACKGROUND\b.*\bPOSS\b.*\bINJ",
            re.IGNORECASE,
        ),
        "Unable to call back. Multiple people were talking in the background; possible injuries",
    ),
    (
        re.compile(
            r"\bPROBLEM\s+CHANGED\s+FROM\s+TRFC\s+COLLISION\s+UNKN\s+INJURIES\s+TO\s+TRFC\s+COLLISION\s+ENRT\s+BY\s+CHP\b",
            re.IGNORECASE,
        ),
        "Dispatch update: traffic collision changed from unknown injuries to CHP units en route",
    ),
    (
        re.compile(
            r"\bPROBLEM\s+CHANGED\s+FROM\b.*?\bTO\b.*?\bENRT\s+BY\s+CHP\b",
            re.IGNORECASE,
        ),
        "Dispatch update: incident updated and CHP units are en route",
    ),
    (
        re.compile(
            r"\bPER\s+SDSO\b.*\bUNKNOWN\b\s*#?\s*\bOF\s+VEHICLES\s+INVOLVED\b",
            re.IGNORECASE,
        ),
        "According to the San Diego Sheriff's Office, the number of vehicles involved is unknown",
    ),
    (
        re.compile(r"\bSIL\s+SUV\s+VS\s+SMALLER\s+SD\b", re.IGNORECASE),
        "Silver SUV versus a smaller sedan",
    ),
    (
        re.compile(r"\bS\d+\s+97\s+ACTIVATE\s+CT\s+FOR\s+CLOSURE\b", re.IGNORECASE),
        "Unit arrived on scene and requested a road closure",
    ),
    (
        re.compile(
            r"\bS\d+\s+WILL\s+GIVE\b.*?\bCLOSURE\s+IN\s+(\d+)\s+MINS?\b",
            re.IGNORECASE,
        ),
        lambda m: f"Unit will provide the closure location update in {m.group(1)} minutes",
    ),
    (
        re.compile(r"^\s*CT\s*$", re.IGNORECASE),
        "Notified Caltrans",
    ),
    (
        re.compile(r"\b95\s*/\s*S\d+\s+CPZ\b", re.IGNORECASE),
        "Unit is at the closure point",
    ),
    (
        re.compile(r"^\s*95\s*/\s*UNIT\s+CLOSURE\s+POINT\s*$", re.IGNORECASE),
        "Unit is at the closure point",
    ),
    (
        re.compile(
            r"\bWILL\s+START\s+MAKING\s+CALLS\s+FOR\s+CLSR\s+CREW\s*/\s*INQ\s+IF\s+NEED\s+SWEEPER\b\??",
            re.IGNORECASE,
        ),
        "Will start calling for a closure crew and ask whether a sweeper is needed",
    ),
    (
        re.compile(r"\b(\d+)\s+VEHICLE'?S?\s+INV['’]?D\b", re.IGNORECASE),
        lambda m: f"{m.group(1)} vehicles involved",
    ),
    (
        re.compile(r"\bVEHICLE'?S?\s+INV['’]?D\b", re.IGNORECASE),
        "vehicles involved",
    ),
    (
        re.compile(r"\bTOYT\s+TAC\b", re.IGNORECASE),
        "Toyota Tacoma",
    ),
    (
        re.compile(r"^\s*IPHONE\s+TRAFFIC\s+COLLISION\s+NOTIFICATION\s*$", re.IGNORECASE),
        "An iPhone crash detection alert reported a traffic collision",
    ),
    (
        re.compile(r"^\s*IN\s+ROAD\s*$", re.IGNORECASE),
        "A vehicle is in the roadway",
    ),
    (
        re.compile(r"^\s*NOT\s+BLOCKING\s+TRAFFIC\s*$", re.IGNORECASE),
        "The collision is not blocking traffic",
    ),
    (
        re.compile(
            r"^\s*ACCORDING\s+TO\s+STAM\s+START\s+FIRE\s+FOR\s+VEHICLE\s+DOWN\s+IN\s+DITCH\s*$",
            re.IGNORECASE,
        ),
        "According to staff, fire crews were started for a vehicle down in a ditch",
    ),
    (
        re.compile(r"^\s*CDF(?:\s+|[-/])SEDAN\.?\s*$", re.IGNORECASE),
        "A Cal Fire sedan is involved",
    ),
    (
        re.compile(r"^\s*3A\s+SO#?\s*\d+\s+ADVANTAGE\s+TOW\.?\s*$", re.IGNORECASE),
        "Tow services were dispatched to the scene",
    ),
    (
        re.compile(r"^\s*ON\s+OFR\.?\s*$", re.IGNORECASE),
        "The vehicle was on the off-ramp",
    ),
    (
        re.compile(r"^\s*ON\s+RHS\s+OF\s+CON\.?\s*$", re.IGNORECASE),
        "The vehicle was on the right-hand side of the connector road",
    ),
    (
        re.compile(r"^\s*IS\s+THE\s+VEH\s+1125\?\s+OR\s+ON\s+RHS\?\s*$", re.IGNORECASE),
        "Initial reports were unclear whether the vehicle was still in traffic or on the right shoulder",
    ),
    (
        re.compile(r"^\s*IS\s+THE\s+VEH\s*\?\s+OR\s+ON\s+RHS\?\s*$", re.IGNORECASE),
        "Initial reports were unclear whether the vehicle was still in traffic or on the right shoulder",
    ),
    (
        re.compile(r"^\s*VEHICLE\s+(\d+)\s+FT\s+OTS\.?\s*$", re.IGNORECASE),
        lambda m: f"The vehicle is about {m.group(1)} feet off to the side",
    ),
    (
        re.compile(r"^\s*VEHICLE\s+(\d+)\s+FT\s+OFF\s+TO\s+THE\s+SIDE\.?\s*$", re.IGNORECASE),
        lambda m: f"The vehicle is about {m.group(1)} feet off to the side",
    ),
    (
        re.compile(r"^\s*BLACK\s+PK\s+OTURNED\.?\s*$", re.IGNORECASE),
        "A black pickup truck overturned",
    ),
    (
        re.compile(r"^\s*(black|white|gray|grey|silver|red)\s+pickup\s+truck\s+overturned\.?\s*$", re.IGNORECASE),
        lambda m: f"A {m.group(1).lower()} pickup truck overturned",
    ),
    (
        re.compile(
            r"^\s*FORD\s+TRAFFIC\s+COLLISION\s+NOTIFICATION\s+AIR\s+BAGS?\s+DEPLOYED\s+NVR\.?\s+GOOD\s+SAM\s+STOPPED\s+TO\s+ASSIST\s+IN\s+WHITE\s+TOTY\s+TUNDRA\s+AND\s+HAS\s+THE\s+(\d+)\s+OCCUPANTS\s+ON\s+THE\s+SIDE\s+OF\s+THE\s+RDWY\s+WAITING\s+FOR\s+MEDICS\s+AND\s+PD\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: f"A crash notification from a Ford vehicle indicated airbags had deployed with no verbal response. A Good Samaritan in a white Toyota Tundra stopped to help and has the {m.group(1)} occupants on the side of the roadway awaiting medics and police",
    ),
    (
        re.compile(
            r"^\s*(\d+)\s+VEHICLES?\s+TRAFFIC\s+COLLISION\s+(.+?)\s+VS\s+(.+?)\s*$",
            re.IGNORECASE,
        ),
        lambda m: f"A {m.group(1)}-vehicle traffic collision involving {m.group(2)} and {m.group(3)}",
    ),
    (
        re.compile(r"^\s*(\d+)\s+VEHICLE\s+COP\s+ONLY\s*$", re.IGNORECASE),
        lambda m: f"{m.group(1)} vehicles involved with complaint of pain only",
    ),
    (
        re.compile(r"^\s*(.+?)\s+VERSUS\s+UNKNOWN\s+VEHICLE\s*$", re.IGNORECASE),
        lambda m: f"A collision involving {m.group(1)} and an unknown vehicle",
    ),
    (
        re.compile(r"^\s*(.+?)\s+VS\s+UNKNOWN\s+VEHICLE\s*$", re.IGNORECASE),
        lambda m: f"A collision involving {m.group(1)} and an unknown vehicle",
    ),
    (
        re.compile(
            r"^\s*PROBLEM\s+CHANGED\s+FROM\s+TRAFFIC\s+COLLISION\s+UNKNOWN\s+INJURIES\s+TO\s+TRAFFIC\s+COLLISION\s+MINOR\s+INJURIES\s*$",
            re.IGNORECASE,
        ),
        "Dispatch updated the incident from unknown injuries to minor injuries",
    ),
    (
        re.compile(r"^\s*TRAFFIC\s+COLLISION\s*[-]?\s*EN\s+ROUTE\s*$", re.IGNORECASE),
        "Traffic collision with CHP units en route",
    ),
    (
        re.compile(
            r"^\s*FD\s+CONFIRMED\s+VIA\s+(?:A/?N|AN)\s+WAS\s+NEEDED(?:\s*/\s*|\s+AND\s+)COPIES\s+(.+?)\s+TOW\s+EN\s+ROUTE\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: f"Fire Department confirmed an ambulance was needed and advised that {m.group(1)} Tow is en route",
    ),
    (
        re.compile(
            r"^\s*FIRE\s+DEPARTMENT\s+CONFIRMED\s+VIA\s+(?:A/?N|AN)\s+WAS\s+NEEDED(?:\s*/\s*|\s+AND\s+)ADVISED\s+(.+?)\s+TOW\s+EN\s+ROUTE\.?\s*$",
            re.IGNORECASE,
        ),
        lambda m: f"Fire Department confirmed an ambulance was needed and advised that {m.group(1)} Tow is en route",
    ),
    (
        re.compile(r"^\s*COPY,?\s+WILL\s+ADV(?:ISE)?\s+(.+?)\s*$", re.IGNORECASE),
        lambda m: f"Acknowledged. Will advise {m.group(1)}",
    ),
    (
        re.compile(r"^\s*ACKNOWLEDGED,\s*WILL\s+ADVISE\s+LINE\s+(\d+)\s*$", re.IGNORECASE),
        lambda m: f"Acknowledged. Will advise tow company line {m.group(1)}",
    ),
    (
        re.compile(r"^\s*ACKNOWLEDGED\.?\s*WILL\s+ADVISE\s+LINE\s+(\d+)\s*$", re.IGNORECASE),
        lambda m: f"Acknowledged. Will advise tow company line {m.group(1)}",
    ),
    (
        re.compile(r"^\s*SANDR(?:\s+TOW)?,?\s+PUTTING\s+BY-OWNER\s+TOW\s*$", re.IGNORECASE),
        "SandR Tow advised they are handling this as a by-owner tow",
    ),
    (
        re.compile(r"^\s*BY-OWNER\s+TOW\s*$", re.IGNORECASE),
        "This is a by-owner tow",
    ),
    (
        re.compile(
            r"^\s*FIRE\s+DEPARTMENT\s+ADVISED\s+PARTY\s+HAS\s+PRIVATE\s+TOW\s+EN\s+ROUTE\s+CAN\s+CLANCY'S\s+AND\s+CLANCY'S\s+BY-OWNER\s+TOW\s*$",
            re.IGNORECASE,
        ),
        "Fire Department advised the party has a private tow en route, so Clancy's tow can be canceled",
    ),
    (
        re.compile(
            r"^\s*FIRE\s+DEPARTMENT\s+ADVISED\s+PARTY\s+HAS\s+PRIVATE\s+TOW\s+EN\s+ROUTE\s*-\s*CAN\s+CLANCY'S\s*(?:/|AND)\s*CLANCY'S\s+BY-OWNER\s+TOW\s*$",
            re.IGNORECASE,
        ),
        "Fire Department advised the party has a private tow en route, so Clancy's tow can be canceled",
    ),
    (
        re.compile(
            r"^\s*REPORTING\s+PARTY\s+STOPPED\s+TO\s+ASSIST\s+AND\s+ADVISE\s+FEMALE\s+IN\s+VEHICLE\s+SAID\s+HER\s+SON\s+IS\s+INJURED\s*$",
            re.IGNORECASE,
        ),
        "The reporting party stopped to help and advised that a woman in the vehicle said her son is injured",
    ),
]


TOKEN_REPLACEMENTS = {
    r"\bRS\b": "right shoulder",
    r"\bHBD\b": "possible DUI (driver may be intoxicated)",
    r"\bPLOT\b": "parking lot",
    r"\bLOT\b": "parking lot",
    r"\bBLU\b": "blue",
    r"\bBRONZE\b": "bronze",
    r"\bDODG\b": "Dodge",
    r"\bCAM\b": "Camaro",
    r"\bCHAV\s*CAM\b": "Chevy Camaro",
    r"\bSUBA\b": "Subaru",
    r"\bSUB\b": "Subaru",
    r"\bMC\b": "motorcycle",
    r"\bETA\b": "estimated arrival in",
    r"\bJNO\b": "just north of",
    r"\bJSO\b": "just south of",
    r"\bJWO\b": "just west of",
    r"\bJEO\b": "just east of",
    r"\bNB\b": "northbound",
    r"\bSB\b": "southbound",
    r"\bEB\b": "eastbound",
    r"\bWB\b": "westbound",
    r"\bRHS\b": "right shoulder",
    r"\bLHS\b": "left shoulder",
    r"\bRP\b": "reporting party",
    r"\bPD\b": "police",
    r"\bTC\b": "traffic collision",
    r"\bTRFC\b": "traffic",
    r"\bVEH\b": "vehicle",
    r"\bVEHS\b": "vehicles",
    r"\bSOLO\b": "single",
    r"\bOTS\b": "off to the side",
    r"\bCON\b": "connector road",
    r"\bLN\b": "lane",
    r"\bLNS\b": "lanes",
    r"\bRD\b": "road",
    r"\bBLKG\b": "blocking",
    r"\bRT\b": "right",
    r"\bOFR\b": "off-ramp",
    r"\bOFFRAMP\b": "off-ramp",
    r"\bSHOLD\b": "shoulder",
    r"\bW/\b": "with",
    r"\bW\s*/\s*": "with ",
    r"\bUNK\b": "unknown",
    r"\bUNKN\b": "unknown",
    r"\bINJ\b": "injuries",
    r"\bNCOMM\b": "communications center",
    r"\bFD\b": "Fire Department",
    r"\bPTY\b": "party",
    r"\bPRVT\b": "private",
    r"\bSANDR\b": "SandR Tow",
    r"\bS\s*AND\s*R\b": "S and R Tow",
    r"\bBOT\b": "by-owner tow",
    r"\bATC\b": "attempted to contact",
    r"\bADV\b": "advise",
    r"\bENRT\b": "en route",
    r"\bCOPIES\b": "advised",
    r"\bCOPY\b": "acknowledged",
    r"\bCB\b": "call back",
    r"\bOO\b": "out of",
    r"\bMULT\b": "multiple",
    r"\bPOSS\b": "possible",
    r"\bPER\b": "according to",
    r"\bSDSO\b": "San Diego Sheriff's Office",
    r"\bSIL\b": "silver",
    r"\bOUTBACK\b": "Outback",
    r"\bSD\b": "sedan",
    r"\bS\d+\b": "unit",
    r"\bC\d+[A-Z]?\b": "unit",
    r"\b\d+[A-Z]\b": "unit",
    r"\b\d+[A-Z]\d\b": "unit",
    r"\bCT\b": "Caltrans",
    r"\bMINS?\b": "minutes",
    r"\bCPZ\b": "closure point",
    r"\bCLSR\b": "closure",
    r"\bINQ\b": "ask",
    r"\bADVS\b": "advised",
    r"\bADVD\b": "advised",
    r"\bADVSD\b": "advised",
    r"\bFB\b": "full blockage",
    r"\bVS\b": "versus",
    r"\bWHI\b": "white",
    r"\bBLK\b": "black",
    r"\bPK\b": "pickup truck",
    r"\bOTURNED\b": "overturned",
    r"\bGRY\b": "gray",
    r"\bHYUN\b": "Hyundai",
    r"\bELN\b": "Elantra",
    r"\bTOTY\b": "Toyota",
    r"\bTOYT\b": "Toyota",
    r"\bTAC\b": "Tacoma",
    r"\bMITSUBITSHI\b": "Mitsubishi",
    r"\bCLANCYS\b": "Clancy's",
    r"\bCDF\b": "Cal Fire",
    r"\bNEG\b": "negative",
    r"\bNVR\b": "no verbal response",
    r"\bITS\b": "it is",
    r"\bCOP\b": "complaint of pain",
    r"\bEXT\s+OF\b": "extent of",
    r"\bINV['’]?D\b": "involved",
    r"\bCAN\s+FIRE\b": "Cal Fire",
    r"\bXRAY\b": "female",
    r"\bGOOD\s+SAM\b": "Good Samaritan",
    r"\bINV\s+PTY\b": "involved party",
    r"\bINV\s+PARTY\b": "involved party",
    r"\bVEHI\b": "vehicle",
    r"\bRDWY\b": "roadway",
    r"\bFWY\b": "freeway",
    r"\bPLT\b": "plate",
    r"\bUTL\b": "unable to locate",
    r"\bSPUN\b": "spun",
    r"\bFAST\b": "fast",
    r"\bMINIVN\b": "minivan",
    r"\bUTL\b": "unable to locate",
    r"\bSPUN\b": "spun",
    r"\bCOPZ\b": "closure point",
    r"\bLMPD\b": "La Mesa Police Department",
    r"\bGRN\b": "green",
    r"\bNISS?\b": "Nissan",
    r"\bROG\b": "Rogue",
    r"\bUSA\b": "update says",
    r"\bMCC\b": "medical command was contacted",
    r"\bPOSS\b": "possible",
    r"\bPLT\b": "license plate",
    r"\b10-97\b": "on scene",
    r"\bWITHSUSPECT\b": "with suspect",
    r"\bWALK\s+INS\b": "walk-in patients",
    r"\bA/?N\b": "an ambulance",
    r"\bNO\s+WALK-IN\s+PATIENTS\b": "reported no walk-in patients",
    r"\bHB\b": "hatchback",
    r"\bINV\b": "involved",
    r"\bFRM\b": "from",
    r"\bFT\b": "feet",
    r"\bCD\b": "center divider",
    r"\bMID\b": "middle",
    r"\bMAZD\b": "Mazda",
    r"\bCX9\b": "CX-9",
    r"\bSEN\b": "Sentra",
    r"\bTK\b": "truck",
    r"\bHRV\b": "HR-V",
    r"\bSGT\b": "sergeant",
    r"\bSTAM\b": "staff",
    r"\bHOV\b": "HOV",
    r"\bAIR\s+BAGS\b": "airbags",
}


CODED_PATTERN = re.compile(
    r"\b(\d{3,4}|NB|SB|EB|WB|RHS|LHS|RP|TC|NCOMM|CPY|JSO|JNO|JWO|ATC|TRFC|UNKN|ENRT|SDSO|CB|MULT|POSS|INJ|OO|ADVS|ADVD|FB)\b",
    re.IGNORECASE,
)


def _is_admin_detail(text):
    if not text:
        return False
    return any(pattern.search(text) for pattern in ADMIN_DETAIL_PATTERNS)


def _to_sentence_case(text):
    text = (text or "").strip()
    if not text:
        return text
    text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text = f"{text}."
    return re.sub(r"([.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)


def _with_article(phrase):
    phrase = (phrase or "").strip()
    if not phrase:
        return phrase
    if re.match(r"^(a|an|the)\b", phrase, re.IGNORECASE):
        return phrase
    article = "an" if phrase[0].lower() in "aeiou" else "a"
    return f"{article} {phrase}"


def _rewrite_vehicle_vs_line(text):
    line = (text or "").strip(" ,;")
    m = re.match(r"^\s*(.+?)\s*,?\s+versus\s+(.+?)\s*$", line, flags=re.IGNORECASE)
    if not m:
        return None
    left = m.group(1).strip(" ,;")
    right = m.group(2).strip(" ,;")
    if not left or not right:
        return None
    left = re.sub(r"^\d+\s+vehicles?\s+traffic\s+collision\s*(?:and)?\s*", "", left, flags=re.IGNORECASE)
    left = re.sub(r"^\d+\s+vehicles?\s*", "", left, flags=re.IGNORECASE)
    left = re.sub(r"^traffic\s+collision\s*(?:and)?\s*", "", left, flags=re.IGNORECASE)
    right = re.sub(r"^unknown\s+vehicle$", "an unknown vehicle", right, flags=re.IGNORECASE)
    return f"A traffic collision involving {_with_article(left)} and {_with_article(right)}"


def _rewrite_common_dispatch_line(text):
    line = (text or "").strip(" ,;.")
    if not line:
        return line

    rules = [
        (
            re.compile(
                r"^small\s+silver\s+hatchback\s+went\s+off\s+the\s+right\s+shoulder\s+down\s+a\s+steep\s+embankment\s+next\s+to\s+a\s+nursery(?:\s+visible\s+if\s+you\s+walk\s+up\s+to\s+the\s+right\s+shoulder)?$",
                re.IGNORECASE,
            ),
            "A small silver hatchback went off the right shoulder down a steep embankment beside a nursery",
        ),
        (
            re.compile(r"^solo\s+vehicle\s+involved$", re.IGNORECASE),
            "Single vehicle involved in the incident",
        ),
        (
            re.compile(r"^communications\s+center$", re.IGNORECASE),
            "No communications at this time",
        ),
        (
            re.compile(
                r"^employee\s+at\s+tree\s+lot\s+vehicle\s+landed\s+in\s+back\s+lot\s+and\s+female\s+driver\s+is\s+(?:passed\s+out|unconscious)$",
                re.IGNORECASE,
            ),
            "An employee at the tree lot reported the vehicle landed in the back lot and the female driver is unconscious",
        ),
        (
            re.compile(r"^[A-Z]?\d+\s*-\s*(\d+)\s*;?\s*from\s+the\s+main\s+lanes$", re.IGNORECASE),
            lambda m: f"The vehicle is approximately {m.group(1)} feet from the main lanes",
        ),
        (
            re.compile(
                r"^[A-Z]?\d+\s*-\s*\d+\s+need\s*,?\s+about\s+(\d+)\s*-\s*(\d+)\s+feet\s+off\s+the\s+roadway$",
                re.IGNORECASE,
            ),
            lambda m: f"Assistance needed with a vehicle about {m.group(1)} to {m.group(2)} feet off the roadway",
        ),
        (
            re.compile(r"^[*.\s]*roadway[*.\s]*$", re.IGNORECASE),
            "Requesting a rotation for a roadway issue; contact number provided",
        ),
        (
            re.compile(
                r"^a?\s*collision\s+involving\s+(\d+)\s+vehicles?\s+traffic\s+collision\s+and\s+(.+?)\s+and\s+an\s+unknown\s+vehicle$",
                re.IGNORECASE,
            ),
            lambda m: f"A {m.group(1)}-vehicle traffic collision involving {m.group(2)} and an unknown vehicle",
        ),
        (
            re.compile(r"^blocking\s+right\s+off-ramp\s+lane$", re.IGNORECASE),
            "Blocking the right off-ramp lane",
        ),
        (
            re.compile(r"^off-ramp\s+is\s+blocked$", re.IGNORECASE),
            "The off-ramp is blocked",
        ),
        (
            re.compile(
                r"^will\s+be\s+opening\s+the\s+road\s+in\s+about\s+(\d+)\s+minutes\s+and\s+unit\s+closure\s+point$",
                re.IGNORECASE,
            ),
            lambda m: f"The road will be reopened in about {m.group(1)} minutes, and the unit is at the closure point",
        ),
        (
            re.compile(
                r"^(white|black|gray|grey|silver|red)\s+sedan\s+and\s+flashers\s+on\s+and\s+right\s+lane$",
                re.IGNORECASE,
            ),
            lambda m: f"A {m.group(1).lower()} sedan was stopped in the right lane with hazard lights on",
        ),
        (
            re.compile(r"^one\s+vehicle\s+in\s+#?1\s+lane\s+other\s+vehicle\s+on\s+right\s+shoulder$", re.IGNORECASE),
            "One vehicle is in lane 1 and the other is on the right shoulder",
        ),
        (
            re.compile(
                r"^additional\s+reporting\s+party\s+advised\s+it\s+is\s+a\s+possible\s+female\s+crying\s+with\s+her\s+kid\s+unknown\s+if\s+injuries\s+central\s+as\s+a\s+precaution$",
                re.IGNORECASE,
            ),
            "An additional reporting party advised there is a woman crying with her child, and injuries are unknown; Central was notified as a precaution",
        ),
        (
            re.compile(
                r"^reporting\s+party\s+stopped\s+to\s+assist\s+and\s+advise\s+female\s+in\s+vehicle\s+said\s+her\s+son\s+is\s+injured$",
                re.IGNORECASE,
            ),
            "A caller stopped to assist and advised that a woman in the vehicle said her son is injured",
        ),
        (
            re.compile(
                r"^reporting\s+party\s+in\s+a\s+(.+?)\s+and\s+daughter\s+was\s+behind\s+her\s+and\s+was\s+hit\s+in\s+a\s+(.+?)\s+and\s+hit\s+by\s+unknown\s+vehicle$",
                re.IGNORECASE,
            ),
            lambda m: f"The reporting party was in a {m.group(1)}. Her daughter was behind her in a {m.group(2)} and was hit by an unknown vehicle",
        ),
        (
            re.compile(
                r"^additional\s+involved\s+party\s+white\s+hond\s+pilot\s+negative\s+injuries\s+vehicle\s+still\s+driveable$",
                re.IGNORECASE,
            ),
            "An additional involved party in a white Honda Pilot reported no injuries, and the vehicle is still drivable",
        ),
        (
            re.compile(
                r"^additional\s+involved\s+party\s+white\s+honda\s+pilot\s+negative\s+injuries\s+vehicle\s+still\s+driveable$",
                re.IGNORECASE,
            ),
            "An additional involved party in a white Honda Pilot reported no injuries, and the vehicle is still drivable",
        ),
        (
            re.compile(
                r"^additional\s+inv\s+party\s+white\s+honda\s+pilot\s+negative\s+injuries\s+vehicle\s+still\s+driveable$",
                re.IGNORECASE,
            ),
            "An additional involved party in a white Honda Pilot reported no injuries, and the vehicle is still drivable",
        ),
        (
            re.compile(r"^unit\s+heavy\s+traffic$", re.IGNORECASE),
            "There is heavy traffic reported",
        ),
        (
            re.compile(r"^unit\s+full\s+blockage\s+for\s+\w+\s+major\s+rear\s+end$", re.IGNORECASE),
            "There is a full blockage due to a major rear-end collision",
        ),
        (
            re.compile(r"^central$", re.IGNORECASE),
            "Central dispatch was notified",
        ),
        (
            re.compile(r"^unit\s+fire\s+will\s+need\s+extraction\s+tools$", re.IGNORECASE),
            "Fire crews will need extraction tools at the scene",
        ),
        (
            re.compile(
                r"^unit\s+will\s+need\s+units\s+to\s+divert\s+traffic\s+off\s+traffic\s+is\s+backed\s+up\s+and\s+medics\s+unable\s+to\s+get\s+to\s+location$",
                re.IGNORECASE,
            ),
            "Traffic units are needed to divert traffic because the roadway is backed up and medics cannot reach the scene",
        ),
        (
            re.compile(r"^la\s+mesa\s+police\s+department$", re.IGNORECASE),
            "La Mesa Police Department provided an update",
        ),
        (
            re.compile(r"^la\s+mesa\s+police\s+department\s+closure\s+point\s+line\s+(\d+)$", re.IGNORECASE),
            lambda m: f"La Mesa Police Department is at the closure point on line {m.group(1)}",
        ),
        (
            re.compile(r"^countywide\s+with\s+(\d+)\s+full\s+blockage'?s?$", re.IGNORECASE),
            lambda m: f"Countywide reports {m.group(1)} full blockages",
        ),
        (
            re.compile(
                r"^unit\s+vehicle\s+will\s+be\s+missing\s+front\s+bumper\s+along\s+with\s+front\s+license\s+plate$",
                re.IGNORECASE,
            ),
            "The vehicle is missing its front bumper and front license plate",
        ),
        (
            re.compile(
                r"^according\s+to\s+la\s+mesa\s+police\s+department\s+they\s+have\s+not\s+received\s+any\s+flock\s+hits\s+for\s+the\s+vehicle\s+after\s+exiting\s+the\s+freeway$",
                re.IGNORECASE,
            ),
            "According to La Mesa Police Department, there have been no Flock camera hits for the vehicle after it exited the freeway",
        ),
        (
            re.compile(
                r"^la\s+mesa\s+police\s+department\s+on\s+scene\s+with\s+suspect\s+vehicle\s+and\s+vehicle\s+is\s+(.+)$",
                re.IGNORECASE,
            ),
            lambda m: f"La Mesa Police Department is on scene with the suspect vehicle; the vehicle is at {m.group(1)}",
        ),
        (
            re.compile(
                r"^la\s+mesa\s+police\s+department\s+making\s+contact\s+with\s+a\s+party\s+seen\s+walking\s+away\s+from\s+the\s+vehicle\s+working\s+to\s+confirm\s+if\s+party\s+is\s+the\s+driver\s+and\s+unconfirmed\s+for\s+now$",
                re.IGNORECASE,
            ),
            "La Mesa Police Department is contacting a person seen walking away from the vehicle and is working to confirm whether that person is the driver; this is unconfirmed for now",
        ),
        (
            re.compile(r"^unit\s+(\d+)\s+evidence\s+(\d+)\s+regular$", re.IGNORECASE),
            lambda m: f"{m.group(1)} vehicle was towed for evidence and {m.group(2)} vehicle was towed routinely",
        ),
        (
            re.compile(r"^unit\s+for\s+evidence$", re.IGNORECASE),
            "A vehicle was towed for evidence",
        ),
        (
            re.compile(r"^unit\s*-\s*for\s+evidence$", re.IGNORECASE),
            "A vehicle was towed for evidence",
        ),
        (
            re.compile(r"^countywide\s+closure\s+point\s+all$", re.IGNORECASE),
            "Countywide update: all units are assigned to their closure points",
        ),
        (
            re.compile(r"^(sharp\s+grossmont|ucsd\s+east|paradise\s+valley|scripps\s+mercy)\s+negative\s+walk-in\s+patients$", re.IGNORECASE),
            lambda m: f"{m.group(1).title()} reported no walk-in patients",
        ),
        (
            re.compile(r"^has\s+closed\s+their\s+incident$", re.IGNORECASE),
            "The incident has been closed",
        ),
        (
            re.compile(
                r"^unit\s+unit\s+following\s+evidence\s+to\s+tow\s+yard\s+unit\s+can\s+open\s+lanes$",
                re.IGNORECASE,
            ),
            "Evidence has been taken to the tow yard and lanes can reopen",
        ),
        (
            re.compile(
                r"^unit(?:-unit)?\s+following\s+evidence\s+to\s+tow\s+yard\s+unit\s+can\s+open\s+lanes$",
                re.IGNORECASE,
            ),
            "Evidence has been taken to the tow yard and lanes can reopen",
        ),
        (
            re.compile(r"^unit\s+following\s+evidence\s+tow$", re.IGNORECASE),
            "Following evidence has been taken to the towing yard",
        ),
    ]

    for pattern, repl in rules:
        m = pattern.match(line)
        if not m:
            continue
        return repl(m) if callable(repl) else repl
    return line


def _to_plain_english(text):
    if not text:
        return "No detail provided."

    raw_text = str(text)
    raw_compact = re.sub(r"\s+", " ", raw_text).strip()
    raw_rules = [
        (
            re.compile(r"^MULTI\s+VEH\s+TC\s+BLKG\s+MID\s+LANES\s*-\s*NO\s+VEH\s+DESC$", re.IGNORECASE),
            "A multi-vehicle traffic collision was reported blocking the middle lanes. No vehicle descriptions were available yet",
        ),
        (
            re.compile(r"^\[?Appended,\s*[^\]]+\]?\s*\[?\d+\]?\s*3\s+VEH\s+TC\s*//\s*RED\s+UNK\s+PK\s+TK\s+ON\s+RHS\s+VS\s+GRY\s+NISS\s+SEN\s+VS\s+UNK\s+VEH$", re.IGNORECASE),
            "A 3-vehicle crash was reported involving a red pickup truck on the right shoulder, a gray Nissan Sentra, and an unknown third vehicle",
        ),
        (
            re.compile(r"^\[?Appended,\s*[^\]]+\]?\s*\[?\d+\]?\s*GRY\s+NISS\s+SEN\s+WAS\s+HIGH\s+SPEEDS\s+PRIOR\s+TO\s+TC$", re.IGNORECASE),
            "The gray Nissan Sentra was reportedly speeding before the crash",
        ),
        (
            re.compile(r"^\[?Appended,\s*[^\]]+\]?\s*\[?\d+\]?\s*2\s+VEH\s+1125\s+MIDDLE\s+LANE$", re.IGNORECASE),
            "Two vehicles were reported in the middle lane",
        ),
        (
            re.compile(r"^2\s+VEH\s+TC\s*/\s*ONE\s+IN\s+CD\s+AND\s+ONE\s+ON\s+RHS(?:\s+\[Shared\])?$", re.IGNORECASE),
            "A 2-vehicle crash was reported, with one vehicle in the center divider and the other on the right shoulder",
        ),
        (
            re.compile(r"^1039\s+MCC\s*-\s*AIR\s+BAGS\s+FOR\s+VEH\s+ON\s+RHS(?:\s+\[Shared\])?$", re.IGNORECASE),
            "Medical command was contacted after airbags were reported deployed in the vehicle on the right shoulder",
        ),
        (
            re.compile(r"^3\s+VEH\s+TC\s+POSSIBLY\s+MORE(?:\s+\[Shared\])?$", re.IGNORECASE),
            "At least 3 vehicles were reported involved, and possibly more",
        ),
        (
            re.compile(r"^RP\s+IN\s+A\s+GRY\s+MAZD\s+SUV\s+CX9\s+ON\s+RHS\s+ANOTHER\s+VEH\s+ON\s+RHS\s+AND\s+3RD\s+VEH\s+IN\s+CD(?:\s+\[Shared\])?$", re.IGNORECASE),
            "The reporting party said they were in a gray Mazda CX-9 on the right shoulder, with another vehicle also on the right shoulder and a third in the center divider",
        ),
        (
            re.compile(r"^INV\s+IN\s+MAZD\s+SUV\s+DECLINED\s+1141\s+UNK\s+IF\s+VEH\s+IS\s+DRIVEABLE\s*//\s*HAS\s+HAZARDS\s+ON(?:\s+\[Shared\])?$", re.IGNORECASE),
            "An involved person in the Mazda SUV declined medical help. It is unclear whether the vehicle can be driven, and its hazard lights are on",
        ),
        (
            re.compile(r"^INV\s+IN\s+MAZD\s+ADV\s+BOTH\s+SIDES\s+OF\s+HER\s+VEH\s+WERE\s+HIT\s+UNK\s+WHAT\s+TYPES\s+OF\s+VEHS(?:\s+\[Shared\])?$", re.IGNORECASE),
            "The Mazda driver said both sides of her vehicle were hit, but she could not identify the other vehicles",
        ),
        (
            re.compile(r"^\[CHP\]\s*-\s*OFF\s+DUTY\s+STAM\s+SGT\s+IN\s+GRY\s+TESLA\s*-\s*NOT\s+INV\s*/\s*GRY\s+HOND\s+HRV\s+IN\s+CD\s+BRO\s+4DR\s+SD\s+ON\s+RHS\s*//\s*RED\s+PK\s+TK\s+ON\s+RHS\s+UNK\s+IF\s+INV(?:\s+\[Shared\])?$", re.IGNORECASE),
            "An off-duty CHP sergeant in a gray Tesla was on scene but not involved. A gray Honda HR-V was in the center divider, a damaged 4-door sedan was on the right shoulder, and it was still unclear whether the red pickup truck on the shoulder was involved",
        ),
        (
            re.compile(r"^\[CHP\]\s*-\s*Problem\s+changed\s+from\s+1183-?Trfc\s+Collision-?Unkn\s+Inj\s+to\s+1179-?Trfc\s+Collision-?1141\s+Enrt(?:\s+\[Shared\])?$", re.IGNORECASE),
            "The incident was updated from unknown injuries to units and medical help en route",
        ),
        (
            re.compile(r"^A\d+-\d+\s+97\s+IN\s+THE\s+CD\s*,\s*FD\s+BLOCKING\s+THE\s+HOV\s+LN(?:\s+\[Shared\])?$", re.IGNORECASE),
            "A unit reported a vehicle in the center divider, and the Fire Department was blocking the HOV lane",
        ),
        (
            re.compile(r"^\d+-\d+\s+START\s+1185(?:\s+\[Shared\])?$", re.IGNORECASE),
            "An officer started the tow request",
        ),
        (
            re.compile(r"^\[Rotation\s+Request\s+Comment\]\s*\*\*\s*1039\s+PACIFIC\s+AUTOW\s+\d{3}-\d{3}-\d{4}(?:\s+\[Shared\])?$", re.IGNORECASE),
            "Tow truck requested from Pacific Auto",
        ),
    ]
    for pattern, replacement in raw_rules:
        if pattern.match(raw_compact):
            return replacement + "."
    if re.search(r"\b1039\s+\d{2,4}\s*-\s*51\b", raw_compact, re.IGNORECASE):
        return "Dispatch advised Unit 51."
    if re.search(r"^(?:\[?\d+\]?\s*)?51\.?(?:\s*\[.*\])?$", raw_compact, re.IGNORECASE):
        return "Unit 51."
    had_leading_index = bool(re.match(r"^\s*\[\d+\]", raw_text))
    cleaned = raw_text
    cleaned = re.sub(r"\[(?:Shared|Notification|Rotation Request Comment)\]", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\[CHP\]\s*[-:]?\s*", "CHP ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*\[Appended,\s*[^\]]+\]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^\s*\[\d+\]\s*", "", cleaned)
    cleaned = re.sub(r"^[\[\]\s,;:.-]+", "", cleaned)
    cleaned = re.sub(r"\[[^\]]*\]", " ", cleaned)
    cleaned = cleaned.replace("[", " ").replace("]", " ")
    cleaned = cleaned.replace("^", " ")
    cleaned = cleaned.replace("//", " / ")
    if had_leading_index:
        cleaned = re.sub(r"^\d+\s*[:.-]?\s*", "", cleaned)
    cleaned = re.sub(r"\b\d{3,5}[A-Z]?\b", " ", cleaned)
    cleaned = re.sub(r"\b911\s+PREFIX\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"-\s*(\d{3,5}[A-Z]?)\b", " ", cleaned)
    cleaned = re.sub(r"\b([A-Za-z0-9/]+)\s+X\s+([A-Za-z0-9/]+)\b", r"\1 and \2", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    for pattern, repl in PHRASE_REPLACEMENTS:
        cleaned = pattern.sub(repl, cleaned)

    for pattern, repl in TOKEN_REPLACEMENTS.items():
        cleaned = re.sub(pattern, repl, cleaned, flags=re.IGNORECASE)

    for pattern, repl in PHRASE_REPLACEMENTS:
        cleaned = pattern.sub(repl, cleaned)

    cleaned = re.sub(r"\s*/\s*", " and ", cleaned)
    cleaned = re.sub(r"\s+-\s+", " ", cleaned)
    cleaned = re.sub(r"^-+\s*", "", cleaned)
    cleaned = re.sub(r"(?<!\w)-(?=unit\b)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bunit-unit\b", "unit", cleaned, flags=re.IGNORECASE)

    vehicle_sentence = _rewrite_vehicle_vs_line(cleaned)
    if vehicle_sentence:
        cleaned = vehicle_sentence
    cleaned = _rewrite_common_dispatch_line(cleaned)

    cleaned = re.sub(r"(?<=\s)-(?=\s)", " ", cleaned)
    cleaned = re.sub(r"\bX\s*(\d+)\b", r"\1 times", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -;:,.")
    cleaned = re.sub(r"\btraffic collision-\s*en route\b", "traffic collision with CHP units en route", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\btraffic collision[-\\s]+no injuries\b", "traffic collision with no reported injuries", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bsolo\s+vehicle\b", "single vehicle", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bsolo\s+mc\b", "single motorcycle", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmc\b", "motorcycle", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brider\b", "motorcycle rider", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(\d+)\s+veh\s+tc\b", r"\1-vehicle traffic collision", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bmulti\s+veh\b", "multi-vehicle", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b3\s+vehicle\s+traffic collision\b", "3-vehicle traffic collision", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b2\s+vehicle\s+traffic collision\b", "2-vehicle traffic collision", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bno\s+veh\s+desc\b", "no vehicle description yet", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bpossibly\s+more\b", "possibly more vehicles involved", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bhigh\s+speeds\s+prior\s+to\s+traffic collision\b", "was reportedly speeding before the crash", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdeclined\s+unknown if vehicle is drivable\b", "declined medical help; it is unknown whether the vehicle is drivable", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bhas\s+hazards\s+on\b", "hazard lights are on", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bboth\s+sides\s+of\s+her\s+vehicle\s+were\s+hit\b", "both sides of her vehicle were hit", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bunknown\s+what\s+types\s+of\s+vehicles\b", "it is unclear what types of vehicles hit her", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bFire Department\s+blocking\s+the\s+HOV\s+lane\b", "the Fire Department is blocking the HOV lane", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bstart\s+1185\b", "started the tow request", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\brotation\s+request\s+comment\b", "Tow truck requested", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bproblem changed from\s+traffic collision-?unknown injuries\s+to\s+traffic collision with CHP units en route\b", "The incident was updated from unknown injuries to CHP units and medical response en route", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\binjuriesuries\b", "injuries", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\binjuries['’]s\b", "injuries", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bnegative injuries\b", "no injuries", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bdriveable\b", "drivable", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bo\s+and\s+turn(ed)?\b", "overturned", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bo\s+and\s+turned\b", "overturned", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bon\s+top\s+on\b", "on top of", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\boverturned\s+on\s+right\s+shoulder\s+ditch", "overturned on the right shoulder in a ditch", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(
        r"\b(gray|grey|white|black|red|silver)\s+unknown\s+(sedan|SUV|vehicle)\b",
        r"an unknown \1 \2",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\binjuries['’]s\b", "injuries", cleaned, flags=re.IGNORECASE)
    special_rules = [
        (
            re.compile(r"^multi-vehicle traffic collision blocking middle lanes no vehicle description yet$", re.IGNORECASE),
            "A multi-vehicle traffic collision is blocking the middle lanes. No vehicle descriptions were available yet",
        ),
        (
            re.compile(r"^3-vehicle traffic collision and red unknown pickup truck on right shoulder versus gray nissan sentra versus unknown vehicle$", re.IGNORECASE),
            "A 3-vehicle crash was reported involving a red pickup truck on the right shoulder, a gray Nissan Sentra, and an unknown third vehicle",
        ),
        (
            re.compile(r"^gray nissan sentra was reportedly speeding before the crash$", re.IGNORECASE),
            "The gray Nissan Sentra was reportedly speeding before the crash",
        ),
        (
            re.compile(r"^2 vehicle middle lane$", re.IGNORECASE),
            "Two vehicles were reported in the middle lane",
        ),
        (
            re.compile(r"^2-vehicle traffic collision and one in center divider and one on right shoulder$", re.IGNORECASE),
            "A 2-vehicle collision was reported, with one vehicle in the center divider and the other on the right shoulder",
        ),
        (
            re.compile(r"^medical command was contacted[- ]airbags for vehicle on right shoulder$", re.IGNORECASE),
            "Medical command was contacted, and airbags were reported deployed in the vehicle on the right shoulder",
        ),
        (
            re.compile(r"^3 vehicle traffic collision possibly more vehicles involved$", re.IGNORECASE),
            "At least 3 vehicles were reported involved, and possibly more",
        ),
        (
            re.compile(r"^reporting party in a gray mazda suv cx-9 on right shoulder another vehicle on right shoulder and 3rd vehicle in center divider$", re.IGNORECASE),
            "The reporting party said they were in a gray Mazda CX-9 on the right shoulder, with another vehicle also on the right shoulder and a third in the center divider",
        ),
        (
            re.compile(r"^involved in mazda suv declined medical help; it is unknown whether the vehicle is drivable and hazard lights are on$", re.IGNORECASE),
            "An involved person in the Mazda SUV declined medical help. It is unclear whether the vehicle can be driven, and its hazard lights are on",
        ),
        (
            re.compile(r"^involved in mazda advise both sides of her vehicle were hit it is unclear what types of vehicles hit her$", re.IGNORECASE),
            "The Mazda driver said both sides of her vehicle were hit, but she could not identify the other vehicles",
        ),
        (
            re.compile(r"^CHP off duty staff sergeant in gray tesla not involved and gray honda hrv in center divider bro 4dr sedan on right shoulder and red pickup truck on right shoulder unknown if involved$", re.IGNORECASE),
            "An off-duty CHP sergeant in a gray Tesla was on scene but not involved. A gray Honda HR-V was in the center divider, a damaged 4-door sedan was on the right shoulder, and it was still unclear whether the red pickup truck on the shoulder was involved",
        ),
        (
            re.compile(r"^CHP the incident was updated from unknown injuries to CHP units and medical response en route$", re.IGNORECASE),
            "The incident was updated from unknown injuries to units and medical help en route",
        ),
        (
            re.compile(r"^a87 in the center divider , the Fire Department is blocking the hov lane$", re.IGNORECASE),
            "A unit reported a vehicle in the center divider, and the Fire Department was blocking the HOV lane",
        ),
        (
            re.compile(r"^87-7 started the tow request$", re.IGNORECASE),
            "An officer started the tow request",
        ),
        (
            re.compile(r"^tow truck requested \*\* pacific autow$", re.IGNORECASE),
            "Tow truck requested from Pacific Auto",
        ),
    ]

    for pattern, replacement in special_rules:
        if pattern.match(cleaned):
            cleaned = replacement
            break

    if not cleaned:
        return "Dispatch update received."

    lowered = cleaned.lower()
    lowered = re.sub(r"\bchp\b", "CHP", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsdpd\b", "San Diego Police Department", lowered, flags=re.IGNORECASE)
    lowered = re.sub(
        r"\bsan diego sheriff's office\b",
        "San Diego Sheriff's Office",
        lowered,
        flags=re.IGNORECASE,
    )
    lowered = re.sub(r"\balberstsons?\b", "Albertsons", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\balbertsons?\b", "Albertsons", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsweewater\b", "Sweetwater", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsweetwater road\b", "Sweetwater Road", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\borasco\b", "Orosco", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bguejito\b", "Guejito", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bpulling into\b", "pulled into", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bcaltrans\b", "Caltrans", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsuv\b", "SUV", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\biphone\b", "iPhone", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\btoyota\b", "Toyota", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\btundra\b", "Tundra", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bford\b", "Ford", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bgood samaritan\b", "Good Samaritan", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\btacoma\b", "Tacoma", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bmitsubishi\b", "Mitsubishi", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bhyundai\b", "Hyundai", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\belantra\b", "Elantra", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bjeep\b", "Jeep", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bwagoneer\b", "Wagoneer", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bhonda\b", "Honda", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bhond\b", "Honda", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bchev\b", "Chevrolet", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsuzi\b", "Suzuki", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\btrail\s*blazer\b", "Trailblazer", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bpilot\b", "Pilot", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bfire department\b", "Fire Department", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bcal fire\b", "Cal Fire", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bcentral\b", "Central", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bla mesa police department\b", "La Mesa Police Department", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bflock\b", "Flock", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bucsd\b", "UCSD", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\blois street\b", "Lois Street", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsharp grossmont\b", "Sharp Grossmont", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bparadise valley\b", "Paradise Valley", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bscripps mercy\b", "Scripps Mercy", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bucsd east\b", "UCSD East", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bla mesa\b", "La Mesa", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsr\s*(\d+)\b", r"State Route \1", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bstate route\s*(\d+)\s+([nsew])\b", r"State Route \1 \2", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bave\b", "Avenue", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bln\b", "Lane", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\band unknown vehicle\b", "and an unknown vehicle", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bclancy's\b", "Clancy's", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bclancy's tow\b", "Clancy's Tow", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bsandr tow\b", "SandR Tow", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bs and r tow\b", "SandR Tow", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bmdc\b", "mobile data computer", lowered, flags=re.IGNORECASE)
    lowered = re.sub(r"\bbased on\b", "Based on", lowered, flags=re.IGNORECASE)
    return _to_sentence_case(lowered)


def translate_label(text):
    translated = _to_plain_english(text)
    return translated[:-1] if translated.endswith(".") else translated


def _contains_dispatch_code(text):
    return bool(CODED_PATTERN.search(text or ""))


def _is_summary_usable(text):
    summary = (text or "").strip()
    if not summary:
        return False
    if summary.startswith("AI interpretation unavailable:"):
        return False
    if _contains_dispatch_code(summary):
        return False
    if _is_admin_detail(summary):
        return False
    return True


def _strip_terminal_punctuation(text):
    return re.sub(r"[.!\s]+$", "", (text or "").strip())


def _format_incident_time(raw_time):
    text = re.sub(r"\s+", " ", (raw_time or "").strip())
    if not text:
        return "an unknown time"
    for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y %I:%M %p"):
        try:
            dt = datetime.strptime(text, fmt)
            rendered = dt.strftime("%B %d, %Y at %I:%M %p")
            rendered = re.sub(r"\b0(\d),", r"\1,", rendered)
            rendered = re.sub(r"\bat 0(\d):", r"at \1:", rendered)
            return rendered
        except ValueError:
            continue
    return text


def _format_incident_date_time_parts(raw_time):
    text = re.sub(r"\s+", " ", (raw_time or "").strip())
    if not text:
        return "", ""
    for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y %I:%M %p"):
        try:
            dt = datetime.strptime(text, fmt)
            date_part = dt.strftime("%B %d, %Y")
            date_part = re.sub(r"\b0(\d),", r"\1,", date_part)
            time_part = dt.strftime("%I:%M %p")
            time_part = re.sub(r"^0", "", time_part)
            return date_part, time_part
        except ValueError:
            continue
    return text, ""


def _format_location(raw_location):
    text = (raw_location or "").strip()
    if not text:
        return "an unknown location"
    text = re.sub(r"\bSR\s*(\d+)\b", r"State Route \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bState Route\s*(\d+)\s+W\b", r"westbound State Route \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bState Route\s*(\d+)\s+E\b", r"eastbound State Route \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bState Route\s*(\d+)\s+N\b", r"northbound State Route \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bState Route\s*(\d+)\s+S\b", r"southbound State Route \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bOFR\b", "off-ramp", text, flags=re.IGNORECASE)
    text = re.sub(r"\bAVE\b", "Avenue", text, flags=re.IGNORECASE)
    text = re.sub(r"\bRD\b", "Road", text, flags=re.IGNORECASE)
    text = re.sub(r"\bLN\b", "Lane", text, flags=re.IGNORECASE)
    text = re.sub(r"\bST\b", "Street", text, flags=re.IGNORECASE)
    text = re.sub(r"\bFWY\b", "freeway", text, flags=re.IGNORECASE)
    text = re.sub(r"\bWO\b", "west of", text, flags=re.IGNORECASE)
    text = re.sub(r"\bEO\b", "east of", text, flags=re.IGNORECASE)
    text = re.sub(r"\bNO\b", "north of", text, flags=re.IGNORECASE)
    text = re.sub(r"\bSO\b", "south of", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*/\s*", " and ", text)
    text = re.sub(r"\s+and\s+midspan\b", " at the midspan of the bridge", text, flags=re.IGNORECASE)
    text = re.sub(
        r"^(.+?)\s+N\s+off-ramp\s+and\s+(.+)$",
        r"the north off-ramp of \1 near \2",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(west|east|north|south)\s+of\s*$", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _detail_sort_key(detail):
    raw_time = re.sub(r"\s+", " ", ((detail or {}).get("time") or "").strip())
    for fmt in ("%b %d %Y %I:%M%p", "%b %d %Y %I:%M %p"):
        try:
            return (0, datetime.strptime(raw_time, fmt))
        except ValueError:
            continue
    return (1, raw_time)


def _normalize_summary_detail(text):
    detail = _strip_terminal_punctuation(text)
    detail = re.sub(r"^A\s+", "a ", detail)
    detail = re.sub(r"\binvolving\s+and\s+", "involving ", detail, flags=re.IGNORECASE)
    detail = re.sub(
        r"\b(gray|grey|white|black|red|silver)\s+unknown\s+(sedan|SUV|vehicle)\b",
        r"an unknown \1 \2",
        detail,
        flags=re.IGNORECASE,
    )
    return detail


def local_summary(incident):
    details = sorted(incident.get("details") or [], key=_detail_sort_key)
    timeline_plain = []
    for d in details:
        raw = (d.get("text") or "").strip()
        if not raw or _is_admin_detail(raw):
            continue
        timeline_plain.append(_to_plain_english(raw))

    primary_detail = next(
        (
            t
            for t in timeline_plain
            if not re.search(r"\btow\b|\bincident has been closed\b|\bwalk-in patients\b", t, re.IGNORECASE)
        ),
        "",
    )
    first_detail = primary_detail or (timeline_plain[0] if timeline_plain else "No detailed updates yet.")
    incident_type = _strip_terminal_punctuation(translate_label(incident.get("type") or "Incident")).lower()
    incident_type = re.sub(r"\bchp\b", "CHP", incident_type, flags=re.IGNORECASE)
    incident_type = re.sub(r"\s+with CHP units en route\b", "", incident_type, flags=re.IGNORECASE)
    when = _format_incident_time(incident.get("time"))
    date_part, time_part = _format_incident_date_time_parts(incident.get("time"))
    location = _format_location(incident.get("location"))
    area = (incident.get("area") or "an unknown area").strip()
    first_detail_clean = _normalize_summary_detail(first_detail)

    if "traffic hazard" in incident_type and date_part and time_part:
        position_line = next(
            (
                t
                for t in timeline_plain
                if re.search(r"right-hand side|off-ramp|right lane", t, re.IGNORECASE)
                and not re.search(r"unclear|\?", t, re.IGNORECASE)
            ),
            "",
        )
        tow_line = next((t for t in timeline_plain if re.search(r"\btow\b", t, re.IGNORECASE)), "")
        unclear_line = next((t for t in timeline_plain if re.search(r"unclear|\?", t, re.IGNORECASE)), "")

        lines = [f"On {date_part}, at around {time_part}, a traffic hazard was reported on {location} in {area}."]
        if position_line:
            pos_phrase = _normalize_summary_detail(position_line).lower()
            pos_phrase = re.sub(r"^the vehicle was on\s+", "", pos_phrase)
            pos_phrase = re.sub(r"^the\s+", "", pos_phrase)
            lines.append(f"It appears a vehicle was involved and was located on the {pos_phrase}.")
        else:
            hazard_detail = first_detail_clean.capitalize()
            if re.match(r"^(White|Black|Gray|Grey|Silver|Red)\s+sedan\b", hazard_detail):
                hazard_detail = f"A {hazard_detail[0].lower()}{hazard_detail[1:]}"
            lines.append(f"{hazard_detail}.")
        if tow_line:
            lines.append("Tow services were dispatched to the scene shortly after the report.")
        if unclear_line:
            lines.append("Some details about the exact position of the vehicle were initially unclear but were later confirmed.")
        elif len(timeline_plain) <= 2:
            lines.append(
                "It is unclear why the vehicle was stopped, but the situation was causing a potential safety concern for other motorists."
            )
        return " ".join(lines)

    if date_part and time_part:
        lines = [f"On {date_part}, at approximately {time_part}, CHP received reports of a {incident_type} near {location} in {area}."]
    else:
        lines = [f"On {when}, CHP received reports of a {incident_type} near {location} in {area}."]
    lines.append(f"Initial reports indicated that {first_detail_clean}.")

    injury_line = next((t for t in timeline_plain if re.search(r"\binjur", t, re.IGNORECASE)), "")
    if injury_line:
        injury_clean = _normalize_summary_detail(injury_line)
        if injury_clean.lower() == first_detail_clean.lower():
            pass
        elif re.search(r"\bno injuries\b", injury_clean, re.IGNORECASE):
            lines.append("At least one involved party reported no injuries, while other injury details were still being checked.")
        else:
            lines.append(f"Early updates indicated possible injuries: {injury_clean}.")

    response_line = next(
        (
            t
            for t in timeline_plain
            if re.search(r"fire crews|extraction tools|medics|divert traffic", t, re.IGNORECASE)
        ),
        "",
    )
    if response_line:
        response_clean = _normalize_summary_detail(response_line)
        if response_clean.lower() != first_detail_clean.lower():
            lines.append(response_clean.capitalize() + ".")

    investigation_line = next(
        (
            t
            for t in reversed(timeline_plain)
            if re.search(r"evidence tow|tow yard|suspect vehicle|incident has been closed|walk-in patients", t, re.IGNORECASE)
        ),
        "",
    )
    if investigation_line:
        investigation_clean = _normalize_summary_detail(investigation_line)
        if investigation_clean.lower() != first_detail_clean.lower():
            lines.append(investigation_clean.capitalize() + ".")

    return " ".join(lines)


def _chat_with_openai(prompt, api_key):
    try:
        try:
            from openai import OpenAI  # openai>=1.0.0

            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content or ""
        except ImportError:
            import openai  # legacy openai<1.0.0

            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
            )
            return resp["choices"][0]["message"]["content"] or ""
    except Exception as exc:
        return f"AI interpretation unavailable: {exc}"


def interpret_incident(incident):
    if not incident:
        return "Incident not found."

    safe_summary = local_summary(incident)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return safe_summary

    details_lines = []
    for d in incident.get("details", []):
        dt = d.get("time") or "Unknown time"
        txt = d.get("text") or "No detail text"
        details_lines.append(f"- {dt}: {txt}")

    details_text = "\n".join(details_lines) if details_lines else "- No details available."

    prompt = f"""
You are translating CHP CAD shorthand into plain English.
Write 1 short paragraph (3-5 sentences) that explains what happened in clear, natural language.
Keep all facts grounded in the incident data. If information is uncertain, say that explicitly.
Do not include internal administrative notes like door/gate codes or RCARD details.
Do not use CHP/CAD abbreviations in the output.
Do not output bullet points.

Incident:
Type: {incident['type']}
Time: {incident.get('time')}
Location: {incident['location']}
Description: {incident['desc']}
Area: {incident.get('area')}

Details:
{details_text}
"""

    content = _chat_with_openai(prompt, api_key)
    if not content or content.startswith("AI interpretation unavailable:"):
        return safe_summary
    if not _is_summary_usable(content):
        return safe_summary
    return content.strip()


def translate_timeline_details(details):
    translated = []
    for d in details or []:
        local_text = _to_plain_english(d.get("text") or "No detail text")
        translated.append(
            {
                "time": d.get("time"),
                "text": d.get("text"),
                "ai_text": local_text,
            }
        )

    if not translated:
        return translated

    return translated
