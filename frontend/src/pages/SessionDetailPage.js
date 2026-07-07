import { api } from "../services/api.js";

export const SessionDetailPage = {
  state: {
    session: null,
    loading: true,
    error: null
  },

  async init(navigateTo) {
    this.lastNavigateTo = navigateTo;
    this.state.loading = true;
    this.state.error = null;
    this.updateView();

    // Extract session ID from hash #session/id
    const hash = window.location.hash;
    const parts = hash.split("/");
    const sessionId = parts[1];

    if (!sessionId) {
      this.state.error = "Invalid Session ID";
      this.state.loading = false;
      this.updateView();
      return;
    }

    try {
      this.state.session = await api.getSessionDetail(sessionId);
    } catch (err) {
      this.state.error = err.message || "Failed to load session details";
    } finally {
      this.state.loading = false;
      this.updateView();
    }
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
          <p style="color: var(--text-secondary); font-size: 1.1rem;">Loading workout details...</p>
        </div>
      `;
    }

    if (this.state.error) {
      return `
        <div style="max-width: 600px; margin: 5rem auto; text-align: center; padding: 3rem;" class="card glass-panel fade-in">
          <i data-lucide="alert-octagon" style="width: 64px; height: 64px; color: var(--color-intervals); margin-bottom: 1.5rem;"></i>
          <h2 style="font-family: var(--font-display); font-size: 2rem; margin-bottom: 1rem;">Error Loading Workout</h2>
          <p style="color: var(--text-secondary); margin-bottom: 2.5rem;">${this.state.error}</p>
          <a href="#current-plan" class="btn btn-secondary">
            <i data-lucide="arrow-left"></i> Back to Current Plan
          </a>
        </div>
      `;
    }

    const s = this.state.session;
    const typeClass = (s.type || "easy").toLowerCase().replace(" ", "-");
    const isKm = window.getUnitPreference() === "km";

    const getSessionBenefits = (type) => {
      const typeLower = (type || "").toLowerCase().trim();
      if (typeLower === "easy") {
        return {
          purpose: "Aerobic Conditioning & Base Building",
          benefits: [
            "Increases capillary density around muscle fibers for better oxygen delivery.",
            "Promotes mitochondrial biogenesis (the cell powerhouses that produce energy).",
            "Strengthens cardiac muscles, increasing stroke volume (heart pumps more blood per beat).",
            "Teaches the body to efficiently burn fat as a primary fuel source."
          ]
        };
      } else if (typeLower === "recovery") {
        return {
          purpose: "Active Recovery & Tissue Repair",
          benefits: [
            "Flushes metabolic waste products from muscle tissue via gentle blood circulation.",
            "Keeps the body moving to prevent stiffness without accumulating additional fatigue.",
            "Maintains neuromuscular coordination while allowing muscle fibers to repair.",
            "Mentally relaxing session to prepare for upcoming high-intensity days."
          ]
        };
      } else if (typeLower === "intervals" || typeLower === "speedwork") {
        return {
          purpose: "VO2 Max & Aerobic Power Expansion",
          benefits: [
            "Pushes the heart to its maximum stroke volume to expand aerobic capacity (VO2 Max).",
            "Recruits fast-twitch muscle fibers, enhancing power and running economy.",
            "Improves tolerance to high levels of blood lactate and acidic environments.",
            "Enhances neuromuscular coordination, making faster paces feel smoother and more natural."
          ]
        };
      } else if (typeLower === "tempo" || typeLower === "threshold") {
        return {
          purpose: "Lactate Threshold & Speed Endurance",
          benefits: [
            "Teaches the body to clear lactic acid from muscles faster than it accumulates.",
            "Increases the maximum running pace you can sustain for a long duration.",
            "Improves aerobic efficiency, allowing you to run faster with less energy expenditure.",
            "Develops mental concentration and comfort at a challenging, uncomfortable pace."
          ]
        };
      } else if (typeLower === "long run") {
        return {
          purpose: "Musculoskeletal Durability & Fat Adaptation",
          benefits: [
            "Prepares bones, joints, ligaments, and tendons to withstand hours of impact.",
            "Depletes glycogen stores, training the body to preserve carbs and burn fats at race pace.",
            "Increases blood volume and expands heart size for higher oxygen transport capacity.",
            "Builds the psychological stamina and confidence needed for long-distance races."
          ]
        };
      } else if (typeLower === "strength") {
        return {
          purpose: "Neuromuscular Power & Injury Resilience",
          benefits: [
            "Strengthens connective tissues and stabilizes joints to prevent running injuries.",
            "Improves force production, helping you generate more power per stride.",
            "Enhances core stability and posture, maintaining form when fatigue sets in.",
            "Corrects muscle imbalances that lead to common issues like IT band syndrome."
          ]
        };
      } else if (typeLower === "rest") {
        return {
          purpose: "Supercompensation & Adaptation",
          benefits: [
            "Allows muscle micro-tears to fully repair and grow back stronger.",
            "Restores muscle glycogen (carbohydrate stores) to baseline levels.",
            "Reduces systemic inflammation and stress hormone levels (cortisol).",
            "Prevents chronic overreaching, injury, and mental burnout."
          ]
        };
      } else {
        return {
          purpose: "General Fitness & Training Continuity",
          benefits: [
            "Contributes to overall weekly volume, supporting long-term aerobic progress.",
            "Maintains consistency in training routines and running habits.",
            "Promotes active recovery and joint mobility.",
            "Supports cardiovascular maintenance and mental health."
          ]
        };
      }
    };

    const benefitsData = getSessionBenefits(s.type);

    // 1. Format distance based on user preference
    let displayDistance = "N/A";
    if (s.distance_miles) {
      displayDistance = window.formatDistance(s.distance_miles);
    }

    // 2. Format pace range based on user preference
    let displayPace = s.target_pace_range || "N/A";
    if (displayPace !== "N/A") {
      if (isKm) {
        displayPace = window.formatPaceRange(displayPace);
      } else {
        displayPace = displayPace + " /mi";
      }
    }

    // 3. Format structure sets list
    const renderSetsList = (sets) => {
      if (!sets || !sets.length) return `<p style="color: var(--text-muted); font-size: 0.95rem; margin: 0;">None specified</p>`;
      return `
        <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.5rem; padding: 0;">
          ${sets.map(set => {
            if (!set) return "";
            const isObj = typeof set === 'object';
            const desc = isObj ? (set.description || "") : set;
            const rep = (isObj && typeof set.repeat !== 'function' && set.repeat) ? `${set.repeat}x ` : "";
            return `
              <li style="display: flex; gap: 0.5rem; font-size: 0.95rem; color: var(--text-primary);">
                <span style="color: var(--accent-secondary); font-weight: bold;">•</span>
                <span>${rep}${window.convertTextUnits(desc)}</span>
              </li>
            `;
          }).join("")}
        </ul>
      `;
    };

    // 4. Format safety alternative distance
    let altDistance = "0.0 mi";
    if (s.safety_alternative && s.safety_alternative.distance_miles) {
      altDistance = window.formatDistance(s.safety_alternative.distance_miles);
    }

    return `
      <div class="fade-in" style="display: flex; flex-direction: column; gap: 2rem; max-width: 900px; margin: 0 auto;">
        
        <!-- Back Button & Header -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
          <a href="#current-plan" class="btn btn-secondary">
            <i data-lucide="arrow-left" style="width: 18px; height: 18px;"></i> Back to Current Plan
          </a>
          <span style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); background: rgba(255,255,255,0.06); padding: 0.4rem 0.8rem; border-radius: 20px;">
            Status: ${s.status}
          </span>
        </div>

        <!-- Workout Header Card -->
        <div class="card" style="display: flex; flex-direction: column; gap: 1rem; border-left: 5px solid var(--color-${typeClass});">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <span class="workout-tag ${typeClass}">${s.type}</span>
            <span style="color: var(--text-muted); font-size: 0.9rem;">${s.date}</span>
          </div>
          <h2 style="font-family: var(--font-display); font-size: 2.25rem; font-weight: 800; line-height: 1.1;">
            ${s.name}
          </h2>
          <p style="color: var(--text-secondary); font-size: 1.1rem; line-height: 1.6; margin: 0;">
            ${window.convertTextUnits(s.description)}
          </p>
        </div>

        <!-- Workout Metrics Grid -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.25rem;">
          <div class="card" style="text-align: center; padding: 1.25rem;">
            <span style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary);">Distance</span>
            <div style="font-family: var(--font-display); font-size: 1.75rem; font-weight: 800; color: var(--accent-secondary); margin-top: 0.25rem;">
              ${displayDistance}
            </div>
          </div>
          <div class="card" style="text-align: center; padding: 1.25rem;">
            <span style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary);">Duration</span>
            <div style="font-family: var(--font-display); font-size: 1.75rem; font-weight: 800; color: var(--accent-secondary); margin-top: 0.25rem;">
              ${s.duration_minutes} mins
            </div>
          </div>
          <div class="card" style="text-align: center; padding: 1.25rem;">
            <span style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary);">Target Pace</span>
            <div style="font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--accent-secondary); margin-top: 0.25rem;">
              ${displayPace}
            </div>
          </div>
          <div class="card" style="text-align: center; padding: 1.25rem;">
            <span style="font-size: 0.85rem; text-transform: uppercase; font-weight: 700; color: var(--text-secondary);">Target RPE / Zone</span>
            <div style="font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--accent-secondary); margin-top: 0.25rem;">
              RPE ${s.target_rpe} | ${s.target_hr_zone}
            </div>
          </div>
        </div>

        <!-- Workout Structure Blocks -->
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; flex-wrap: wrap;">
          <div class="card" style="display: flex; flex-direction: column; gap: 1.25rem;">
            <h3 style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
              <i data-lucide="play-circle" style="color: var(--color-easy); width: 20px; height: 20px;"></i> Workout Structure
            </h3>
            
            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem;">Warm-Up</h4>
              ${renderSetsList(s.warm_up)}
            </div>

            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem;">Main Set</h4>
              ${renderSetsList(s.main_set)}
            </div>

            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem;">Cool-Down</h4>
              ${renderSetsList(s.cool_down)}
            </div>
          </div>

          <!-- Session Benefits Section -->
          <div class="card" style="display: flex; flex-direction: column; gap: 1.25rem;">
            <h3 style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
              <i data-lucide="graduation-cap" style="color: var(--accent-secondary); width: 20px; height: 20px;"></i> Training Benefits
            </h3>
            
            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.25rem;">Primary Purpose</h4>
              <p style="font-size: 1.05rem; font-weight: 700; color: var(--accent-secondary);">${benefitsData.purpose}</p>
            </div>

            <div>
              <h4 style="font-size: 0.85rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">Physiological Adaptations</h4>
              <ul style="list-style: none; display: flex; flex-direction: column; gap: 0.75rem; padding: 0;">
                ${benefitsData.benefits.map(b => `
                  <li style="display: flex; gap: 0.5rem; font-size: 0.95rem; color: var(--text-primary); line-height: 1.4;">
                    <i data-lucide="check" style="color: var(--color-easy); width: 18px; height: 18px; flex-shrink: 0; margin-top: 2px;"></i>
                    <span>${b}</span>
                  </li>
                `).join("")}
              </ul>
            </div>
          </div>
        </div>

        <!-- Safety Alternatives -->
        <div class="card" style="border: 1px solid rgba(244, 63, 94, 0.2); background: rgba(244, 63, 94, 0.02); padding: 2rem;">
          <h3 style="font-family: var(--font-display); font-size: 1.25rem; font-weight: 700; color: var(--color-intervals); margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="shield-alert" style="width: 24px; height: 24px;"></i> Safety Alternatives
          </h3>
          
          <div style="margin-bottom: 1.5rem;">
            <h4 style="font-weight: 700; font-size: 1.1rem; color: var(--text-primary); margin-bottom: 0.25rem;">
              ${s.safety_alternative.name} (${s.safety_alternative.duration_minutes ? s.safety_alternative.duration_minutes + 'm' : ''}${s.safety_alternative.distance_miles ? ' | ' + altDistance : ''})
            </h4>
            <p style="color: var(--text-secondary); font-size: 0.95rem; line-height: 1.5;">
              ${window.convertTextUnits(s.safety_alternative.description)}
            </p>
          </div>

          <div style="display: flex; gap: 0.75rem; border-top: 1px solid rgba(255,255,255,0.06); padding-top: 1.25rem; align-items: flex-start;">
            <i data-lucide="alert-circle" style="color: var(--text-muted); width: 20px; height: 20px; flex-shrink: 0; margin-top: 2px;"></i>
            <span style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; font-style: italic;">
              ${s.medical_disclaimer}
            </span>
          </div>
        </div>

      </div>
    `;
  }
};
