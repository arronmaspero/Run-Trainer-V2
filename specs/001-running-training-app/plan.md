# Implementation Plan: AI-Powered Running Training Web App

**Branch**: `001-running-training-app` | **Date**: 2026-06-29 | **Spec**: [spec.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/spec.md)

**Input**: Feature specification from [spec.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/spec.md)

**Note**: This plan defines the technical architecture, project layout, and quality gates for implementing the Running Training Web App.

## Summary

The goal of this feature is to build a modern, high-fidelity running training web application. The frontend uses Vite + React with custom Vanilla CSS for premium sporty aesthetics. The backend uses Python + FastAPI with SQLAlchemy and SQLite for clean, lightweight, local-first storage. Plan generation is handled by Google Gemini with search grounding for race course intelligence, and Strava activity synchronization is managed via background async tasks.

## Technical Context

**Language/Version**: Python 3.12+ (Backend), Node.js 20+ (Frontend)

**Primary Dependencies**: FastAPI, uvicorn, SQLAlchemy, Pydantic, google-genai, httpx (Backend); React, Vite, Lucide React (Frontend)

**Storage**: SQLite database (local file: `running_coach.db`), structured with SQLAlchemy ORM

**Testing**: pytest (Backend), Vitest (Frontend)

**Target Platform**: Local execution (Windows, macOS, Linux), future cloud deployment ready

**Project Type**: Web Application (Single-Page App + REST API)

**Performance Goals**: Dashboard and calendar load under 2 seconds, session drags execute database updates in under 1 second.

**Constraints**: Strava API rate limits (200 requests/15 mins, 2000/day); Gemini API key required in local environment.

**Scale/Scope**: Local-first single user deployment, support for 5K, 10K, Half Marathon, Marathon, and Ultra plans.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

-   **I. Minimum Lovable Product (MLP)**: Verified. Visual layout uses custom dark-mode sporty gradients and card layouts, with fluid drag-and-drop animations and dynamic warnings.
-   **II. Spec-Driven Development (SDD)**: Verified. Feature spec `spec.md` is complete, and this plan forms the blueprint before implementation.
-   **III. Clean & Modular Python Backend**: Verified. FastAPI backend is structured cleanly with services, models, and api endpoints. Centralized exception middleware captures all database/OAuth failures.
-   **IV. High-Fidelity Frontend**: Verified. The frontend uses a Vite configuration with no external CSS framework, styled purely with custom Vanilla CSS for visual excellence.
-   **V. Local-First with Production Readiness**: Verified. Runs locally with uvicorn and npm dev servers, and OAuth credentials are saved in environment variables (`.env`) for future production swap.

## Project Structure

### Documentation (this feature)

```text
specs/001-running-training-app/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/
│   └── api-contracts.md # Phase 1 output (/speckit-plan command)
└── checklists/
    └── requirements.md  # Specification Quality Checklist
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api/             # Routes (auth, strava, plan, calendar)
│   ├── models/          # SQLAlchemy Database entities
│   ├── services/        # Gemini planner service, Strava OAuth sync service
│   ├── main.py          # FastAPI application entrypoint
│   └── config.py        # Configuration & Secrets management
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_planner.py
└── requirements.txt

frontend/
├── src/
│   ├── components/      # Calendar, Dashboard widget cards, AI panel
│   ├── pages/           # Landing, Onboarding, Dashboard, SessionDetail
│   ├── services/        # Backend API clients
│   ├── index.css        # Core Vanilla CSS styling and HSL color variables
│   └── main.jsx
├── tests/
│   └── calendar.test.jsx
├── package.json
└── vite.config.js
```

**Structure Decision**: Web application layout (Option 2) separates Python backend and Vite frontend to ensure independent build/run steps.
