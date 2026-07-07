import { api } from "../services/api.js";

export const ProfilePage = {
  state: {
    loading: true,
    profile: null
  },

  async init(navigateTo) {
    this.lastNavigateTo = navigateTo;
    this.state.loading = true;
    this.updateView();

    try {
      const data = await api.getProfile();
      this.state.profile = data;
    } catch (err) {
      window.showToast("Failed to load profile data", "error");
    } finally {
      this.state.loading = false;
      this.updateView();
    }
  },

  updateView() {
    const container = document.getElementById("app-view");
    if (container) {
      container.innerHTML = this.render();
      if (!this.state.loading && this.state.profile) {
        this.bindEvents(this.lastNavigateTo);
      }
    }
  },

  render() {
    if (this.state.loading) {
      return `
        <div style="text-align: center; margin: 6rem auto;" class="fade-in">
          <div style="width: 50px; height: 50px; border: 4px solid var(--border-color); border-top: 4px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto 1.5rem;"></div>
          <p style="color: var(--text-secondary); font-size: 1.1rem;">Loading your profile...</p>
        </div>
      `;
    }

    const p = this.state.profile || {};

    return `
      <div style="max-width: 600px; margin: 3rem auto; padding: 2.5rem;" class="card glass-panel fade-in">
        <h2 style="font-family: var(--font-display); font-size: 2rem; margin-bottom: 0.5rem; text-align: center;">
          Profile Settings
        </h2>
        <p style="color: var(--text-secondary); text-align: center; margin-bottom: 2rem; font-size: 0.95rem;">
          Customize your running credentials and physiological zones
        </p>

        <form id="profile-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
          <!-- Basic Info -->
          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Full Name</label>
            <input type="text" id="prof-name" value="${p.name || ""}" required placeholder="Jane Doe" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth);">
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Email Address (Read-only)</label>
            <input type="email" value="${p.email || ""}" disabled style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.2); color: var(--text-muted); outline: none; font-size: 1rem; cursor: not-allowed;">
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Date of Birth</label>
              <input type="date" id="prof-dob" value="${p.date_of_birth || ""}" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Gender</label>
              <select id="prof-gender" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: #1e293b; color: white; font-size: 1rem;">
                <option value="" ${!p.gender ? "selected" : ""}>Select Gender</option>
                <option value="female" ${p.gender === "female" ? "selected" : ""}>Female</option>
                <option value="male" ${p.gender === "male" ? "selected" : ""}>Male</option>
                <option value="non-binary" ${p.gender === "non-binary" ? "selected" : ""}>Non-Binary</option>
                <option value="prefer_not_to_say" ${p.gender === "prefer_not_to_say" ? "selected" : ""}>Prefer not to say</option>
              </select>
            </div>
          </div>

          <!-- Heart Rate Zones -->
          <h3 style="font-family: var(--font-display); font-size: 1.25rem; margin-top: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Physiological Zones</h3>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Resting Heart Rate (bpm)</label>
              <input type="number" id="prof-rhr" value="${p.resting_heart_rate || ""}" placeholder="60" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Max Heart Rate (bpm)</label>
              <input type="number" id="prof-mhr" value="${p.max_heart_rate || ""}" placeholder="190" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem;">
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Threshold Heart Rate (bpm)</label>
              <input type="number" id="prof-thr" value="${p.threshold_heart_rate || ""}" placeholder="165" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
            </div>
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">VO2 Max</label>
              <input type="number" step="0.1" id="prof-vo2" value="${p.vo2_max || ""}" placeholder="45.5" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
            </div>
          </div>

          <!-- Strava API Settings -->
          <h3 style="font-family: var(--font-display); font-size: 1.25rem; margin-top: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 0.5rem;">Strava API Setup</h3>
          <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: -0.5rem;">
            Enter your custom client details to connect Strava via your own developer app.
          </p>

          <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); padding: 0.75rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color);">
            <span style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary);">Connection Status</span>
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background-color: ${p.strava_connected ? 'var(--color-easy)' : 'var(--text-muted)'};"></span>
              <span style="font-size: 0.9rem; font-weight: bold; color: ${p.strava_connected ? 'var(--color-easy)' : 'var(--text-secondary)'};">
                ${p.strava_connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Strava Client ID</label>
            <input type="text" id="prof-strava-id" value="${p.strava_client_id || ""}" placeholder="e.g. 123456" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Strava Client Secret</label>
            <input type="password" id="prof-strava-secret" value="${p.strava_client_secret || ""}" placeholder="••••••••" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem;">
          </div>

          <div style="display: flex; gap: 1rem; margin-top: 0.5rem;">
            <button id="btn-connect-strava" class="btn" style="flex: 1; background: hsl(15, 100%, 45%); color: white; justify-content: center; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; border-radius: var(--radius-sm);">
              <i data-lucide="navigation" style="width: 16px; height: 16px;"></i> Connect Strava OAuth
            </button>
            <button id="btn-test-strava" class="btn btn-secondary" style="flex: 1; justify-content: center; font-size: 0.95rem; display: flex; align-items: center; gap: 0.5rem; border-radius: var(--radius-sm);">
              <i data-lucide="shield-check" style="width: 16px; height: 16px;"></i> Test Connection
            </button>
          </div>

          <button type="submit" class="btn btn-primary" style="justify-content: center; margin-top: 1.5rem; font-size: 1.05rem;">
            Save Changes
          </button>
        </form>

        <!-- Danger Zone Section -->
        <h3 style="font-family: var(--font-display); font-size: 1.25rem; margin-top: 2.5rem; border-bottom: 1px solid rgba(244, 63, 94, 0.2); padding-bottom: 0.5rem; color: var(--color-intervals);">
          Danger Zone
        </h3>
        <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;">
          Irreversible actions for data control and privacy.
        </p>

        <div style="display: flex; flex-direction: column; gap: 1rem; margin-top: 1rem;">
          <!-- Revoke Strava -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: rgba(255,255,255,0.01); flex-wrap: wrap; gap: 1rem;">
            <div>
              <div style="font-weight: 600; font-size: 0.95rem;">Disconnect Strava</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary);">Remove Strava connection credentials.</div>
            </div>
            <button id="btn-revoke-strava" class="btn btn-secondary" style="padding: 0.5rem 1rem; border-color: rgba(255,255,255,0.15);">
              Disconnect
            </button>
          </div>

          <!-- Export Data -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; border: 1px solid var(--border-color); border-radius: var(--radius-sm); background: rgba(255,255,255,0.01); flex-wrap: wrap; gap: 1rem;">
            <div>
              <div style="font-weight: 600; font-size: 0.95rem;">Export Data</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary);">Download all profile and workout data in JSON.</div>
            </div>
            <button id="btn-export-data" class="btn btn-secondary" style="padding: 0.5rem 1rem;">
              Export JSON
            </button>
          </div>

          <!-- Delete Account -->
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem; border: 1px solid rgba(244, 63, 94, 0.2); border-radius: var(--radius-sm); background: rgba(244, 63, 94, 0.02); flex-wrap: wrap; gap: 1rem;">
            <div>
              <div style="font-weight: 600; font-size: 0.95rem; color: var(--color-intervals);">Permanently Delete Account</div>
              <div style="font-size: 0.8rem; color: var(--text-secondary);">Delete your profile and all generated plans.</div>
            </div>
            <button id="btn-delete-account" class="btn" style="background: var(--color-intervals); color: white; padding: 0.5rem 1rem; border-radius: var(--radius-sm); font-weight: 600; border: none; cursor: pointer;">
              Delete Account
            </button>
          </div>
        </div>
      </div>
    `;
  },

  bindEvents(navigateTo) {
    const form = document.getElementById("profile-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();

      const profileData = {
        name: document.getElementById("prof-name").value,
        date_of_birth: document.getElementById("prof-dob").value || null,
        gender: document.getElementById("prof-gender").value || null,
        resting_heart_rate: parseInt(document.getElementById("prof-rhr").value) || null,
        max_heart_rate: parseInt(document.getElementById("prof-mhr").value) || null,
        threshold_heart_rate: parseInt(document.getElementById("prof-thr").value) || null,
        vo2_max: parseFloat(document.getElementById("prof-vo2").value) || null,
        strava_client_id: document.getElementById("prof-strava-id").value.trim() || null,
        strava_client_secret: document.getElementById("prof-strava-secret").value.trim() || null
      };

      try {
        await api.updateProfile(profileData);
        window.showToast("Profile settings updated successfully!");
        navigateTo("#current-plan");
      } catch (err) {
        window.showToast(err.message, "error");
      }
    });

    const btnConnect = document.getElementById("btn-connect-strava");
    if (btnConnect) {
      btnConnect.onclick = async (e) => {
        e.preventDefault();
        try {
          const { url } = await api.getStravaConnectUrl();
          window.location.href = url;
        } catch (err) {
          window.showToast(err.message, "error");
        }
      };
    }

    const btnTest = document.getElementById("btn-test-strava");
    if (btnTest) {
      btnTest.onclick = async (e) => {
        e.preventDefault();
        try {
          const res = await api.testStravaConnection();
          if (res.status === "success") {
            window.showToast(res.message, "success");
          } else {
            window.showToast(res.message, "error");
          }
        } catch (err) {
          window.showToast(err.message, "error");
        }
      };
    }

    const btnRevoke = document.getElementById("btn-revoke-strava");
    if (btnRevoke) {
      btnRevoke.onclick = async (e) => {
        e.preventDefault();
        if (!confirm("Are you sure you want to disconnect your Strava integration?")) return;
        try {
          await api.revokeStrava();
          window.showToast("Strava credentials revoked successfully!");
          navigateTo("#profile");
        } catch (err) {
          window.showToast(err.message, "error");
        }
      };
    }

    const btnExport = document.getElementById("btn-export-data");
    if (btnExport) {
      btnExport.onclick = async (e) => {
        e.preventDefault();
        try {
          const data = await api.exportUserData();
          const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `aurarun_export_${new Date().toISOString().split("T")[0]}.json`;
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          window.showToast("Personal data exported successfully!");
        } catch (err) {
          window.showToast(err.message, "error");
        }
      };
    }

    const btnDelete = document.getElementById("btn-delete-account");
    if (btnDelete) {
      btnDelete.onclick = async (e) => {
        e.preventDefault();
        if (!confirm("WARNING: Are you absolutely sure you want to permanently delete your account and all associated training plan data? This action cannot be undone.")) return;
        try {
          await api.deleteAccount();
          api.logout();
          window.showToast("Your account has been deleted.", "success");
          navigateTo("#home");
          window.location.reload();
        } catch (err) {
          window.showToast(err.message, "error");
        }
      };
    }
  }
};
