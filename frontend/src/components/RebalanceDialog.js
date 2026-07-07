import { api } from "../services/api.js";

export const RebalanceDialog = {
  activePlanId: null,
  activeWeekNumber: null,

  async show(planId, warningMessage = "", weekNumber = null) {
    this.activePlanId = planId;
    this.activeWeekNumber = weekNumber;
    
    // Ensure modal container structure exists in DOM
    let root = document.getElementById("rebalance-modal-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "rebalance-modal-root";
      root.className = "modal-overlay";
      document.body.appendChild(root);
    }

    // Render loading state while retrieving AI preview
    root.innerHTML = `
      <div class="modal-container">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            AI Coach Rebalancing...
          </h3>
        </div>
        <div class="modal-body" style="text-align: center; padding: 3rem;">
          <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
          <p style="color: var(--text-secondary);">Analyzing schedule constraints and preparing adjustments...</p>
        </div>
      </div>
    `;
    root.classList.add("active");
    lucide.createIcons();

    try {
      // Fetch AI rebalance preview
      const data = await api.rebalancePlan(planId, false, weekNumber);
      const changes = data.proposed_changes || [];
      const warnings = data.warnings || [];

      // Render the review view
      this.renderContent(root, warnings, changes);
    } catch (err) {
      window.showToast("Failed to fetch rebalance recommendations", "error");
      this.hide();
    }
  },

  renderContent(root, warnings, changes) {
    const formattedWarnings = warnings.length > 0
      ? warnings.map(w => `
          <li style="display: flex; align-items: flex-start; gap: 0.5rem; color: var(--color-intervals); font-size: 0.95rem; line-height: 1.4; margin-bottom: 0.5rem;">
            <i data-lucide="alert-triangle" style="width: 18px; height: 18px; flex-shrink: 0; margin-top: 2px;"></i>
            <span>${w}</span>
          </li>
        `).join("")
      : `
          <li style="display: flex; align-items: flex-start; gap: 0.5rem; color: var(--color-easy); font-size: 0.95rem; line-height: 1.4; margin-bottom: 0.5rem;">
            <i data-lucide="check-circle" style="width: 18px; height: 18px; flex-shrink: 0; margin-top: 2px;"></i>
            <span>No schedule warnings detected. Everything looks safe!</span>
          </li>
        `;

    let changesHtml = "";
    if (changes.length === 0) {
      changesHtml = `
        <div style="background: rgba(255,255,255,0.02); padding: 1.5rem; border-radius: var(--radius-sm); text-align: center; border: 1px solid var(--border-color);">
          <p style="color: var(--text-secondary); margin: 0;">No further schedule adjustments needed. The move satisfies safety rules.</p>
        </div>
      `;
    } else {
      changesHtml = `
        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); overflow: hidden;">
          <div style="background: rgba(255,255,255,0.04); padding: 0.75rem 1rem; font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; border-bottom: 1px solid var(--border-color);">
            <span>Workout</span>
            <span>Old Date</span>
            <span>Proposed Date</span>
          </div>
          <div style="max-height: 200px; overflow-y: auto;">
            ${changes.map(c => `
              <div style="padding: 0.75rem 1rem; font-size: 0.9rem; display: grid; grid-template-columns: 2fr 1.5fr 1.5fr; border-bottom: 1px solid var(--border-color); align-items: center;">
                <span style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${c.name}</span>
                <span style="color: var(--text-muted); text-decoration: line-through;">${c.old_date}</span>
                <span style="color: var(--color-easy); font-weight: 600; display: flex; align-items: center; gap: 0.25rem;">
                  <i data-lucide="arrow-right" style="width: 14px; height: 14px;"></i> ${c.new_date}
                </span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    root.innerHTML = `
      <div class="modal-container">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            AI Coach Recommendation
          </h3>
          <button onclick="RebalanceDialog.hide()" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center;">
            <i data-lucide="x" style="width: 20px; height: 20px;"></i>
          </button>
        </div>
        <div class="modal-body" style="display: flex; flex-direction: column; gap: 1.5rem;">
          <div>
            <h4 style="font-size: 0.95rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">Safety Warnings</h4>
            <ul style="list-style: none;">
              ${formattedWarnings}
            </ul>
          </div>
          
          <div>
            <h4 style="font-size: 0.95rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">AI Schedule Rebalance</h4>
            ${changesHtml}
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="RebalanceDialog.hide()">Keep My Schedule</button>
          ${changes.length > 0 ? `
            <button class="btn btn-primary" onclick="RebalanceDialog.applyRebalance()">
              Apply AI Rebalance <i data-lucide="sparkles"></i>
            </button>
          ` : ""}
        </div>
      </div>
    `;
    lucide.createIcons();
  },

  async applyRebalance() {
    if (!this.activePlanId) return;

    let root = document.getElementById("rebalance-modal-root");
    if (root) {
      root.innerHTML = `
        <div class="modal-container">
          <div class="modal-header">
            <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
              <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
              Applying AI Rebalance...
            </h3>
          </div>
          <div class="modal-body" style="text-align: center; padding: 3rem;">
            <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
            <p style="color: var(--text-secondary);">Updating calendar dates and reorganizing sessions...</p>
          </div>
        </div>
      `;
      lucide.createIcons();
    }

    try {
      await api.rebalancePlan(this.activePlanId, true, this.activeWeekNumber);
      window.showToast("Schedule rebalanced successfully!");
      this.hide();
      
      // Full view refresh
      if (window.refreshCurrentPlanView) {
        await window.refreshCurrentPlanView();
      }
    } catch (err) {
      window.showToast(err.message || "Failed to apply rebalance", "error");
      this.hide();
    }
  },

  hide() {
    const root = document.getElementById("rebalance-modal-root");
    if (root) {
      root.classList.remove("active");
    }
    this.activePlanId = null;
    this.activeWeekNumber = null;
  }
};

// Bind to window to allow inline element calls
window.RebalanceDialog = RebalanceDialog;
