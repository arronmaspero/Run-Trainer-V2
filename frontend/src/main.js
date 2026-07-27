import { api } from "./services/api.js?v=2";
import { AuthPage } from "./pages/AuthPage.js?v=2";
import { OnboardingPage } from "./pages/OnboardingPage.js?v=2";
import { CurrentPlanPage } from "./pages/CurrentPlanPage.js?v=2";
import { ProfilePage } from "./pages/ProfilePage.js?v=2";
import { SessionDetailPage } from "./pages/SessionDetailPage.js?v=2";
import { StravaDrawer } from "./components/StravaDrawer.js";
import { UpdatePlanDialog } from "./components/UpdatePlanDialog.js";

window.CurrentPlanPage = window.DashboardPage = CurrentPlanPage;
window.UpdatePlanDialog = UpdatePlanDialog;

// Unit Preference Helpers
window.formatLocalDate = (dateObj) => {
  const yyyy = dateObj.getFullYear();
  const mm = String(dateObj.getMonth() + 1).padStart(2, '0');
  const dd = String(dateObj.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
};

window.getUnitPreference = () => {
  return localStorage.getItem("unit_preference") || "miles";
};

window.toggleUnitPreference = () => {
  const current = window.getUnitPreference();
  const next = current === "miles" ? "km" : "miles";
  localStorage.setItem("unit_preference", next);
  
  // Update toggle button text
  const btn = document.getElementById("btn-unit-toggle");
  if (btn) btn.textContent = next === "miles" ? "Unit: mi" : "Unit: km";
  
  // Re-run router to update any visible numbers
  router();
};

window.formatDistance = (miles) => {
  if (miles === undefined || miles === null) return "";
  const pref = window.getUnitPreference();
  if (pref === "km") {
    const km = miles * 1.60934;
    return `${km.toFixed(1)} km`;
  }
  return `${miles.toFixed(1)} mi`;
};

window.convertTextUnits = (text) => {
  if (typeof text !== "string") return text;
  const pref = window.getUnitPreference();
  if (pref !== "km") return text;
  
  // 1. Convert distances (miles -> km)
  const distRegex = /(\d+(?:\.\d+)?)\s*-?\s*(?:miles|mile|mi)\b/gi;
  let result = text.replace(distRegex, (match, p1) => {
    const miles = parseFloat(p1);
    const km = miles * 1.60934;
    return `${km.toFixed(1)} km`;
  });
  
  // 2. Convert paces (min/mile -> min/km)
  const convertPaceStr = (paceStr) => {
    const timeParts = paceStr.split(":");
    if (timeParts.length !== 2) return paceStr;
    const min = parseInt(timeParts[0]);
    const sec = parseInt(timeParts[1]);
    const totalSec = min * 60 + sec;
    const totalSecKm = totalSec / 1.60934;
    const minKm = Math.floor(totalSecKm / 60);
    const secKm = Math.round(totalSecKm % 60);
    return `${minKm}:${secKm < 10 ? '0' : ''}${secKm}`;
  };

  const paceRegex = /\b(\d{1,2}:\d{2})(?:\s*-\s*(\d{1,2}:\d{2}))?\s*(min\/mile|min\/mi|\/mile|\/mi|pace)\b/gi;
  result = result.replace(paceRegex, (match, p1, p2, p3) => {
    const pace1Km = convertPaceStr(p1);
    const suffix = p3.toLowerCase();
    
    let newSuffix = "/km";
    if (suffix === "pace") {
      newSuffix = "pace";
    } else if (suffix.includes("min/")) {
      newSuffix = "min/km";
    }
    
    if (p2) {
      const pace2Km = convertPaceStr(p2);
      return `${pace1Km}-${pace2Km} ${newSuffix}`;
    }
    return `${pace1Km} ${newSuffix}`;
  });

  return result;
};

window.formatPaceRange = (paceRangeStr) => {
  if (!paceRangeStr || paceRangeStr === "N/A") return "N/A";
  try {
    const parts = paceRangeStr.split("-");
    const formattedParts = parts.map(part => {
      const timeParts = part.trim().split(":");
      if (timeParts.length !== 2) return part;
      const min = parseInt(timeParts[0]);
      const sec = parseInt(timeParts[1]);
      const totalSec = min * 60 + sec;
      const totalSecKm = totalSec / 1.60934;
      const minKm = Math.floor(totalSecKm / 60);
      const secKm = Math.round(totalSecKm % 60);
      return `${minKm}:${secKm < 10 ? '0' : ''}${secKm}`;
    });
    return formattedParts.join("-") + " /km";
  } catch (e) {
    return paceRangeStr;
  }
};

// Global Toast System
window.showToast = (message, type = "success") => {
  const container = document.getElementById("toast-container");
  if (!container) return;
  
  const toast = document.createElement("div");
  toast.className = "fade-in";
  toast.style.cssText = `
    padding: 0.9rem 1.5rem;
    border-radius: var(--radius-sm);
    color: white;
    font-weight: 500;
    font-size: 0.95rem;
    box-shadow: var(--shadow-lg);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: ${type === "error" ? "hsl(346, 84%, 61%)" : "hsl(142, 70%, 45%)"};
    border-left: 4px solid ${type === "error" ? "hsl(346, 84%, 40%)" : "hsl(142, 70%, 30%)"};
    animation: slideIn 0.3s ease forwards;
  `;
  toast.innerHTML = message;
  
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "fadeOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

// Route Controller
function navigateTo(hash) {
  window.location.hash = hash;
  window.scrollTo({ top: 0, behavior: "instant" });
}

// Router Logic
async function router() {
  const hash = window.location.hash || "#login";
  const container = document.getElementById("app-view");
  if (!container) return;

  // Always scroll to top on route change
  window.scrollTo({ top: 0, behavior: "instant" });

  // Update toggle button text
  const btnUnit = document.getElementById("btn-unit-toggle");
  if (btnUnit) {
    btnUnit.textContent = window.getUnitPreference() === "miles" ? "Unit: mi" : "Unit: km";
  }

  const token = localStorage.getItem("session_token");
  const userName = localStorage.getItem("user_name");

  // If not logged in, always redirect to login — hide chrome and bail
  const isAuthPage = hash === "#login" || hash === "#register";
  if (!token && !isAuthPage) {
    navigateTo("#login");
    return;
  }

  // Show/hide header chrome depending on auth state
  const header = document.querySelector("header");
  const footer = document.querySelector("footer");
  if (isAuthPage) {
    if (header) header.style.display = "none";
    if (footer) footer.style.display = "none";
    container.style.minHeight = "100vh";
    container.style.display = "flex";
    container.style.alignItems = "center";
    container.style.justifyContent = "center";
  } else {
    if (header) header.style.display = "";
    if (footer) footer.style.display = "";
    container.style.minHeight = "80vh";
    container.style.display = "";
    container.style.alignItems = "";
    container.style.justifyContent = "";
  }

  // Update nav visibility for logged-in users
  const authButtons = document.getElementById("nav-auth-buttons");
  const userProfile = document.getElementById("nav-user-profile");
  const usernameSpan = document.getElementById("nav-username");
  const navCurrentPlan = document.getElementById("nav-current-plan") || document.getElementById("nav-dashboard");
  const navHome = document.getElementById("nav-home");

  if (token) {
    if (authButtons) authButtons.style.display = "none";
    if (userProfile) userProfile.style.display = "flex";
    if (usernameSpan) usernameSpan.textContent = userName || "Runner";
    if (navCurrentPlan) navCurrentPlan.style.display = "block";
    if (navHome) navHome.style.display = "block";
    if (btnUnit) btnUnit.style.display = "block";
  } else {
    if (authButtons) authButtons.style.display = "none";
    if (userProfile) userProfile.style.display = "none";
    if (navCurrentPlan) navCurrentPlan.style.display = "none";
    if (navHome) navHome.style.display = "none";
    if (btnUnit) btnUnit.style.display = "none";
  }

  // Route definitions
  if (hash === "#home") {
    container.innerHTML = `
      <div style="max-width: 900px; margin: 4rem auto; text-align: center; padding: 2rem;" class="fade-in">
        <span style="text-transform: uppercase; font-size: 0.9rem; letter-spacing: 0.15em; font-weight: 700; color: var(--accent-secondary); margin-bottom: 1rem; display: block;">A professional running coach in your pocket</span>
        <h1 style="font-family: var(--font-display); font-size: 4rem; line-height: 1.1; font-weight: 800; margin-bottom: 1.5rem; background: var(--gradient-premium); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
          Personalized running training, driven by AI.
        </h1>
        <p style="color: var(--text-secondary); font-size: 1.25rem; max-width: 680px; margin: 0 auto 3rem; line-height: 1.6;">
          Connect Strava to import activity logs. Google Gemini adapts your training calendar dynamically based on fatigue, goals, course terrain, and progress.
        </p>
        <div style="display: flex; gap: 1.5rem; justify-content: center;">
          <a href="#register" class="btn btn-primary" style="font-size: 1.1rem; padding: 0.9rem 2.25rem;">Start Training Free <i data-lucide="zap"></i></a>
          <a href="#login" class="btn btn-secondary" style="font-size: 1.1rem; padding: 0.9rem 2.25rem;">Sign In</a>
        </div>
      </div>
    `;
    lucide.createIcons();
  } 
  else if (hash === "#login") {
    container.innerHTML = AuthPage.render(false);
    AuthPage.init(false, navigateTo);
  } 
  else if (hash === "#register") {
    container.innerHTML = AuthPage.render(true);
    AuthPage.init(true, navigateTo);
  } 
  else if (hash === "#onboarding") {
    if (!token) {
      navigateTo("#login");
      return;
    }
    OnboardingPage.init(navigateTo);
  } 
  else if (hash === "#current-plan" || hash === "#dashboard") {
    if (!token) {
      navigateTo("#login");
      return;
    }
    if (hash === "#dashboard") {
      navigateTo("#current-plan");
      return;
    }
    CurrentPlanPage.init(navigateTo);
  }
  else if (hash === "#profile") {
    if (!token) {
      navigateTo("#login");
      return;
    }
    ProfilePage.init(navigateTo);
  }
  else if (hash.startsWith("#session/")) {
    if (!token) {
      navigateTo("#login");
      return;
    }
    SessionDetailPage.init(navigateTo);
  }
}

// Bind Logout
const btnLogout = document.getElementById("btn-logout");
if (btnLogout) {
  btnLogout.onclick = () => {
    api.logout();
    window.showToast("Signed out successfully");
    navigateTo("#login");
    router();
  };
}

// Hash change and Load events
window.addEventListener("hashchange", router);
window.addEventListener("load", router);

// Check URL query parameters (e.g. for Strava OAuth redirects callback)
const params = new URLSearchParams(window.location.search);
if (params.get("strava") === "connected") {
  // Clear search query params
  window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
  window.showToast("Strava connected successfully!");
  navigateTo("#onboarding");
  // Set onboarding to step 3 so it goes to skip/generate stage
  OnboardingPage.state.step = 3;
}

// Run router on startup
router();
