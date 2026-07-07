import { api } from "../services/api.js";

export const UpdatePlanDialog = {
  activePlanId: null,
  selectedDifficulty: "normal",
  userComments: "",

  async show(planId) {
    this.activePlanId = planId;
    this.selectedDifficulty = "normal";
    this.userComments = "";

    let root = document.getElementById("update-plan-modal-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "update-plan-modal-root";
      root.className = "modal-overlay";
      document.body.appendChild(root);
    }

    this.renderInputForm(root);
    root.classList.add("active");
  },

  hide() {
    const root = document.getElementById("update-plan-modal-root");
    if (root) {
      root.classList.remove("active");
    }
  },

  renderInputForm(root) {
    root.innerHTML = `
      <div class="modal-container" style="max-width: 550px;">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            Adapt Your Training Plan
          </h3>
          <button onclick="UpdatePlanDialog.hide()" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center;">
            <i data-lucide="x" style="width: 20px; height: 20px;"></i>
          </button>
        </div>
        <div class="modal-body" style="display: flex; flex-direction: column; gap: 1.5rem;">
          <p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0;">
            Struggling with workouts or finding them too easy? Give your AI Coach feedback to adapt your upcoming schedule safely.
          </p>

          <!-- Difficulty Feedback Selection Cards -->
          <div>
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">
              How is the plan going?
            </h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.75rem;">
              
              <!-- Easy Card -->
              <div id="diff-card-easy" onclick="UpdatePlanDialog.selectDifficulty('easy')" style="
                border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1rem;
                text-align: center; cursor: pointer; transition: all 0.25s ease;
                background: rgba(255,255,255,0.02);
              ">
                <i data-lucide="trending-up" style="color: var(--color-easy); width: 24px; height: 24px; margin-bottom: 0.5rem;"></i>
                <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">Too Easy</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Increase pace/volume</div>
              </div>

              <!-- Normal Card (Default selected) -->
              <div id="diff-card-normal" onclick="UpdatePlanDialog.selectDifficulty('normal')" style="
                border: 2px solid var(--accent-primary); border-radius: var(--radius-md); padding: 1rem;
                text-align: center; cursor: pointer; transition: all 0.25s ease;
                background: rgba(99, 102, 241, 0.05);
              ">
                <i data-lucide="check-circle" style="color: var(--accent-primary); width: 24px; height: 24px; margin-bottom: 0.5rem;"></i>
                <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">Just Right</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Keep current pace</div>
              </div>

              <!-- Hard Card -->
              <div id="diff-card-hard" onclick="UpdatePlanDialog.selectDifficulty('hard')" style="
                border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 1rem;
                text-align: center; cursor: pointer; transition: all 0.25s ease;
                background: rgba(255,255,255,0.02);
              ">
                <i data-lucide="alert-triangle" style="color: var(--color-intervals); width: 24px; height: 24px; margin-bottom: 0.5rem;"></i>
                <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary);">Struggling</div>
                <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">Reduce intensity</div>
              </div>

            </div>
          </div>

          <!-- Free-text request comments -->
          <div>
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">
              Request Specific Changes (Optional)
            </h4>
            <textarea id="update-user-comments" placeholder="e.g. 'I would like to move my long runs from Sundays to Saturdays' or 'Please replace speed intervals with hill repeats'..." style="
              width: 100%; height: 90px; padding: 0.75rem;
              border-radius: var(--radius-sm); border: 1px solid var(--border-color);
              background: rgba(15, 23, 42, 0.4); color: white; outline: none;
              font-family: inherit; font-size: 0.9rem; resize: none; line-height: 1.4;
            ">${this.userComments}</textarea>
          </div>

        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="UpdatePlanDialog.hide()">Cancel</button>
          <button class="btn btn-primary" onclick="UpdatePlanDialog.submitFeedback()">
            Adapt Plan Preview <i data-lucide="arrow-right"></i>
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
  },

  selectDifficulty(difficulty) {
    this.selectedDifficulty = difficulty;
    
    // Reset borders
    ["easy", "normal", "hard"].forEach(d => {
      const card = document.getElementById(`diff-card-${d}`);
      if (card) {
        card.style.border = "1px solid var(--border-color)";
        card.style.background = "rgba(255,255,255,0.02)";
      }
    });

    // Highlight selected card
    const selectedCard = document.getElementById(`diff-card-${difficulty}`);
    if (selectedCard) {
      if (difficulty === "easy") {
        selectedCard.style.border = "2px solid var(--color-easy)";
        selectedCard.style.background = "rgba(16, 185, 129, 0.05)";
      } else if (difficulty === "normal") {
        selectedCard.style.border = "2px solid var(--accent-primary)";
        selectedCard.style.background = "rgba(99, 102, 241, 0.05)";
      } else if (difficulty === "hard") {
        selectedCard.style.border = "2px solid var(--color-intervals)";
        selectedCard.style.background = "rgba(244, 63, 94, 0.05)";
      }
    }
  },

  async submitFeedback() {
    const commentsEl = document.getElementById("update-user-comments");
    if (commentsEl) {
      this.userComments = commentsEl.value.trim();
    }

    const root = document.getElementById("update-plan-modal-root");
    if (!root) return;

    // Render loading state
    root.innerHTML = `
      <div class="modal-container" style="max-width: 500px;">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            AI Coach Adapting Plan...
          </h3>
        </div>
        <div class="modal-body" style="text-align: center; padding: 3rem;">
          <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
          <p style="color: var(--text-secondary); font-size: 0.95rem;">Adapting future training sessions based on your difficulty feedback and comments...</p>
        </div>
      </div>
    `;
    lucide.createIcons();

    try {
      const data = await api.previewPlanUpdate(this.selectedDifficulty, this.userComments);
      this.renderPreview(root, data.explanation, data.sessions);
    } catch (err) {
      window.showToast(err.message || "Failed to generate plan update preview", "error");
      this.renderInputForm(root);
    }
  },

  renderPreview(root, explanation, sessions) {
    let listHtml = "";
    if (sessions.length === 0) {
      listHtml = `
        <div style="background: rgba(255,255,255,0.02); padding: 1.5rem; border-radius: var(--radius-sm); text-align: center; border: 1px solid var(--border-color);">
          <p style="color: var(--text-secondary); margin: 0;">No remaining future sessions found in plan.</p>
        </div>
      `;
    } else {
      listHtml = `
        <div style="background: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); overflow: hidden;">
          <div style="background: rgba(255,255,255,0.04); padding: 0.75rem 1rem; font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); display: grid; grid-template-columns: 1fr 1.5fr 1fr 1fr; border-bottom: 1px solid var(--border-color);">
            <span>Date</span>
            <span>Workout Name</span>
            <span>Type</span>
            <span>Distance</span>
          </div>
          <div style="max-height: 200px; overflow-y: auto;">
            ${sessions.map(s => `
              <div style="padding: 0.75rem 1rem; font-size: 0.85rem; display: grid; grid-template-columns: 1fr 1.5fr 1fr 1fr; border-bottom: 1px solid var(--border-color); align-items: center;">
                <span style="color: var(--text-muted);">${s.date}</span>
                <span style="font-weight: 600; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${s.name}">${s.name}</span>
                <span style="text-transform: capitalize; color: var(--text-secondary);">${s.type}</span>
                <span style="color: var(--accent-secondary); font-weight: 600;">
                  ${s.distance_miles > 0 ? window.formatDistance(s.distance_miles) : 'Rest'}
                </span>
              </div>
            `).join("")}
          </div>
        </div>
      `;
    }

    root.innerHTML = `
      <div class="modal-container" style="max-width: 600px;">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            Proposed Plan Adaptations
          </h3>
          <button onclick="UpdatePlanDialog.hide()" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer; display: flex; align-items: center;">
            <i data-lucide="x" style="width: 20px; height: 20px;"></i>
          </button>
        </div>
        <div class="modal-body" style="display: flex; flex-direction: column; gap: 1.5rem;">
          
          <!-- Coach Commentary Box -->
          <div class="glass-panel" style="padding: 1.25rem; border-left: 4px solid var(--accent-primary); background: rgba(30, 41, 59, 0.4); border-radius: var(--radius-sm);">
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
              <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 18px; height: 18px;"></i>
              <h5 style="margin: 0; font-weight: 700; font-size: 0.95rem;">AI Coach Adaptation Notes</h5>
            </div>
            <p style="color: var(--text-primary); font-size: 0.9rem; line-height: 1.5; margin: 0; font-style: italic;">
              "${explanation}"
            </p>
          </div>

          <!-- Updated sessions list -->
          <div>
            <h4 style="font-size: 0.9rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.75rem;">
              Proposed Future Workouts
            </h4>
            ${listHtml}
          </div>

        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" onclick="UpdatePlanDialog.renderInputForm(document.getElementById('update-plan-modal-root'))">
            <i data-lucide="arrow-left"></i> Change Request
          </button>
          <button class="btn btn-primary" onclick="UpdatePlanDialog.applyChanges()">
            Confirm & Apply Plan <i data-lucide="check"></i>
          </button>
        </div>
      </div>
    `;
    lucide.createIcons();
  },

  async applyChanges() {
    const root = document.getElementById("update-plan-modal-root");
    if (!root) return;

    // Render loading state
    root.innerHTML = `
      <div class="modal-container" style="max-width: 500px;">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            Applying Training Plan...
          </h3>
        </div>
        <div class="modal-body" style="text-align: center; padding: 3rem;">
          <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
          <p style="color: var(--text-secondary); font-size: 0.95rem;">Updating your calendar and scheduled sessions...</p>
        </div>
      </div>
    `;
    lucide.createIcons();

    try {
      await api.applyPlanUpdate(this.selectedDifficulty, this.userComments);
      window.showToast("Your training plan has been updated successfully!");
      this.hide();
      
      if (window.refreshCurrentPlanView) {
        await window.refreshCurrentPlanView();
      }
    } catch (err) {
      window.showToast(err.message || "Failed to apply plan updates", "error");
      this.hide();
    }
  }
};
