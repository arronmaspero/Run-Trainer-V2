# Feature Specification: AI-Powered Running Training Web App

**Feature Branch**: `001-running-training-app`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description of the AI-Powered Running Training Web App including product vision, target users, core journey, Strava integration, calendar drag-and-drop mechanics, Gemini-powered adaptive planning, Garmin setup guides, and visual aesthetics.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Onboarding and Plan Generation (Priority: P1)

**Why this priority**: This is the core flow required to get the user set up and running on the platform. Without onboarding and the initial plan generation, the app has no value.

**Independent Test**: A user registers a new account, completes the profile wizard, authorizes Strava, and lands on a personalized training plan dashboard.

**Acceptance Scenarios**:

1. **Given** a new user visits the web app, **When** they register with email and password and verify their email, **Then** they are guided to the onboarding profile wizard.
2. **Given** the user is in the onboarding wizard, **When** they input their current volume (e.g., 20 miles/week), running goals, and click "Connect Strava" to complete OAuth authentication, **Then** the app imports their historical activity summary and Google Gemini generates a custom, safe training plan.
3. **Given** the training plan is successfully generated, **When** the generation finishes, **Then** the user is redirected to their dashboard containing their weekly calendar and countdown to their race.

---

### User Story 2 - Interactive Training Calendar & Drag-and-Drop (Priority: P2)

**Why this priority**: The training calendar is the primary interface for ongoing engagement. Runners need flexibility to adapt their training to real-life schedule changes.

**Independent Test**: The user views their weekly calendar and drags a workout to a different day, receiving validation warnings if safety checks are violated.

**Acceptance Scenarios**:

1. **Given** a user is viewing their training calendar, **When** they drag an interval session from Tuesday to Wednesday, **Then** the calendar updates the session date and saves the change.
2. **Given** the user drags a hard session to a day immediately adjacent to another hard session, **When** the move is completed, **Then** the calendar displays a safety warning recommending an adjustment and shows an "AI Rebalance" button, but allows the user to override it.
3. **Given** the user updates their schedule via drag-and-drop, **When** they confirm the change, **Then** the change is logged in the Plan Change Log.

---

### User Story 3 - Workout Details & Coach's Training Benefits (Priority: P3)

**Why this priority**: A training plan is only useful if the runner knows how to execute each individual session and understands the physiological adaptations and benefits behind them.

**Independent Test**: The user clicks on a calendar session and views clear instructions, target paces, and a dynamic breakdown of the physiological benefits of the workout.

**Acceptance Scenarios**:

1. **Given** a user is on their dashboard or calendar, **When** they click on a "Threshold Intervals" session, **Then** they see detailed warm-up, main set, cool-down, target RPE, and target paces (e.g., 7:25–7:40 /mi).
2. **Given** the user is viewing the session detail page, **When** they check the Training Benefits section, **Then** they see the workout's primary purpose and specific physiological adaptations (e.g. "Lactate Threshold & Speed Endurance", "Teaches the body to clear lactic acid faster").
3. **Given** the user is tired or in pain while viewing a session, **When** they review the safety alternatives, **Then** they see an easier alternative workout and a clear medical disclaimer.

---

### Edge Cases

- **Strava API Rate Limit Exceeded**: When the daily or 15-minute Strava API limits are reached, the app queues the sync in the background and displays a friendly notice: "Activity sync is currently queued due to high volume. Your runs will appear shortly."
- **Injury/Pain Reporting**: When a user logs pain above a threshold (e.g., RPE/pain flag in post-session reflection), the app triggers a plan adaptation recommendation, suggesting an easy run or rest day.
- **Race Search Grounding Failure**: If the Gemini model cannot find the user's specific race details using search grounding, the app falls back to a generic plan for the selected race distance and prompts the user to verify course terrain manually.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support user registration and authentication via email/password and secure session management.
- **FR-002**: The onboarding wizard MUST collect running metrics (weekly mileage, recent race times, terrain access, preferred training days) and health/physiological metrics (HR, sleep, injuries) with a clear medical disclaimer. It MUST support selecting standard distances (5k, 10k, Half, Marathon) or entering a manual custom distance and unit (miles or kilometers).
- **FR-003**: The app MUST integrate with Strava OAuth 2.0 to request athlete authorization and securely store access and refresh tokens server-side.
- **FR-004**: The system MUST sync Strava activity data (distance, moving time, splits, laps, heart rate, cadence, grade) in the background.
- **FR-005**: The system MUST use Google Gemini (specifically the `gemini-3.5-flash` model) with search grounding to lookup race course details (date, distance, elevation, terrain, weather) based on the race name provided by the user.
- **FR-006**: The system MUST generate a personalized training plan using Google Gemini API (`gemini-3.5-flash` model), combining deterministic training guidelines (e.g., weekly volume progression limits) with imported Strava metrics and user constraints.
- **FR-007**: The dashboard MUST display current weekly mileage, training compliance rate, race countdown, an AI insight panel, and a weekly/monthly calendar view. The header MUST include a unit toggle (mi/km) to switch the display of all dashboard, onboarding, and calendar distance units between miles and kilometers.
- **FR-008**: The calendar view MUST support interactive drag-and-drop moves of workouts, with warning prompts if consecutive hard sessions or overreaching patterns are detected. Moving a session updates the date immediately; if this move creates a plan imbalance, an AI recommendation is presented which the user must manually accept to rebalance the remaining sessions.
- **FR-009**: The session detail page MUST display workout structures (warm-up, sets, cool-down), target paces, target heart rate zones, RPE values, safety alternatives, and the dynamic Coach's Training Benefits. Workout export to physical files (.FIT, .TCX, .ZWO) is out of scope for the MVP.
- **FR-010**: The user settings MUST support updating the athlete profile (name, physiological parameters, birth date, gender) by clicking their name in the header, and configuring custom developer Strava API credentials (`client_id` and `client_secret`) to be used for OAuth connection. It MUST also support revoking the Strava authorization, exporting all personal data in JSON format, and permanently deleting the user account.

### Key Entities

- **User**: Authentication credentials, consent history, and settings.
- **Athlete Profile**: Age, sex, resting/max HR, VO₂ max, injury history, running experience, and training availability constraints.
- **Connected Account**: Strava OAuth credentials (access/refresh tokens, expiry timestamps, scopes).
- **Activity**: Imported Strava run details (coordinates, splits, metrics, elevation) linked to a user.
- **Training Plan**: Generated schedule containing date range, target race, target time, and style parameter.
- **Training Session**: Detailed workout (type, target pace, warm-up, sets, cool-down, status, RPE, Garmin text guides).
- **Plan Change Log**: Audit trail of manual or AI-suggested session modifications.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: New users can complete the onboarding wizard and see their generated training plan in under 3 minutes (excluding Strava external authentication time).
- **SC-002**: Visual dashboard widgets and calendar views must load and render in under 2 seconds on standard local executions.
- **SC-003**: Dragging a session on the calendar must execute the safety check and save the updated date to the database in under 1 second.
- **SC-004**: The training plan compliance calculator must accurately match completed Strava activities to planned sessions within 5 seconds of sync completion.
- **SC-005**: All screens must achieve a 100% responsive layout across desktop and mobile screens.

## Assumptions

- Users have a pre-existing Strava account with some historical running data to inform the planning engine.
- An internet connection is available to perform Google Gemini API requests, Strava OAuth redirects, and race search grounding.
- The web app is run locally (e.g., standard Python backend and Vite frontend development servers), utilizing local environment files (`.env`) for API keys and database credentials.
- Calendar drag-and-drop rebalancing relies on user confirmation of AI suggestions rather than immediate automatic recalculation.
- Garmin watch workout synchronization is limited to manual setup instructions in the Garmin Connect app for the MVP.
