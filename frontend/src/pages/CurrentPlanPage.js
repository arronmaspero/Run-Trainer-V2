import { api } from "../services/api.js";
import { Calendar } from "../components/Calendar.js";

export const CurrentPlanPage = {
  state: {
    plan: null,
    sessions: [],
    profile: null,
    loading: true
  },

  async init(navigateTo) {
    this.lastNavigateTo = navigateTo;
    this.state.loading = true;
    this.state.isEvaluating = false;
    this.state.evalStage = 1;
    this.state.weekly_evaluations = [];
    this.state.activities = [];
    this.updateView();

    // Bind global plan page refresh triggers
    window.refreshCurrentPlanView = window.refreshDashboardView = async () => {
      try {
        const data = await api.getActivePlan();
        this.state.plan = data.plan;
        this.state.sessions = data.sessions;
        this.state.weekly_evaluations = data.weekly_evaluations || [];
        if (this.state.plan) {
          this.state.profile = await api.getProfile();
          this.state.activities = await api.getStravaActivities().catch(() => []);
        }
      } catch (err) {
        window.showToast("Failed to refresh calendar schedule", "error");
      } finally {
        this.updateView();
      }
    };

    window.refreshCurrentPlanDataOnly = window.refreshDashboardDataOnly = async () => {
      try {
        const data = await api.getActivePlan();
        this.state.plan = data.plan;
        this.state.sessions = data.sessions;
        this.state.weekly_evaluations = data.weekly_evaluations || [];
        if (this.state.plan) {
          this.state.activities = await api.getStravaActivities().catch(() => []);
        }
        // Quiet update of totals on UI without re-rendering everything (prevents dragging resets)
        const weeklyMilesText = document.getElementById("dashboard-weekly-miles");
        const progressFill = document.getElementById("dashboard-weekly-progress-fill");
        
        if (weeklyMilesText || progressFill) {
          const stats = this.calculateMileageStats();
          if (weeklyMilesText) {
            weeklyMilesText.innerHTML = `${window.formatDistance(stats.completedWeekMileage)} / <span style="color: var(--text-secondary); font-size: 1.5rem; font-weight: 500;">${window.formatDistance(stats.thisWeekMileage)}</span>`;
          }
          if (progressFill) {
            const pct = stats.thisWeekMileage > 0 ? Math.min(100, (stats.completedWeekMileage / stats.thisWeekMileage) * 100) : 0;
            progressFill.style.width = `${pct}%`;
          }
        }
      } catch (_) {}
    };

    try {
      const data = await api.getActivePlan();
      this.state.plan = data.plan;
      this.state.sessions = data.sessions;
      this.state.weekly_evaluations = data.weekly_evaluations || [];
      if (this.state.plan) {
        this.state.profile = await api.getProfile();
        this.state.activities = await api.getStravaActivities().catch(() => []);
      }
    } catch (err) {
      window.showToast("Failed to load plan metrics", "error");
    } finally {
      this.state.loading = false;
      this.updateView();
    }
  },

  calculateMileageStats() {
    if (!this.state.plan || !this.state.sessions.length) {
      return { thisWeekMileage: 0, completedWeekMileage: 0 };
    }

    const planStart = new Date(this.state.plan.start_date + "T00:00:00");
    const startDay = planStart.getDay();
    const distanceToMonday = startDay === 0 ? 6 : startDay - 1;
    const planMonday = new Date(planStart);
    planMonday.setDate(planStart.getDate() - distanceToMonday);

    const today = new Date();
    today.setHours(0,0,0,0);
    const diffTodayTime = today - planMonday;
    const diffTodayDays = Math.floor(diffTodayTime / (1000 * 60 * 60 * 24));
    const currentWeekNum = Math.max(1, Math.floor(diffTodayDays / 7) + 1);

    let thisWeekMileage = 0;
    this.state.sessions.forEach(s => {
      const sDate = new Date(s.date + "T00:00:00");
      const diffTime = sDate - planMonday;
      const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
      const wNum = Math.floor(diffDays / 7) + 1;
      if (wNum === currentWeekNum && s.distance_miles) {
        thisWeekMileage += s.distance_miles;
      }
    });

    let completedWeekMileage = 0;
    if (this.state.activities && this.state.activities.length) {
      this.state.activities.forEach(a => {
        if (!a.start_date) return;
        const aDate = new Date(a.start_date);
        const diffTime = aDate - planMonday;
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        const wNum = Math.floor(diffDays / 7) + 1;
        
        const isRun = !a.type || ["run", "trailrun", "trail run", "virtualrun"].includes(a.type.toLowerCase());
        if (wNum === currentWeekNum && isRun && a.distance_miles) {
          completedWeekMileage += a.distance_miles;
        }
      });
    }

    return { thisWeekMileage, completedWeekMileage };
  },

  updateView() {
    const container = document.getElementById("app-view");
    if (container) {
      container.innerHTML = this.render();
      lucide.createIcons();
    }
  },

  render() {
    if (this.state.loading) {
      return `
        <div style="text-align: center; margin: 6rem auto;" class="fade-in">
          <div style="width: 50px; height: 50px; border: 4px solid var(--border-color); border-top: 4px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
          <p style="color: var(--text-secondary); font-size: 1.1rem;">Loading your plan metrics...</p>
        </div>
      `;
    }

    if (!this.state.plan) {
      return `
        <div style="max-width: 600px; margin: 5rem auto; text-align: center; padding: 3rem;" class="card glass-panel fade-in">
          <i data-lucide="calendar" style="width: 64px; height: 64px; color: var(--accent-primary); margin-bottom: 1.5rem;"></i>
          <h2 style="font-family: var(--font-display); font-size: 2rem; margin-bottom: 1rem;">No Active Plan Found</h2>
          <p style="color: var(--text-secondary); margin-bottom: 2.5rem; font-size: 1.05rem;">
            You haven't generated a running training plan yet. Let's create your first lovable schedule today!
          </p>
          <a href="#onboarding" class="btn btn-primary" style="font-size: 1.1rem; padding: 0.9rem 2.25rem;">
            Create New Plan <i data-lucide="plus"></i>
          </a>
        </div>
      `;
    }

    if (this.state.isEvaluating) {
      let stageText = "Syncing Strava activities starting from Monday of Week 1...";
      if (this.state.evalStage === 2) {
        stageText = "Matching activities to plan sessions...";
      } else if (this.state.evalStage === 3) {
        stageText = "Gemini is generating coach commentaries...";
      }

      return `
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); z-index: 9999; display: flex; align-items: center; justify-content: center; color: white;" class="fade-in">
          <div style="max-width: 500px; padding: 3rem; text-align: center; background: #1e293b; border-radius: var(--radius-lg); border: 1px solid var(--border-color); box-shadow: var(--shadow-2xl);">
            <div style="width: 70px; height: 70px; border: 4px solid var(--border-color); border-top: 4px solid var(--accent-secondary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 2rem;"></div>
            <h2 style="font-family: var(--font-display); font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;">AI Performance Evaluation</h2>
            <p style="color: var(--accent-secondary); font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; margin-bottom: 1.5rem;">Phase ${this.state.evalStage} of 3</p>
            <p style="color: var(--text-secondary); font-size: 1.1rem; line-height: 1.5; min-height: 50px;">
              ${stageText}
            </p>
            <style>
              @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
          </div>
        </div>
      `;
    }

    if (this.state.isSyncingGarmin) {
      return `
        <div style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.85); backdrop-filter: blur(12px); z-index: 9999; display: flex; align-items: center; justify-content: center; color: white;" class="fade-in">
          <div style="max-width: 500px; padding: 3rem; text-align: center; background: #1e293b; border-radius: var(--radius-lg); border: 1px solid var(--border-color); box-shadow: var(--shadow-2xl);">
            <div style="width: 70px; height: 70px; border: 4px solid var(--border-color); border-top: 4px solid #007cc2; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 2rem;"></div>
            <h2 style="font-family: var(--font-display); font-size: 1.8rem; font-weight: 700; margin-bottom: 0.5rem;">Garmin Calendar Sync</h2>
            <p style="color: #007cc2; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 700; margin-bottom: 1.5rem;">Connecting to Garmin Connect</p>
            <p style="color: var(--text-secondary); font-size: 1.1rem; line-height: 1.5; min-height: 50px;">
              Generating structured watch workouts and scheduling them on your Garmin calendar...
            </p>
            <style>
              @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            </style>
          </div>
        </div>
      `;
    }

    // Calculations
    const today = new Date();
    today.setHours(0,0,0,0);
    const raceDate = new Date(this.state.plan.race_date + "T00:00:00");
    const timeDiff = raceDate.getTime() - today.getTime();
    const daysUntilRace = Math.max(0, Math.ceil(timeDiff / (1000 * 3600 * 24)));

    // Calculate dynamic mileage
    const stats = this.calculateMileageStats();

    // Find next planned workout (excluding Rest days)
    const todayStr = window.formatLocalDate(today);
    const nextSession = this.state.sessions.find(s => s.status === "planned" && s.type.toLowerCase() !== "rest" && s.date >= todayStr) 
      || this.state.sessions.find(s => s.status === "planned" && s.type.toLowerCase() !== "rest");

    // Calculate dynamic compliance
    const pastRunSessions = this.state.sessions.filter(s => s.type.toLowerCase() !== "rest" && s.date < todayStr);
    const completedPastRuns = pastRunSessions.filter(s => s.status === "completed");
    let compliancePercent = 100;
    let complianceText = "All generated workouts are matched and verified.";
    
    if (pastRunSessions.length > 0) {
      compliancePercent = Math.round((completedPastRuns.length / pastRunSessions.length) * 100);
      complianceText = `${completedPastRuns.length} of ${pastRunSessions.length} past runs completed.`;
    } else {
      const totalRuns = this.state.sessions.filter(s => s.type.toLowerCase() !== "rest").length;
      complianceText = `Plan ready! ${totalRuns} total runs scheduled.`;
    }

    return `
      <div class="fade-in" style="display: flex; flex-direction: column; gap: 2rem;">
        <!-- Top Banner: Goal Summary & Countdown -->
        <div style="background: var(--gradient-premium); padding: 2.5rem; border-radius: var(--radius-lg); color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--shadow-lg); flex-wrap: wrap; gap: 1.5rem;">
          <div>
            <span style="text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.1em; font-weight: 700; opacity: 0.8;">Target Race Goal</span>
            <h2 style="font-family: var(--font-display); font-size: 2.5rem; font-weight: 800; margin-top: 0.25rem;">
              ${this.state.plan.race_name || "Custom Run Goal"}
            </h2>
            <p style="font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
              <i data-lucide="map-pin" style="width: 18px; height: 18px;"></i>
              ${window.formatDistance(this.state.plan.race_distance_miles)} | ${this.state.plan.style} style plan
            </p>
          </div>
          <div style="text-align: right; background: rgba(0,0,0,0.25); padding: 1rem 2rem; border-radius: var(--radius-md); backdrop-filter: blur(8px);">
            <div style="font-family: var(--font-display); font-size: 2.75rem; font-weight: 900; line-height: 1;">${daysUntilRace}</div>
            <span style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; opacity: 0.8;">Days to Race</span>
          </div>
        </div>

        <!-- Metric Cards Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem;">
          <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
              <span style="color: var(--text-secondary); font-weight: 600; font-size: 0.95rem;">This Week's Mileage</span>
              <div style="background: rgba(99, 102, 241, 0.1); padding: 0.5rem; border-radius: 50%; color: var(--accent-primary);">
                <i data-lucide="activity" style="width: 20px; height: 20px;"></i>
              </div>
            </div>
            <div id="dashboard-weekly-miles" style="font-size: 2rem; font-family: var(--font-display); font-weight: 800; margin-bottom: 0.5rem;">
              ${window.formatDistance(stats.completedWeekMileage)} / <span style="color: var(--text-secondary); font-size: 1.5rem; font-weight: 500;">${window.formatDistance(stats.thisWeekMileage)}</span>
            </div>
            <div style="background: var(--border-color); height: 6px; border-radius: 3px; overflow: hidden;">
              <div id="dashboard-weekly-progress-fill" style="background: var(--gradient-premium); height: 100%; width: ${stats.thisWeekMileage > 0 ? Math.min(100, (stats.completedWeekMileage / stats.thisWeekMileage) * 100) : 0}%;"></div>
            </div>
          </div>

          <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
              <span style="color: var(--text-secondary); font-weight: 600; font-size: 0.95rem;">Plan Compliance</span>
              <div style="background: rgba(16, 185, 129, 0.1); padding: 0.5rem; border-radius: 50%; color: var(--color-easy);">
                <i data-lucide="check-circle" style="width: 20px; height: 20px;"></i>
              </div>
            </div>
            <div style="font-size: 2rem; font-family: var(--font-display); font-weight: 800; margin-bottom: 0.5rem;">
              ${compliancePercent}%
            </div>
            <p style="font-size: 0.85rem; color: var(--text-secondary);">${complianceText}</p>
          </div>

          <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
              <span style="color: var(--text-secondary); font-weight: 600; font-size: 0.95rem;">Next Key Workout</span>
              <div style="background: rgba(244, 63, 94, 0.1); padding: 0.5rem; border-radius: 50%; color: var(--color-intervals);">
                <i data-lucide="target" style="width: 20px; height: 20px;"></i>
              </div>
            </div>
            ${nextSession ? `
              <h4 style="font-family: var(--font-display); font-weight: 700; font-size: 1.15rem; margin-bottom: 0.25rem; cursor: pointer; color: var(--text-primary);" onclick="window.location.hash='#session/${nextSession.id}'">${nextSession.name}</h4>
              <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem;">${nextSession.date} | ${nextSession.duration_minutes} mins${nextSession.distance_miles ? ' | ' + window.formatDistance(nextSession.distance_miles) : ''}</p>
            ` : `
              <p style="font-size: 0.95rem; color: var(--text-muted);">No planned sessions left in this plan.</p>
            `}
          </div>
        </div>

        <!-- AI Insight Panel -->
        <div class="card glass-panel" style="padding: 2rem; border-left: 5px solid var(--accent-primary); background: rgba(30, 41, 59, 0.45);">
          <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 1rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700;">Coach's AI Recommendation</h3>
          </div>
          <p style="color: var(--text-primary); font-size: 1.05rem; line-height: 1.6;">
            "Welcome to AuraRun! Your training plan has been custom generated to safely scale your training block. Drag calendar workouts to customize your training schedule, or click on any workout card to open its target details and Garmin watch instructions."
          </p>
        </div>

        <!-- Interactive Calendar Grid Section -->
        ${Calendar.render(this.state.plan, this.state.sessions, this.state.profile?.unavailable_days || "", this.state.weekly_evaluations || [])}

        <!-- Action Buttons Row -->
        <div style="display: flex; justify-content: center; align-items: center; gap: 1rem; flex-wrap: wrap; margin-top: 1.5rem; border-top: 1px solid var(--border-color); padding-top: 2rem;">
          <a href="#onboarding" class="btn btn-primary" style="font-size: 1.05rem; padding: 0.8rem 2rem; display: inline-flex; align-items: center; gap: 0.5rem; background: var(--gradient-premium); box-shadow: var(--shadow-md);">
            <i data-lucide="plus-circle" style="width: 20px; height: 20px;"></i> Generate New Plan
          </a>
          <button onclick="window.StravaDrawer && window.StravaDrawer.show()" style="
            font-size: 1rem; padding: 0.8rem 1.75rem;
            display: inline-flex; align-items: center; gap: 0.6rem;
            background: linear-gradient(135deg, rgba(252,76,2,0.15), rgba(252,76,2,0.05));
            border: 1px solid rgba(252,76,2,0.4); border-radius: 12px;
            color: var(--text-primary); cursor: pointer; font-weight: 600;
            transition: all 0.2s ease; box-shadow: 0 2px 12px rgba(252,76,2,0.1);
          "
          onmouseover="this.style.background='linear-gradient(135deg,rgba(252,76,2,0.25),rgba(252,76,2,0.1))'; this.style.borderColor='rgba(252,76,2,0.7)'"
          onmouseout="this.style.background='linear-gradient(135deg,rgba(252,76,2,0.15),rgba(252,76,2,0.05))'; this.style.borderColor='rgba(252,76,2,0.4)'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#FC4C02"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/></svg>
            See latest Strava data
          </button>
          
          <button id="btn-evaluate-plan" onclick="window.CurrentPlanPage.handleEvaluatePlan()" style="
            font-size: 1rem; padding: 0.8rem 1.75rem;
            display: inline-flex; align-items: center; gap: 0.6rem;
            background: rgba(99, 102, 241, 0.1);
            border: 1px solid rgba(99, 102, 241, 0.4); border-radius: 12px;
            color: var(--text-primary); cursor: pointer; font-weight: 600;
            transition: all 0.2s ease; box-shadow: 0 2px 12px rgba(99,102,241,0.1);
          "
          onmouseover="this.style.background='rgba(99, 102, 241, 0.2)'; this.style.borderColor='rgba(99, 102, 241, 0.7)'"
          onmouseout="this.style.background='rgba(99, 102, 241, 0.1)'; this.style.borderColor='rgba(99, 102, 241, 0.4)'">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 18px; height: 18px;"></i>
            Evaluate Plan Progress
          </button>

          <button id="btn-update-plan" onclick="window.UpdatePlanDialog && window.UpdatePlanDialog.show(window.CurrentPlanPage.state.plan.id)" style="
            font-size: 1rem; padding: 0.8rem 1.75rem;
            display: inline-flex; align-items: center; gap: 0.6rem;
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 12px;
            color: var(--text-primary); cursor: pointer; font-weight: 600;
            transition: all 0.2s ease; box-shadow: 0 2px 12px rgba(245, 158, 11, 0.1);
          "
          onmouseover="this.style.background='rgba(245, 158, 11, 0.2)'; this.style.borderColor='rgba(245, 158, 11, 0.7)'"
          onmouseout="this.style.background='rgba(245, 158, 11, 0.1)'; this.style.borderColor='rgba(245, 158, 11, 0.4)'">
            <i data-lucide="refresh-cw" style="color: var(--accent-secondary); width: 18px; height: 18px;"></i>
            Update Plan
          </button>

          <button id="btn-sync-garmin" onclick="window.CurrentPlanPage.handleSyncGarmin()" style="
            font-size: 1rem; padding: 0.8rem 1.75rem;
            display: inline-flex; align-items: center; gap: 0.6rem;
            background: rgba(0, 124, 194, 0.1);
            border: 1px solid rgba(0, 124, 194, 0.4); border-radius: 12px;
            color: var(--text-primary); cursor: pointer; font-weight: 600;
            transition: all 0.2s ease; box-shadow: 0 2px 12px rgba(0, 124, 194, 0.1);
          "
          onmouseover="this.style.background='rgba(0, 124, 194, 0.2)'; this.style.borderColor='rgba(0, 124, 194, 0.7)'"
          onmouseout="this.style.background='rgba(0, 124, 194, 0.1)'; this.style.borderColor='rgba(0, 124, 194, 0.4)'">
            <i data-lucide="arrow-up-right" style="color: #007cc2; width: 18px; height: 18px;"></i>
            Sync to Garmin
          </button>
        </div>

      </div>
    `;
  },

  async handleEvaluatePlan() {
    this.state.isEvaluating = true;
    this.state.evalStage = 1;
    this.updateView();

    const interval = setInterval(() => {
      if (this.state.evalStage < 3) {
        this.state.evalStage += 1;
        this.updateView();
      }
    }, 2800);

    try {
      await api.evaluatePlan();
      clearInterval(interval);
      window.showToast("Evaluation complete! Your calendar and coach feedback have been updated.");
      await window.refreshCurrentPlanView();
    } catch (err) {
      clearInterval(interval);
      window.showToast(err.message, "error");
    } finally {
      this.state.isEvaluating = false;
      this.updateView();
    }
  },

  async handleSyncGarmin() {
    if (!this.state.profile || !this.state.profile.garmin_connected) {
      window.showToast("Please set up your Garmin Connect credentials in Profile Settings first.", "error");
      return;
    }

    this.state.isSyncingGarmin = true;
    this.updateView();

    try {
      const res = await api.pushPlanToGarmin();
      window.showToast(res.message || "Workouts successfully synced to Garmin Connect!", "success");
    } catch (err) {
      window.showToast(err.message || "Failed to push workouts to Garmin Connect.", "error");
    } finally {
      this.state.isSyncingGarmin = false;
      this.updateView();
    }
  }
};
