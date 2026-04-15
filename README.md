# Breaklytics

Breaklytics is a full-stack employee break calculator for Keka-style attendance logs.

It includes:
- a Python backend for parsing attendance timestamps and calculating break duration
- a React + Vite frontend for pasting logs and viewing results in the browser

## Features

- Accepts raw pasted attendance logs with extra text like `MISSING`
- Extracts timestamps in `HH:MM:SS AM/PM` format
- Supports Keka-style `IN, OUT, IN, OUT` attendance order
- Calculates break time from each `OUT` entry to the next `IN` entry
- Ignores entries before the configured shift start
- Ignores incomplete trailing entries safely
- Shows break taken and break remaining out of the allowed limit

## Project Structure

```text
Breaklytics/
├── backend/
│   ├── break.py
│   └── break_service.py
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
├── .gitignore
└── README.md
```

## Run The Project

Open two terminals.

### Backend

From the project root:

```powershell
python backend\break.py --serve
```

The backend runs on:

```text
http://127.0.0.1:8000
```

### Frontend

From the `frontend` folder:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The frontend usually runs on:

```text
http://127.0.0.1:5173
```

## CLI Mode

You can also run the backend directly as a terminal tool:

```powershell
python backend\break.py
```

Then paste attendance log lines and finish with:

```text
END
```

## Break Calculation Logic

Breaklytics assumes Keka logs follow this sequence:

```text
IN
OUT
IN
OUT
...
```

Breaks are calculated as:

- `OUT -> next IN`

Rules:

- timestamps before shift start are ignored for break calculation
- invalid text is ignored
- if the final entry is incomplete, it is skipped
- remaining break time never goes below zero

## API

The frontend sends requests to:

```text
POST /api/calculate-break
```

Example request body:

```json
{
  "rawText": "11:01:30 AM\n11:02:24 AM\n11:04:17 AM",
  "shiftStart": "11:00:00 AM",
  "allowedBreakMinutes": 60
}
```

## Notes

- Start the backend before using the frontend
- If PowerShell blocks `npm`, use `npm.cmd`
- Restart the backend after changing Python logic
