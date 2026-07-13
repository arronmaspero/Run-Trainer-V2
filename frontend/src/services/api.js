const API_BASE = window.location.port === "5173" || window.location.port === "3000"
  ? "http://localhost:8000/api/v1"
  : `${window.location.origin}/api/v1`;

function getHeaders() {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("session_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function handleResponse(res, errorMessage) {
  if ((res.status === 401 || res.status === 410) && !res.url.includes("/auth/login")) {
    localStorage.removeItem("session_token");
    localStorage.removeItem("user_name");
    window.location.hash = "#login";
    throw new Error("Session expired. Please log in again.");
  }
  if (!res.ok) {
    let detail = errorMessage;
    try {
      const err = await res.json();
      detail = err.detail || errorMessage;
    } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // Auth API
  async register(name, email, password) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ name, email, password })
    });
    return handleResponse(res, "Registration failed");
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ email, password })
    });
    const data = await handleResponse(res, "Login failed");
    localStorage.setItem("session_token", data.session_token);
    localStorage.setItem("user_name", data.user.name);
    return data;
  },

  logout() {
    localStorage.removeItem("session_token");
    localStorage.removeItem("user_name");
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Unauthorized");
  },

  async getProfile() {
    const res = await fetch(`${API_BASE}/auth/profile`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to fetch profile");
  },

  async updateProfile(profileData) {
    const res = await fetch(`${API_BASE}/auth/profile`, {
      method: "PUT",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify(profileData)
    });
    const data = await handleResponse(res, "Failed to update profile");
    localStorage.setItem("user_name", data.user.name);
    return data;
  },

  // Strava API
  async getStravaConnectUrl() {
    const res = await fetch(`${API_BASE}/strava/connect-url`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to get connect URL");
  },

  async testStravaConnection() {
    const res = await fetch(`${API_BASE}/strava/test`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to test Strava connection");
  },

  async getStravaActivities() {
    const res = await fetch(`${API_BASE}/strava/activities`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to load Strava activities");
  },

  async getStravaActivity(activityId) {
    const res = await fetch(`${API_BASE}/strava/activities/${activityId}`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to load activity detail");
  },

  // Plan API
  async generatePlan(planConfig) {
    const res = await fetch(`${API_BASE}/plans/generate`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify(planConfig)
    });
    return handleResponse(res, "Plan generation failed");
  },

  async getActivePlan() {
    const res = await fetch(`${API_BASE}/plans/active`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to get active plan");
  },

  async evaluatePlan() {
    const res = await fetch(`${API_BASE}/plans/evaluate`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to evaluate training plan progress");
  },

  async moveSession(sessionId, newDate) {
    const res = await fetch(`${API_BASE}/plans/sessions/move`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ session_id: sessionId, new_date: newDate })
    });
    return handleResponse(res, "Failed to move session");
  },

  async rebalancePlan(planId, confirm = false, weekNumber = null) {
    const res = await fetch(`${API_BASE}/plans/rebalance`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ plan_id: planId, confirm, week_number: weekNumber })
    });
    return handleResponse(res, "Failed to rebalance training plan");
  },

  async previewPlanUpdate(difficultyFeedback, userComments) {
    const res = await fetch(`${API_BASE}/plans/update/preview`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ difficulty_feedback: difficultyFeedback, user_comments: userComments })
    });
    return handleResponse(res, "Failed to preview plan updates");
  },

  async applyPlanUpdate(difficultyFeedback, userComments) {
    const res = await fetch(`${API_BASE}/plans/update/apply`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ difficulty_feedback: difficultyFeedback, user_comments: userComments })
    });
    return handleResponse(res, "Failed to apply plan updates");
  },

  async getSessionDetail(sessionId) {
    const res = await fetch(`${API_BASE}/plans/sessions/${sessionId}`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to load session details");
  },

  // Settings API
  async revokeStrava() {
    const res = await fetch(`${API_BASE}/settings/strava`, {
      method: "DELETE",
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to revoke Strava");
  },

  async exportUserData() {
    const res = await fetch(`${API_BASE}/settings/export`, {
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to export user data");
  },

  async deleteAccount() {
    const res = await fetch(`${API_BASE}/settings/account`, {
      method: "DELETE",
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to delete account");
  },

  async connectGarmin(email, password) {
    const res = await fetch(`${API_BASE}/settings/garmin`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders(),
      body: JSON.stringify({ email, password })
    });
    return handleResponse(res, "Failed to connect Garmin Connect");
  },

  async disconnectGarmin() {
    const res = await fetch(`${API_BASE}/settings/garmin`, {
      method: "DELETE",
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to disconnect Garmin Connect");
  },

  async pushPlanToGarmin(forceClear = false) {
    const res = await fetch(`${API_BASE}/plans/push-garmin?force_clear=${forceClear}`, {
      method: "POST",
      cache: "no-store",
      headers: getHeaders()
    });
    return handleResponse(res, "Failed to push structured workouts to Garmin");
  }
};
