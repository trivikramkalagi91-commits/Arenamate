# ArenaMate 🏟️

**An intelligent, highly-accessible, and multilingual wayfinding assistant designed for fans at Los Angeles Stadium (SoFi Stadium) for the FIFA World Cup 2026.**

ArenaMate is a specialized assistant that resolves wayfinding directions, safety guidelines, and amenity proximity for stadium attendees. The application is built on a "deterministic rules first, LLM phrasing last" architecture. This ensures that routing steps, accessibility modes, and occupancy states are computed using verified venue data and cannot be altered by prompt injection or model hallucination.

---

## Key Highlights & Features

- **Primary Venue**: Modelled for **SoFi Stadium** (FIFA Name: *Los Angeles Stadium*), capacity 70,240, located in Inglewood, CA, USA.
- **Multilingual Support**: Fully localized in English, Español, and Français (the three WC26 host-nation languages). Localizations cover the UI controls, dynamic route instructions, and place names.
- **Rules-First Guarding**: The AI model is strictly limited to phrasing and re-translating facts determined by the offline routing engine (`context_engine.py`). Proximity and steps are calculated before any LLM calls are made. If a fan submits no free-text question, the request is short-circuited to return instant static templates—incurring zero LLM costs.
- **Accessibility Modes**:
  - **Wheelchair / Step-Free**: Avoids stairs and restricts routes to accessible pathways (ramps, elevators).
  - **Screen-Reader Mode (Visual Need)**: Activates high-visibility themes and Landmark-based audio descriptions.
  - **Captioned Mode (Hearing Need)**: Emphasizes visual signage indicators and points out the quiet Sensory Room.
- **Time-Dependent Occupancy Simulation**: Escalates crowd levels at gates/concourses dynamically depending on minutes left before kickoff. Swaps crowded target amenities to quieter equivalents when possible.
- **Enterprise-Grade Security**: Strict Pydantic validations, IP rate limiting using an in-memory token bucket, input sanitization, and robust HTTP security headers (CSP, Frame-Options, Content-Type-Options).

---

## Technical Stack & Structure

- **Framework**: FastAPI (Asynchronous ASGI server)
- **Data Serialization**: Pydantic v2
- **Routing Engine**: Dijkstra Shortest-Path algorithm
- **AI Core**: Google Gemini API (optional, degrades gracefully to static offline phraser if API key is unset)
- **Formatting/Static Analysis**: Ruff, MyPy, Pytest

```
arenamate/
├── app/
│   ├── main.py            # FastAPI setup, CORS, rate limits, endpoints
│   ├── config.py          # Configuration loader
│   ├── logging_conf.py    # Log configurations
│   ├── models/
│   │   ├── schemas.py     # Pydantic validation schemas & Enums
│   ├── services/
│   │   ├── arena_data.py  # In-memory graph loading from JSON fixtures
│   │   ├── routing.py     # Dijkstra search implementation
│   │   ├── crowd.py       # Simulated occupancy surges
│   │   ├── phrasing.py    # Localized text compilation
│   │   ├── llm.py         # Offline phraser & Generative AI phrasing client
│   │   ├── security.py    # Input sanitization and IP rate limit tracking
│   │   └── context_engine.py  # Core decision routing pipeline
│   ├── data/              # JSON fixtures: arena.json, amenities.json, crowd.json
│   └── static/            # Static assets: index.html, style.css, app.js
├── tests/                 # 100% covered offline unit test suite
├── Dockerfile             # Container specification
├── pyproject.toml         # Ruff and MyPy setup
├── pytest.ini             # Pytest directives
└── requirements.txt       # Project dependencies
```

---

## Setup & Running

### Requirements
- Python 3.11+

### Local Setup

1. **Clone and navigate to the project directory**:
   ```bash
   cd C:\Users\trivi\.gemini\antigravity\scratch\arenamate
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration (Optional)**:
   Copy `.env.example` to `.env` and configure your `GEMINI_API_KEY` to enable live LLM phrasing. If no key is set, the app will degrade gracefully to the offline deterministic phraser.

5. **Start the development server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

---

## Running Quality Checks & Tests

ArenaMate is packaged with an offline test suite featuring unit and integration tests covering 100% statement coverage.

### Run tests:
```bash
pytest
```

### Run Linter (Ruff):
```bash
ruff check app tests
```

### Run Type Checker (MyPy):
```bash
mypy
```

---

## Container Deployment

To build and run the Docker container locally:
```bash
docker build -t arenamate .
docker run -p 8080:8080 arenamate
```
