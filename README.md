# Startup Idea Bank Chatbot

A chat-style web app for browsing a 640-idea, 32-sector startup idea bank —
built with a Python (Flask) backend and a plain HTML/CSS/JS frontend.

## Project structure

```
backend/
  app.py               Flask app: serves the frontend + a small JSON API
  data_loader.py        Loads and cleans the .xlsx workbook into idea records
  requirements.txt      Python dependencies

frontend/
  index.html             Page shell
  static/
    css/style.css        All styling
    js/app.js             Talks to the backend API, renders the chat UI

data/
  Startup_Idea_Bank_640_Unique.xlsx   Source workbook (32 sheets + Index)
```

## Setup (VS Code / terminal)

1. Open this folder in VS Code.
2. Create and activate a virtual environment:

   ```bash
   cd backend
   python -m venv venv

   # macOS / Linux
   source venv/bin/activate

   # Windows
   venv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the server:

   ```bash
   python app.py
   ```

5. Open **http://localhost:5000** in your browser.

VS Code will pick up `backend/venv` as the interpreter automatically if you
select it via *Python: Select Interpreter*; otherwise point it at
`backend/venv/bin/python` (or `venv\Scripts\python.exe` on Windows).

## How it works

- On startup, `backend/app.py` calls `data_loader.load_idea_bank()`, which
  reads every sheet in the workbook (except "Index"), normalizes the columns,
  and splits each idea into a name/description.
- The frontend never sees the spreadsheet directly — it talks to a small JSON
  API:
  - `GET /api/meta` — sector list with counts, difficulty levels, total count
  - `GET /api/search?q=&domain=&difficulty=&limit=&offset=` — keyword search.
    When `q` is given and something matches, the response also includes a
    `"best"` object: the single top-fit idea plus a `confidence` percentage,
    the `matched_terms`, and which field they landed in — this is what the
    chat leads with instead of a plain list.
  - `GET /api/random?domain=&difficulty=` — one random idea
  - `GET /api/idea/<id>` — a single idea by id
- `frontend/static/js/app.js` renders the sidebar filters and the chat thread.
  On a text query it shows a short typing indicator, then leads with a
  highlighted "best pick" card (confidence bar + matched keywords + a "top
  match" stamp), with any other close matches offered underneath as
  secondary options — rather than dumping a flat grid of results.

## Updating the data

Replace `data/Startup_Idea_Bank_640_Unique.xlsx` with a new workbook (same
sheet layout: one sheet per sector, plus an "Index" sheet to ignore) and
restart the server — no other changes needed.
# finsuite-py
