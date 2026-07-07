# Technical Research: AI-Powered Running Training Web App

This document outlines the technical design decisions, rationales, and alternatives considered for building the running training app locally with future production readiness.

## 1. AI Planning Engine & Orchestration

*   **Decision**: Google Gemini 1.5 Flash using the official `google-genai` Python SDK, utilizing Gemini Function Calling for structured operations and Google Search Grounding for race details lookup.
*   **Rationale**: Gemini 1.5 Flash offers low latency (supporting the 10-second plan generation requirement) and excellent function calling capability. Search Grounding provides real-time web search capability for race information with citations.
*   **Alternatives considered**:
    *   *OpenAI GPT-4o-mini*: Rejected due to project alignment with Google ecosystem and Gemini-native grounding features.
    *   *Manual Web Scraping for Races*: Rejected because search grounding dynamically captures race details without maintaining custom scrapers.

## 2. Strava OAuth & Background Synchronization

*   **Decision**: Standard OAuth 2.0 authorization code flow. Token storage in a local SQLite database (encrypted at rest if needed via SQLCipher, but using standard SQLite for local development). Background activity synchronization implemented using a lightweight asynchronous queue in Python (`asyncio.Queue` or `APScheduler`) to avoid Celery/Redis overhead for local execution.
*   **Rationale**: Keeps the local installation simple (no Redis prerequisite) while fully respecting Strava API rate limits (200 requests/15 mins) by caching activity data.
*   **Alternatives considered**:
    *   *Celery + Redis*: Rejected as a required dependency for local runs, though the background queue design is modular to allow seamless migration to Celery if deployed to production.
    *   *Polling on Frontend*: Rejected because it leads to repeated API hits and easily exceeds rate limits.

## 3. Database & Storage Architecture

*   **Decision**: SQLite database using SQLAlchemy ORM.
*   **Rationale**: SQLite is serverless, zero-configuration, and files are stored directly in the workspace, making it ideal for local-first apps. Using SQLAlchemy ensures database-agnostic code, allowing a trivial switch to PostgreSQL for future production deployments.
*   **Alternatives considered**:
    *   *PostgreSQL (Local Docker)*: Rejected as a hard requirement to simplify local setup, but target compatibility remains.

## 4. Frontend Calendar & Drag-and-Drop

*   **Decision**: React (Vite-powered) styled with Vanilla CSS. Calendar view rendered custom or using a lightweight library, with drag-and-drop built using native HTML5 Drag and Drop API or `@hello-pangea/dnd`.
*   **Rationale**: Enforces the project constitution requirement of Vanilla CSS for premium visual styling and precise control over gradients/transitions. Native HTML5 drag-and-drop or lightweight wrapper keeps the bundle fast.
*   **Alternatives considered**:
    *   *Full FullCalendar.js*: Rejected due to complex CSS overrides which conflict with the need for a highly customized, premium dark-mode visual aesthetic.
