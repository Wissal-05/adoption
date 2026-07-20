#!/usr/bin/env python3

import csv
import gzip
import hashlib
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit
from zoneinfo import ZoneInfo

BASE = Path(__file__).resolve().parent
INPUT = BASE / "nginx-access-all.log"

EVENTS = BASE / "nginx-events.csv.gz"
DAILY = BASE / "daily-kpis.csv"
ROUTES = BASE / "top-routes.csv"
REJECTED = BASE / "unparsed-lines.log"

UTC = ZoneInfo("UTC")
LOCAL_TZ = ZoneInfo("Africa/Casablanca")

LOG_PATTERN = re.compile(
    r'^(?P<remote_addr>\S+) - (?P<remote_user>\S+) '
    r'\[(?P<time>[^\]]+)\] '
    r'"(?P<request>(?:\\.|[^"])*)" '
    r'(?P<status>\d{3}) '
    r'(?P<bytes>\d+|-) '
    r'"(?P<referer>(?:\\.|[^"])*)" '
    r'"(?P<user_agent>(?:\\.|[^"])*)" '
    r'"(?P<xff>(?:\\.|[^"])*)"$'
)

STATIC_EXTENSIONS = {
    ".css", ".js", ".map", ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".ico", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".mp4",
    ".mp3", ".pdf", ".zip", ".xml", ".txt"
}

BOT_PATTERN = re.compile(
    r'bot|crawler|spider|slurp|wget|curl|python-requests|'
    r'uptimerobot|zabbix|prometheus|healthcheck',
    re.IGNORECASE
)

daily_visitors = defaultdict(set)
daily_requests = Counter()
daily_human_requests = Counter()
daily_page_views = Counter()
daily_api_requests = Counter()
daily_errors_4xx = Counter()
daily_errors_5xx = Counter()
route_counter = Counter()

parsed = 0
rejected = 0

fields = [
    "event_time_utc",
    "event_time_local",
    "event_date_local",
    "remote_addr",
    "client_ip",
    "visitor_id_approx",
    "method",
    "path",
    "query_keys",
    "status",
    "bytes_sent",
    "referer",
    "user_agent",
    "event_type",
    "is_bot",
    "is_static",
    "is_api",
    "is_internal_backend",
    "analytics_eligible"
]

with (
    INPUT.open("r", encoding="utf-8", errors="replace") as source,
    gzip.open(EVENTS, "wt", encoding="utf-8", newline="") as events_file,
    REJECTED.open("w", encoding="utf-8") as rejected_file
):
    writer = csv.DictWriter(events_file, fieldnames=fields)
    writer.writeheader()

    for line_number, raw_line in enumerate(source, 1):
        line = raw_line.rstrip("\n")
        match = LOG_PATTERN.match(line)

        if not match:
            rejected += 1
            if rejected <= 10000:
                rejected_file.write(f"{line_number}\t{line}\n")
            continue

        data = match.groupdict()

        try:
            timestamp = datetime.strptime(
                data["time"], "%d/%b/%Y:%H:%M:%S %z"
            )
            utc_time = timestamp.astimezone(UTC)
            local_time = timestamp.astimezone(LOCAL_TZ)

            request_parts = data["request"].split(" ", 2)
            method = request_parts[0] if request_parts else ""
            target = request_parts[1] if len(request_parts) > 1 else ""

            parsed_url = urlsplit(target)
            path = parsed_url.path or "/"
            query_keys = ",".join(
                sorted({key for key, _ in parse_qsl(
                    parsed_url.query,
                    keep_blank_values=True
                )})
            )

            status = int(data["status"])
            bytes_sent = (
                int(data["bytes"]) if data["bytes"].isdigit() else 0
            )

            xff = data["xff"].strip()
            client_ip = (
                xff.split(",")[0].strip()
                if xff and xff != "-"
                else data["remote_addr"]
            )

            user_agent = data["user_agent"]
            visitor_id = hashlib.sha256(
                f"{client_ip}|{user_agent}".encode("utf-8")
            ).hexdigest()[:24]

            suffix = Path(path.lower()).suffix
            is_static = suffix in STATIC_EXTENSIONS
            is_api = (
                path.startswith("/api/")
                or path.startswith("/v1/api/")
                or path == "/api"
                or path == "/v1/api"
            )
            is_bot = bool(BOT_PATTERN.search(user_agent))
            is_internal = (
                user_agent.lower().startswith("axios/")
                or client_ip in {"127.0.0.1", "::1", "10.16.183.166"}
            )

            if is_bot:
                event_type = "bot_request"
            elif is_internal:
                event_type = "internal_backend_request"
            elif is_static:
                event_type = "static_asset"
            elif is_api:
                event_type = "api_request"
            else:
                event_type = "page_view"

            analytics_eligible = (
                not is_bot
                and not is_internal
                and not is_static
                and status < 500
            )

            date_key = local_time.date().isoformat()

            daily_requests[date_key] += 1

            if 400 <= status < 500:
                daily_errors_4xx[date_key] += 1

            if status >= 500:
                daily_errors_5xx[date_key] += 1

            if analytics_eligible:
                daily_visitors[date_key].add(visitor_id)
                daily_human_requests[date_key] += 1
                route_counter[path] += 1

                if event_type == "page_view":
                    daily_page_views[date_key] += 1
                elif event_type == "api_request":
                    daily_api_requests[date_key] += 1

            writer.writerow({
                "event_time_utc": utc_time.isoformat(),
                "event_time_local": local_time.isoformat(),
                "event_date_local": date_key,
                "remote_addr": data["remote_addr"],
                "client_ip": client_ip,
                "visitor_id_approx": visitor_id,
                "method": method,
                "path": path,
                "query_keys": query_keys,
                "status": status,
                "bytes_sent": bytes_sent,
                "referer": data["referer"],
                "user_agent": user_agent,
                "event_type": event_type,
                "is_bot": int(is_bot),
                "is_static": int(is_static),
                "is_api": int(is_api),
                "is_internal_backend": int(is_internal),
                "analytics_eligible": int(analytics_eligible)
            })

            parsed += 1

        except Exception:
            rejected += 1
            if rejected <= 10000:
                rejected_file.write(f"{line_number}\t{line}\n")

dates = sorted(daily_requests)

with DAILY.open("w", encoding="utf-8", newline="") as daily_file:
    fieldnames = [
        "date",
        "dau_approx",
        "wau_approx",
        "mau_approx",
        "total_requests",
        "human_requests",
        "page_views",
        "api_requests",
        "errors_4xx",
        "errors_5xx"
    ]

    writer = csv.DictWriter(daily_file, fieldnames=fieldnames)
    writer.writeheader()

    for date_text in dates:
        current_date = datetime.strptime(date_text, "%Y-%m-%d").date()

        wau_visitors = set()
        mau_visitors = set()

        for candidate_date, visitors in daily_visitors.items():
            parsed_date = datetime.strptime(
                candidate_date, "%Y-%m-%d"
            ).date()
            difference = (current_date - parsed_date).days

            if 0 <= difference < 7:
                wau_visitors.update(visitors)

            if 0 <= difference < 30:
                mau_visitors.update(visitors)

        writer.writerow({
            "date": date_text,
            "dau_approx": len(daily_visitors[date_text]),
            "wau_approx": len(wau_visitors),
            "mau_approx": len(mau_visitors),
            "total_requests": daily_requests[date_text],
            "human_requests": daily_human_requests[date_text],
            "page_views": daily_page_views[date_text],
            "api_requests": daily_api_requests[date_text],
            "errors_4xx": daily_errors_4xx[date_text],
            "errors_5xx": daily_errors_5xx[date_text]
        })

with ROUTES.open("w", encoding="utf-8", newline="") as routes_file:
    writer = csv.writer(routes_file)
    writer.writerow(["path", "requests"])

    for path, count in route_counter.most_common():
        writer.writerow([path, count])

print(f"Parsed lines  : {parsed}")
print(f"Rejected lines: {rejected}")
print(f"Events file   : {EVENTS}")
print(f"Daily KPIs    : {DAILY}")
print(f"Top routes    : {ROUTES}")
