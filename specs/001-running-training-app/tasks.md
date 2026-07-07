# Tasks: AI-Powered Running Training Web App

**Input**: Design documents from [specs/001-running-training-app/](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/)

**Prerequisites**: [plan.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/plan.md) (required), [spec.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/spec.md) (required), [data-model.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/data-model.md) (required), [contracts/api-contracts.md](file:///d:/Spec%20Kit%20install/specs/001-running-training-app/contracts/api-contracts.md) (required)

**Tests**: Pytest testing is required for all backend API endpoints per the project constitution.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project directory structure and basic setup.

- [x] T001 Create backend directory layout and configure backend/requirements.txt
- [x] T002 Create frontend directory layout and configure frontend/package.json
- [x] T003 [P] Configure backend/.env and frontend/.env configuration templates

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core database models and routing frameworks that must be completed before user stories.

**⚠️ CRITICAL**: No user story implementation can begin until this phase is complete.

- [x] T004 Initialize SQLite database schema and SQLAlchemy engine in backend/src/models/__init__.py
- [x] T005 Create User and AthleteProfile database models in backend/src/models/user.py
- [x] T006 Create ConnectedAccount and Activity database models in backend/src/models/activity.py
- [x] T007 Create TrainingPlan and TrainingSession database models in backend/src/models/plan.py
- [x] T008 Create PlanChangeLog database model in backend/src/models/changelog.py
- [x] T009 Configure base FastAPI application and CORS middleware in backend/src/main.py
- [x] T010 Create core index.css with HSL color variables and dark/light modes in frontend/src/index.css

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel.

---

## Phase 3: User Story 1 - Onboarding and Plan Generation (Priority: P1) 🎯 MVP

**Goal**: Allow users to register, connect Strava, input their training constraints, and generate a customized training plan via Gemini.

**Independent Test**: Complete the onboarding flow, login, authenticate Strava, and view the generated training plan on the dashboard.

### Tests for User Story 1

- [x] T013 [P] [US1] Add pytest tests for registration and login in backend/tests/test_auth.py
- [x] T018 [P] [US1] Add pytest tests for plan generation in backend/tests/test_planner.py

### Implementation for User Story 1

- [x] T011 [P] [US1] Create Auth models and helper services in backend/src/services/auth_service.py
- [x] T012 [US1] Implement registration and login API routes in backend/src/api/auth.py
- [x] T014 [P] [US1] Implement Strava OAuth client and token refresh logic in backend/src/services/strava_service.py
- [x] T015 [US1] Implement Strava auth callback API route in backend/src/api/strava.py
- [x] T016 [P] [US1] Implement Google Gemini training plan generator with search grounding in backend/src/services/planner_service.py
- [x] T017 [US1] Implement training plan generation API route in backend/src/api/plans.py
- [x] T019 [US1] Create frontend API clients for auth, Strava, and plan generation in frontend/src/services/api.js
- [x] T020 [P] [US1] Create registration and login pages in frontend/src/pages/AuthPage.jsx
- [x] T021 [US1] Create onboarding profile wizard pages in frontend/src/pages/OnboardingPage.jsx
- [x] T022 [US1] Create main dashboard summary widgets and countdown timer in frontend/src/pages/DashboardPage.jsx

**Checkpoint**: At this point, User Story 1 (onboarding + generation) is fully functional and testable.

---

## Phase 4: User Story 2 - Interactive Training Calendar & Drag-and-Drop (Priority: P2)

**Goal**: Allow users to drag-and-drop sessions, triggering warning recommendations if imbalances occur.

**Independent Test**: Drag an interval session on the calendar next to another hard session and verify the warning recommendation appears.

### Tests for User Story 2

- [x] T024 [P] [US2] Add pytest tests for moving calendar sessions in backend/tests/test_calendar.py

### Implementation for User Story 2

- [x] T023 [US2] Implement calendar session move API route with rebalance validation checks in backend/src/api/calendar.py
- [x] T025 [P] [US2] Create reusable weekly/monthly calendar tiles and grid layouts in frontend/src/components/Calendar.jsx
- [x] T026 [US2] Implement HTML5 drag-and-drop actions on calendar in frontend/src/components/CalendarDragDrop.jsx
- [x] T027 [US2] Create dynamic AI rebalance recommendation dialog in frontend/src/components/RebalanceDialog.jsx
- [x] T028 [US2] Integrate the calendar grid on the main DashboardPage in frontend/src/pages/DashboardPage.jsx

**Checkpoint**: User Stories 1 and 2 are functional together.

---

## Phase 5: User Story 3 - Workout Details & Garmin Watch Setup (Priority: P3)

**Goal**: View detailed session breakdown and step-by-step watch setup guides.

**Independent Test**: Open a workout details page, verify target pace/heart-rate zones, and read manual watch instructions.

### Implementation for User Story 3

- [x] T029 [US3] Implement session details retrieval API endpoint in backend/src/api/sessions.py
- [x] T030 [P] [US3] Create Garmin Connect manual workout text formatter service in backend/src/services/garmin_formatter.py
- [x] T031 [P] [US3] Create session detail display page showing warm-up, sets, target paces in frontend/src/pages/SessionDetailPage.jsx
- [x] T032 [US3] Add Garmin manual instruction steps and safety alternative workout views in frontend/src/pages/SessionDetailPage.jsx

**Checkpoint**: All user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Cleanup, data privacy settings, responsive adjustments, and final verification.

- [x] T033 Implement revoking Strava credentials, data export, and account deletion in backend/src/api/settings.py
- [x] T034 Add responsive visual tweaks for mobile screens in frontend/src/index.css
- [x] T035 Run end-to-end quickstart verification scenarios in specs/001-running-training-app/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (Phase 1) completion. Blocks all user stories.
- **User Stories (Phases 3+)**: All depend on Foundational (Phase 2) completion. Must be executed in priority order (P1 -> P2 -> P3) for step-by-step MVP delivery.
- **Polish (Phase 6)**: Depends on all user story phases being complete.

### Within Each User Story

- Backend models and endpoints must be implemented and tested before frontend views.
- Story must be fully complete and verified before moving to the next priority level.

---

## Parallel Execution Examples

### Setup and Foundational (Phase 1 & 2)
```bash
# Setup config templates (T003) can run in parallel with general setup (T001, T002)
# Database models (T005, T006, T007, T008) can be created in parallel after models directory init (T004)
```

### User Story 1 (Phase 3)
```bash
# Auth models (T011) and Strava client (T014) can be coded in parallel.
# Pytest tests (T013, T018) can be written and executed in parallel.
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Confirm user onboarding and plan generation works end-to-end using mock Strava OAuth parameters.
5. Proceed to calendar and session details.
