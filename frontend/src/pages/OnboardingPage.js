import { api } from "../services/api.js";

export const OnboardingPage = {
  state: {
    step: 1,
    weekly_volume_miles: 20,
    runs_per_week: 3,
    long_run_day: "Sunday",
    unavailable_days: "Monday,Friday",
    race_name: "",
    race_date: "",
    race_distance: "half marathon",
    target_time: "02:00:00",
    style: "balanced",
    isGenerating: false,
    additional_notes: ""
  },

  render() {
    if (this.state.isGenerating) {
      return `
        <div style="max-width: 600px; margin: 6rem auto; text-align: center;" class="card glass-panel fade-in">
          <div style="width: 80px; height: 80px; border: 5px solid var(--border-color); border-top: 5px solid var(--accent-secondary); border-radius: 50%; animation: spin 1s linear infinite; margin: 2rem auto;"></div>
          <h2 style="font-family: var(--font-display); font-size: 2.25rem; margin-bottom: 1rem;">Crafting Your Lovable Plan</h2>
          <p style="color: var(--text-secondary); margin-bottom: 2rem; font-size: 1.1rem;">
            Google Gemini is analyzing your profile, running history, and race goals to generate your structured training calendar...
          </p>
          <div style="background: var(--border-color); height: 8px; border-radius: 4px; overflow: hidden; max-width: 300px; margin: 0 auto;">
            <div style="background: var(--gradient-premium); height: 100%; width: 75%; animation: progressPulse 2s infinite ease-in-out;"></div>
          </div>
          
          <style>
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            @keyframes progressPulse { 0% { transform: translateX(-100%); } 100% { transform: translateX(150%); } }
          </style>
        </div>
      `;
    }

    return `
      <div style="max-width: 720px; margin: 3rem auto;" class="card glass-panel fade-in">
        <!-- Steps Header -->
        <div style="display: flex; justify-content: space-between; margin-bottom: 3rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color);">
          <div style="display: flex; align-items: center; gap: 0.5rem; opacity: ${this.state.step === 1 ? '1' : '0.5'}">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: var(--gradient-premium); color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85rem;">1</div>
            <span style="font-family: var(--font-display); font-weight: 600;">Running Profile</span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem; opacity: ${this.state.step === 2 ? '1' : '0.5'}">
            <div style="width: 28px; height: 28px; border-radius: 50%; background: ${this.state.step >= 2 ? 'var(--gradient-premium)' : 'var(--border-color)'}; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 0.85rem;">2</div>
            <span style="font-family: var(--font-display); font-weight: 600;">Race Goals</span>
          </div>
        </div>

        <!-- Wizard Steps Content -->
        <div id="step-content">
          ${this.renderStep()}
        </div>
      </div>
    `;
  },

  renderStep() {
    if (this.state.step === 1) {
      return `
        <h3 style="font-family: var(--font-display); font-size: 1.75rem; margin-bottom: 0.5rem;">Your Running Baseline</h3>
        <p style="color: var(--text-secondary); margin-bottom: 2rem;">Let us know your current running habits to create a safe, adaptive progression.</p>
        
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Current Weekly Volume (${window.getUnitPreference() === "miles" ? "miles" : "km"})</label>
              <input type="number" id="volume" value="${window.getUnitPreference() === "km" ? Math.round(this.state.weekly_volume_miles * 1.60934) : this.state.weekly_volume_miles}" min="0" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Runs per Week</label>
              <select id="runs-count" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: #1e293b; color: white; font-size: 1rem;">
                <option value="2" ${this.state.runs_per_week === 2 ? "selected" : ""}>2 runs/week</option>
                <option value="3" ${this.state.runs_per_week === 3 ? "selected" : ""}>3 runs/week (Recommended)</option>
                <option value="4" ${this.state.runs_per_week === 4 ? "selected" : ""}>4 runs/week</option>
                <option value="5" ${this.state.runs_per_week === 5 ? "selected" : ""}>5+ runs/week</option>
              </select>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Preferred Long Run Day</label>
              <select id="long-day" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: #1e293b; color: white; font-size: 1rem;">
                <option value="Saturday" ${this.state.long_run_day === "Saturday" ? "selected" : ""}>Saturday</option>
                <option value="Sunday" ${this.state.long_run_day === "Sunday" ? "selected" : ""}>Sunday</option>
              </select>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Unavailable Days (Comma-separated)</label>
              <input type="text" id="unavailable" value="${this.state.unavailable_days}" placeholder="Monday, Friday" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
          </div>

          <div style="display: flex; justify-content: flex-end; margin-top: 1.5rem;">
            <button id="btn-next" class="btn btn-primary">Next Step <i data-lucide="arrow-right"></i></button>
          </div>
        </div>
      `;
    }

    if (this.state.step === 2) {
      return `
        <h3 style="font-family: var(--font-display); font-size: 1.75rem; margin-bottom: 0.5rem;">Race Goals</h3>
        <p style="color: var(--text-secondary); margin-bottom: 2rem;">Gemini will search course details to tailor hill climbs, paces, and taper schedules.</p>
        
        <div style="display: flex; flex-direction: column; gap: 1.5rem;">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Race Name (Optional)</label>
              <input type="text" id="race-name" value="${this.state.race_name}" placeholder="e.g., Boston Marathon" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Race Date</label>
              <input type="date" id="race-date" value="${this.state.race_date}" required style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Race Distance</label>
              <select id="distance" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: #1e293b; color: white; font-size: 1rem;">
                <option value="5k" ${this.state.race_distance === "5k" ? "selected" : ""}>5K</option>
                <option value="10k" ${this.state.race_distance === "10k" ? "selected" : ""}>10K</option>
                <option value="half marathon" ${this.state.race_distance === "half marathon" ? "selected" : ""}>Half Marathon</option>
                <option value="marathon" ${this.state.race_distance === "marathon" ? "selected" : ""}>Marathon</option>
                <option value="custom" ${this.state.race_distance === "custom" || (!["5k", "10k", "half marathon", "marathon"].includes(this.state.race_distance) && this.state.race_distance) ? "selected" : ""}>Custom Distance...</option>
              </select>
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Target Time (HH:MM:SS)</label>
              <input type="text" id="target-time" value="${this.state.target_time}" placeholder="03:45:00" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
          </div>

          <!-- Custom Distance Input Container -->
          <div id="custom-distance-container" style="display: ${this.state.race_distance === "custom" || (!["5k", "10k", "half marathon", "marathon"].includes(this.state.race_distance) && this.state.race_distance) ? "grid" : "none"}; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-top: 0.5rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Custom Distance Value</label>
              <input type="number" id="custom-distance-val" step="0.1" min="0.1" value="${this.getCustomDistanceVal()}" placeholder="15" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Custom Distance Unit</label>
              <select id="custom-distance-unit" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: #1e293b; color: white; font-size: 1rem;">
                <option value="miles" ${this.getCustomDistanceUnit() === "miles" ? "selected" : ""}>Miles (mi)</option>
                <option value="km" ${this.getCustomDistanceUnit() === "km" ? "selected" : ""}>Kilometers (km)</option>
              </select>
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; color: var(--text-secondary); font-weight: 500;">Additional notes for your AI coach (optional)</label>
            <textarea id="additional-notes" placeholder="e.g. I have a knee injury, I prefer trail running, I want to peak for the first 3 weeks..." style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; font-size: 1rem; min-height: 100px; resize: vertical; font-family: inherit; line-height: 1.5;">${this.state.additional_notes || ""}</textarea>
          </div>

          <div style="display: flex; justify-content: space-between; margin-top: 1.5rem;">
            <button id="btn-back" class="btn btn-secondary"><i data-lucide="arrow-left"></i> Back</button>
            <button id="btn-generate" class="btn btn-primary">Generate Training Plan <i data-lucide="check"></i></button>
          </div>
        </div>
      `;
    }
  },

  handleNext() {
    if (this.state.step === 1) {
      const volInput = parseFloat(document.getElementById("volume").value) || 20;
      const pref = window.getUnitPreference();
      this.state.weekly_volume_miles = pref === "km" ? volInput * 0.621371 : volInput;
      this.state.runs_per_week = parseInt(document.getElementById("runs-count").value) || 3;
      this.state.long_run_day = document.getElementById("long-day").value;
      this.state.unavailable_days = document.getElementById("unavailable").value;
      
      this.state.step = 2;
      this.updateView();
    }
  },

  handleBack() {
    if (this.state.step === 2) {
      this.state.race_name = document.getElementById("race-name").value;
      this.state.race_date = document.getElementById("race-date").value;
      
      const distSelect = document.getElementById("distance").value;
      if (distSelect === "custom") {
        const val = parseFloat(document.getElementById("custom-distance-val").value);
        const unit = document.getElementById("custom-distance-unit").value;
        if (!isNaN(val) && val > 0) {
          this.state.race_distance = `${val} ${unit}`;
        }
      } else {
        this.state.race_distance = distSelect;
      }
      this.state.target_time = document.getElementById("target-time").value;
      
      const notesEl = document.getElementById("additional-notes");
      if (notesEl) {
        this.state.additional_notes = notesEl.value;
      }
    }
    if (this.state.step > 1) {
      this.state.step -= 1;
      this.updateView();
    }
  },

  handleGeneratePlan(navigateTo) {
    this.state.race_name = document.getElementById("race-name").value;
    this.state.race_date = document.getElementById("race-date").value;
    
    const distSelect = document.getElementById("distance").value;
    if (distSelect === "custom") {
      const val = parseFloat(document.getElementById("custom-distance-val").value);
      const unit = document.getElementById("custom-distance-unit").value;
      if (isNaN(val) || val <= 0) {
        window.showToast("Please enter a valid custom distance", "error");
        return;
      }
      this.state.race_distance = `${val} ${unit}`;
    } else {
      this.state.race_distance = distSelect;
    }
    this.state.target_time = document.getElementById("target-time").value;
    
    const notesEl = document.getElementById("additional-notes");
    if (notesEl) {
      this.state.additional_notes = notesEl.value;
    }
    
    if (!this.state.race_date) {
      window.showToast("Race date is required", "error");
      return;
    }
    
    this.triggerPlanGeneration(navigateTo);
  },

  getCustomDistanceVal() {
    const dist = this.state.race_distance;
    if (!dist || ["5k", "10k", "half marathon", "marathon", "custom"].includes(dist)) {
      return "";
    }
    const match = dist.match(/([0-9.]+)/);
    return match ? match[1] : "";
  },

  getCustomDistanceUnit() {
    const dist = this.state.race_distance;
    if (!dist || ["5k", "10k", "half marathon", "marathon", "custom"].includes(dist)) {
      return window.getUnitPreference();
    }
    if (dist.includes("km") || dist.includes("kilometer")) {
      return "km";
    }
    return "miles";
  },

  async triggerPlanGeneration(navigateTo) {
    this.state.isGenerating = true;
    this.updateView();
    
    try {
      await api.generatePlan({
        weekly_volume_miles: this.state.weekly_volume_miles,
        runs_per_week: this.state.runs_per_week,
        long_run_day: this.state.long_run_day,
        unavailable_days: this.state.unavailable_days,
        race_name: this.state.race_name,
        race_date: this.state.race_date,
        race_distance: this.state.race_distance,
        target_time: this.state.target_time,
        style: this.state.style,
        additional_notes: this.state.additional_notes
      });
      window.showToast("Your training plan has been successfully generated!");
      navigateTo("#current-plan");
    } catch (err) {
      this.state.isGenerating = false;
      this.updateView();
      window.showToast(err.message, "error");
    }
  },

  updateView() {
    const container = document.getElementById("app-view");
    if (container) {
      container.innerHTML = this.render();
      lucide.createIcons();
      this.bindEvents(this.lastNavigateTo);
    }
  },

  async init(navigateTo) {
    this.lastNavigateTo = navigateTo;
    this.state.step = 1;
    this.state.isGenerating = false;
    this.state.strava_connected = false;
    this.state.additional_notes = "";
    try {
      const profile = await api.getProfile();
      if (profile) {
        this.state.weekly_volume_miles = profile.weekly_volume_miles || 20;
        this.state.runs_per_week = profile.runs_per_week || 3;
        this.state.long_run_day = profile.long_run_day || "Sunday";
        this.state.unavailable_days = profile.unavailable_days || "Monday,Friday";
        this.state.strava_connected = profile.strava_connected || false;
      }
    } catch (_) {}
    this.updateView();
  },

  bindEvents(navigateTo) {
    const btnNext = document.getElementById("btn-next");
    const btnBack = document.getElementById("btn-back");
    const btnGenerate = document.getElementById("btn-generate");
    const distanceSelect = document.getElementById("distance");

    if (btnNext) {
      btnNext.onclick = () => this.handleNext();
    }
    if (btnBack) {
      btnBack.onclick = () => this.handleBack();
    }
    if (btnGenerate) {
      btnGenerate.onclick = () => this.handleGeneratePlan(navigateTo);
    }
    if (distanceSelect) {
      distanceSelect.onchange = () => {
        const customContainer = document.getElementById("custom-distance-container");
        if (customContainer) {
          customContainer.style.display = distanceSelect.value === "custom" ? "grid" : "none";
        }
      };
    }
  }
};
