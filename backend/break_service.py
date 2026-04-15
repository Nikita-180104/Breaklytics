import json
import re
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_SHIFT_START = "11:00:00 AM"
DEFAULT_ALLOWED_BREAK_MINUTES = 60
TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}:\d{2}\s*[APap][Mm]\b")


def extract_times(text):
    return TIME_PATTERN.findall(text or "")


def parse_time(timestamp):
    cleaned_timestamp = re.sub(r"\s+", " ", (timestamp or "").strip()).upper()
    try:
        return datetime.strptime(cleaned_timestamp, "%I:%M:%S %p")
    except ValueError:
        return None


def format_duration(total_seconds):
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return {"minutes": minutes, "seconds": seconds}


def parse_valid_times(timestamps):
    valid_times = []
    for timestamp in timestamps:
        parsed_time = parse_time(timestamp)
        if parsed_time:
            valid_times.append(parsed_time)
    return valid_times


def calculate_total_break_seconds(times, shift_start_time):
    total_seconds = 0
    used_pairs = []
    used_timestamps = []

    # Keka attendance logs alternate as IN, OUT, IN, OUT...
    # Break duration is measured from each OUT timestamp to the next IN timestamp.
    for index in range(1, len(times) - 1, 2):
        start_time = times[index]
        end_time = times[index + 1]

        if (
            start_time.time() < shift_start_time.time()
            or end_time.time() < shift_start_time.time()
        ):
            continue

        duration = int((end_time - start_time).total_seconds())
        if duration > 0:
            total_seconds += duration
            used_timestamps.extend(
                [
                    start_time.strftime("%I:%M:%S %p"),
                    end_time.strftime("%I:%M:%S %p"),
                ]
            )
            used_pairs.append(
                {
                    "start": start_time.strftime("%I:%M:%S %p"),
                    "end": end_time.strftime("%I:%M:%S %p"),
                    "durationSeconds": duration,
                }
            )

    return total_seconds, used_pairs, used_timestamps


def calculate_break(
    raw_text,
    shift_start=DEFAULT_SHIFT_START,
    allowed_break_minutes=DEFAULT_ALLOWED_BREAK_MINUTES,
):
    shift_start_time = parse_time(shift_start)
    if shift_start_time is None:
        raise ValueError("Invalid shift start time. Use HH:MM:SS AM/PM format.")

    try:
        allowed_break_minutes = int(allowed_break_minutes)
    except (TypeError, ValueError) as exc:
        raise ValueError("Allowed break minutes must be a whole number.") from exc

    if allowed_break_minutes < 0:
        raise ValueError("Allowed break minutes cannot be negative.")

    extracted_times = extract_times(raw_text)
    valid_times = parse_valid_times(extracted_times)
    total_seconds, used_pairs, used_timestamps = calculate_total_break_seconds(
        valid_times, shift_start_time
    )
    remaining_seconds = max(0, (allowed_break_minutes * 60) - total_seconds)

    return {
        "breakTakenSeconds": total_seconds,
        "breakRemainingSeconds": remaining_seconds,
        "breakTaken": format_duration(total_seconds),
        "breakRemaining": format_duration(remaining_seconds),
        "allowedBreakMinutes": allowed_break_minutes,
        "shiftStart": shift_start_time.strftime("%I:%M:%S %p"),
        "matchedTimestamps": extracted_times,
        "usedTimestamps": used_timestamps,
        "ignoredOddTimestamp": len(valid_times) % 2 == 1,
        "pairs": used_pairs,
    }


def read_multiline_input():
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip().upper() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


class BreakRequestHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path == "/api/health":
            self._send_json(200, {"status": "ok"})
            return

        self._send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/calculate-break":
            self._send_json(404, {"error": "Not found"})
            return

        content_length = self.headers.get("Content-Length", "0")
        try:
            body_length = int(content_length)
        except ValueError:
            self._send_json(400, {"error": "Invalid Content-Length header"})
            return

        try:
            raw_body = self.rfile.read(body_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return

        raw_text = payload.get("rawText", "")
        shift_start = payload.get("shiftStart", DEFAULT_SHIFT_START)
        allowed_break_minutes = payload.get(
            "allowedBreakMinutes", DEFAULT_ALLOWED_BREAK_MINUTES
        )

        try:
            result = calculate_break(raw_text, shift_start, allowed_break_minutes)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
            return

        self._send_json(200, result)

    def log_message(self, format_string, *args):
        return


def run_server(host="127.0.0.1", port=8000):
    server = ThreadingHTTPServer((host, port), BreakRequestHandler)
    print(f"Break API server running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def run_cli():
    print("Paste attendance logs line by line. Type END to finish.")
    raw_text = read_multiline_input()
    result = calculate_break(raw_text)

    print(
        f"Break taken: {result['breakTaken']['minutes']} minutes "
        f"{result['breakTaken']['seconds']} seconds"
    )
    print(
        f"Break remaining: {result['breakRemaining']['minutes']} minutes "
        f"{result['breakRemaining']['seconds']} seconds "
        f"(out of {result['allowedBreakMinutes']} minutes)"
    )
