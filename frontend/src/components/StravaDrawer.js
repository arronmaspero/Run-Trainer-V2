import { api } from "../services/api.js";

export const StravaDrawer = {

  // ─── Show the activity list drawer ───────────────────────────────────────
  async show() {
    let drawer = document.getElementById("strava-drawer");
    if (!drawer) {
      drawer = document.createElement("div");
      drawer.id = "strava-drawer";
      document.body.appendChild(drawer);
    }

    drawer.innerHTML = `
      <div id="strava-drawer-backdrop" onclick="window.StravaDrawer.hide()" style="
        position: fixed; inset: 0; background: rgba(0,0,0,0.55); z-index: 900;
        animation: fadeIn 0.2s ease;
      "></div>
      <div id="strava-drawer-panel" style="
        position: fixed; top: 0; right: 0; height: 100vh; width: min(560px, 100vw);
        background: var(--bg-app); border-left: 1px solid var(--border-color);
        z-index: 901; display: flex; flex-direction: column;
        animation: slideInRight 0.3s cubic-bezier(0.4,0,0.2,1);
        box-shadow: -8px 0 40px rgba(0,0,0,0.4);
      ">
        <!-- Header -->
        <div style="
          padding: 1.5rem; border-bottom: 1px solid var(--border-color);
          display: flex; align-items: center; justify-content: space-between;
          background: linear-gradient(135deg, rgba(252,76,2,0.12), rgba(252,76,2,0.04));
          flex-shrink: 0;
        ">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="
              width: 40px; height: 40px; border-radius: 10px;
              background: linear-gradient(135deg, #FC4C02, #e03d00);
              display: flex; align-items: center; justify-content: center;
            ">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="white">
                <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/>
              </svg>
            </div>
            <div>
              <h2 style="font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; margin: 0;">Your Strava Activities</h2>
              <p style="font-size: 0.8rem; color: var(--text-secondary); margin: 0;">Last 90 days synced at plan generation</p>
            </div>
          </div>
          <button onclick="window.StravaDrawer.hide()" style="
            background: none; border: 1px solid var(--border-color); border-radius: 8px;
            color: var(--text-secondary); cursor: pointer; padding: 0.4rem 0.7rem;
            font-size: 1.1rem; line-height: 1; transition: all 0.15s;
          " onmouseover="this.style.color='var(--text-primary)'" onmouseout="this.style.color='var(--text-secondary)'">✕</button>
        </div>

        <!-- Body: scrollable content -->
        <div id="strava-drawer-body" style="flex: 1; overflow-y: auto; padding: 1.5rem;">
          <div style="text-align: center; padding: 3rem 0;">
            <div style="
              width: 36px; height: 36px; border: 3px solid var(--border-color);
              border-top: 3px solid #FC4C02; border-radius: 50%;
              animation: spin 1s linear infinite; margin: 0 auto 1rem;
            "></div>
            <p style="color: var(--text-secondary);">Loading activities...</p>
          </div>
        </div>
      </div>
    `;

    // Inject keyframe animations if not already present
    if (!document.getElementById("strava-drawer-styles")) {
      const style = document.createElement("style");
      style.id = "strava-drawer-styles";
      style.textContent = `
        @keyframes slideInRight {
          from { transform: translateX(100%); opacity: 0; }
          to   { transform: translateX(0);    opacity: 1; }
        }
        @keyframes fadeIn {
          from { opacity: 0; } to { opacity: 1; }
        }
        .strava-card {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 1rem 1.25rem;
          cursor: pointer;
          transition: all 0.18s ease;
          position: relative;
          overflow: hidden;
        }
        .strava-card::before {
          content: '';
          position: absolute;
          top: 0; left: 0;
          width: 4px; height: 100%;
          background: linear-gradient(180deg, #FC4C02, #e03d00);
          border-radius: 4px 0 0 4px;
        }
        .strava-card:hover {
          border-color: rgba(252,76,2,0.4);
          transform: translateY(-2px);
          box-shadow: 0 4px 20px rgba(252,76,2,0.15);
        }
        .stat-chip {
          display: flex; align-items: center; gap: 0.35rem;
          font-size: 0.8rem; color: var(--text-secondary);
        }
        .stat-chip strong { color: var(--text-primary); font-weight: 600; }
      `;
      document.head.appendChild(style);
    }

    try {
      const activities = await api.getStravaActivities();
      this.renderActivityGrid(activities);
    } catch (err) {
      const body = document.getElementById("strava-drawer-body");
      if (body) {
        body.innerHTML = `
          <div style="text-align: center; padding: 3rem 0; color: var(--text-secondary);">
            <div style="font-size: 3rem; margin-bottom: 1rem;">🏃</div>
            <p style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">No Strava activities found</p>
            <p style="font-size: 0.9rem;">Generate a new plan while connected to Strava to sync your recent activities.</p>
          </div>
        `;
      }
    }
  },

  renderActivityGrid(activities) {
    const body = document.getElementById("strava-drawer-body");
    if (!body) return;

    if (!activities || activities.length === 0) {
      body.innerHTML = `
        <div style="text-align: center; padding: 3rem 0; color: var(--text-secondary);">
          <div style="font-size: 3rem; margin-bottom: 1rem;">🏃</div>
          <p style="font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">No activities yet</p>
          <p style="font-size: 0.9rem;">Generate a training plan while connected to Strava to sync your recent runs.</p>
        </div>
      `;
      return;
    }

    const formatDate = (isoStr) => {
      if (!isoStr) return "";
      const d = new Date(isoStr);
      return d.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" });
    };

    const typeIcon = (type) => {
      const icons = { run: "🏃", ride: "🚴", swim: "🏊", walk: "🚶", hike: "🥾" };
      return icons[type?.toLowerCase()] || "🏃";
    };

    const cards = activities.map(a => `
      <div class="strava-card" onclick="window.StravaDrawer.showDetail('${a.id}')">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.2rem;">
              <span style="font-size: 1.1rem;">${typeIcon(a.type)}</span>
              <span style="font-weight: 700; font-size: 0.95rem; color: var(--text-primary);">${a.name}</span>
            </div>
            <div style="font-size: 0.78rem; color: var(--text-secondary);">${formatDate(a.start_date)}</div>
          </div>
          <span style="font-size: 0.7rem; background: rgba(252,76,2,0.12); color: #FC4C02; border-radius: 20px; padding: 0.2rem 0.6rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;">${a.type || "Run"}</span>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.5rem;">
          <div class="stat-chip">
            <span>📏</span><div><div style="font-size:0.7rem;color:var(--text-secondary);">Distance</div><strong>${window.formatDistance ? window.formatDistance(a.distance_miles) : a.distance_miles + " mi"}</strong></div>
          </div>
          <div class="stat-chip">
            <span>⏱</span><div><div style="font-size:0.7rem;color:var(--text-secondary);">Time</div><strong>${a.moving_time_formatted}</strong></div>
          </div>
          <div class="stat-chip">
            <span>⚡</span><div><div style="font-size:0.7rem;color:var(--text-secondary);">Pace</div><strong>${window.convertTextUnits ? window.convertTextUnits(a.pace) : a.pace}</strong></div>
          </div>
          ${a.average_heart_rate ? `<div class="stat-chip"><span>❤️</span><div><div style="font-size:0.7rem;color:var(--text-secondary);">Avg HR</div><strong>${a.average_heart_rate} bpm</strong></div></div>` : ""}
          ${a.elevation_gain_feet ? `<div class="stat-chip"><span>⛰️</span><div><div style="font-size:0.7rem;color:var(--text-secondary);">Elevation</div><strong>${a.elevation_gain_feet} ft</strong></div></div>` : ""}
        </div>
        <div style="margin-top: 0.75rem; text-align: right; font-size: 0.78rem; color: rgba(252,76,2,0.7); font-weight: 600;">View details →</div>
      </div>
    `).join("");

    body.innerHTML = `
      <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 1rem;">${activities.length} activit${activities.length === 1 ? "y" : "ies"} found</p>
      <div style="display: flex; flex-direction: column; gap: 0.85rem;">
        ${cards}
      </div>
    `;
  },

  // ─── Show detail modal for one activity ────────────────────────────────────
  async showDetail(activityId) {
    let modal = document.getElementById("strava-detail-modal");
    if (!modal) {
      modal = document.createElement("div");
      modal.id = "strava-detail-modal";
      document.body.appendChild(modal);
    }

    modal.innerHTML = `
      <div style="
        position: fixed; inset: 0; z-index: 1000;
        display: flex; align-items: center; justify-content: center;
        background: rgba(0,0,0,0.65); padding: 1rem;
        animation: fadeIn 0.2s ease;
      " onclick="if(event.target===this) window.StravaDrawer.hideDetail()">
        <div style="
          background: var(--bg-app); border: 1px solid var(--border-color);
          border-radius: 20px; width: 100%; max-width: 580px;
          max-height: 85vh; overflow-y: auto;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5);
          animation: slideUp 0.25s cubic-bezier(0.4,0,0.2,1);
        ">
          <div style="text-align: center; padding: 3rem 0;">
            <div style="
              width: 36px; height: 36px; border: 3px solid var(--border-color);
              border-top: 3px solid #FC4C02; border-radius: 50%;
              animation: spin 1s linear infinite; margin: 0 auto 1rem;
            "></div>
            <p style="color: var(--text-secondary);">Loading activity...</p>
          </div>
        </div>
      </div>
    `;

    // Inject slideUp keyframe
    if (!document.getElementById("strava-detail-styles")) {
      const s = document.createElement("style");
      s.id = "strava-detail-styles";
      s.textContent = `
        @keyframes slideUp {
          from { transform: translateY(30px); opacity: 0; }
          to   { transform: translateY(0); opacity: 1; }
        }
        .detail-stat-tile {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px; padding: 1rem;
          text-align: center;
        }
        .splits-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .splits-table th {
          text-align: left; padding: 0.5rem 0.75rem;
          border-bottom: 1px solid var(--border-color);
          color: var(--text-secondary); font-weight: 600; font-size: 0.78rem;
          text-transform: uppercase; letter-spacing: 0.05em;
        }
        .splits-table td {
          padding: 0.5rem 0.75rem; border-bottom: 1px solid rgba(255,255,255,0.05);
          color: var(--text-primary);
        }
        .splits-table tr:last-child td { border-bottom: none; }
        .splits-table tr:hover td { background: rgba(255,255,255,0.03); }
      `;
      document.head.appendChild(s);
    }

    try {
      const a = await api.getStravaActivity(activityId);
      this.renderDetail(modal, a);
    } catch (err) {
      this.hideDetail();
      window.showToast("Failed to load activity details", "error");
    }
  },

  renderDetail(modal, a) {
    const formatDate = (isoStr) => {
      if (!isoStr) return "";
      const d = new Date(isoStr);
      return d.toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" });
    };

    const statTile = (icon, label, value) => value ? `
      <div class="detail-stat-tile">
        <div style="font-size: 1.6rem; margin-bottom: 0.25rem;">${icon}</div>
        <div style="font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">${value}</div>
        <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.15rem;">${label}</div>
      </div>
    ` : "";

    const splitsHtml = a.splits && a.splits.length > 0 ? `
      <div style="margin-top: 1.5rem;">
        <h3 style="font-size: 0.9rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 0.75rem;">
          Splits
        </h3>
        <div style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: 12px; overflow: hidden;">
          <table class="splits-table">
            <thead>
              <tr>
                <th>Lap</th>
                <th>Dist</th>
                <th>Time</th>
                <th>Pace</th>
                ${a.splits[0]?.average_heartrate ? "<th>HR</th>" : ""}
                <th>Elev</th>
              </tr>
            </thead>
            <tbody>
              ${a.splits.map(sp => `
                <tr>
                  <td style="font-weight: 600; color: #FC4C02;">${sp.lap}</td>
                  <td>${window.formatDistance ? window.formatDistance(sp.distance) : sp.distance + " mi"}</td>
                  <td>${sp.moving_time_formatted}</td>
                  <td>${window.convertTextUnits ? window.convertTextUnits(sp.pace) : sp.pace}</td>
                  ${sp.average_heartrate ? `<td>${Math.round(sp.average_heartrate)} bpm</td>` : ""}
                  <td>${sp.elevation_difference > 0 ? "+" : ""}${sp.elevation_difference} ft</td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>
      </div>
    ` : "";

    const distStr = window.formatDistance ? window.formatDistance(a.distance_miles) : `${a.distance_miles} mi`;

    modal.innerHTML = `
      <div style="
        position: fixed; inset: 0; z-index: 1000;
        display: flex; align-items: center; justify-content: center;
        background: rgba(0,0,0,0.65); padding: 1rem;
      " onclick="if(event.target===this) window.StravaDrawer.hideDetail()">
        <div style="
          background: var(--bg-app); border: 1px solid var(--border-color);
          border-radius: 20px; width: 100%; max-width: 580px;
          max-height: 85vh; overflow-y: auto;
          box-shadow: 0 20px 60px rgba(0,0,0,0.5);
        ">
          <!-- Detail header -->
          <div style="
            padding: 1.5rem; border-bottom: 1px solid var(--border-color);
            background: linear-gradient(135deg, rgba(252,76,2,0.1), transparent);
            border-radius: 20px 20px 0 0;
          ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
              <div>
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.3rem;">
                  <span style="font-size: 1.4rem;">🏃</span>
                  <h2 style="font-family: var(--font-display); font-size: 1.3rem; font-weight: 700; margin: 0;">${a.name}</h2>
                </div>
                <div style="font-size: 0.85rem; color: var(--text-secondary);">${formatDate(a.start_date)}</div>
              </div>
              <div style="display: flex; gap: 0.5rem; align-items: center;">
                <button onclick="window.StravaDrawer.hideDetail()" style="
                  background: none; border: 1px solid var(--border-color); border-radius: 8px;
                  color: var(--text-secondary); cursor: pointer; padding: 0.4rem 0.7rem;
                  font-size: 1rem; transition: all 0.15s;
                ">✕</button>
              </div>
            </div>
          </div>

          <!-- Stats grid -->
          <div style="padding: 1.5rem;">
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin-bottom: 0.75rem;">
              ${statTile("📏", "Distance", distStr)}
              ${statTile("⏱", "Moving Time", a.moving_time_formatted)}
              ${statTile("⚡", "Avg Pace", window.convertTextUnits ? window.convertTextUnits(a.pace) : a.pace)}
              ${statTile("❤️", "Avg Heart Rate", a.average_heart_rate ? `${a.average_heart_rate} bpm` : null)}
              ${statTile("⛰️", "Elevation Gain", a.elevation_gain_feet ? `${a.elevation_gain_feet} ft` : null)}
              ${statTile("🦵", "Avg Cadence", a.average_cadence ? `${a.average_cadence} spm` : null)}
            </div>

            ${splitsHtml}

            <!-- Footer actions -->
            <div style="display: flex; justify-content: flex-end; gap: 0.75rem; margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border-color);">
              ${a.strava_activity_id ? `
                <a href="https://www.strava.com/activities/${a.strava_activity_id}" target="_blank" style="
                  display: flex; align-items: center; gap: 0.5rem;
                  background: linear-gradient(135deg, #FC4C02, #e03d00);
                  color: white; border: none; border-radius: 10px;
                  padding: 0.6rem 1.2rem; font-size: 0.85rem; font-weight: 600;
                  cursor: pointer; text-decoration: none; transition: opacity 0.15s;
                " onmouseover="this.style.opacity='0.85'" onmouseout="this.style.opacity='1'">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="white"><path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066m-7.008-5.599l2.836 5.598h4.172L10.463 0l-7 13.828h4.169"/></svg>
                  View on Strava
                </a>
              ` : ""}
              <button onclick="window.StravaDrawer.hideDetail()" style="
                background: var(--bg-card); border: 1px solid var(--border-color);
                color: var(--text-primary); border-radius: 10px;
                padding: 0.6rem 1.2rem; font-size: 0.85rem; font-weight: 600;
                cursor: pointer; transition: all 0.15s;
              ">← Back to list</button>
            </div>
          </div>
        </div>
      </div>
    `;
  },

  hide() {
    const drawer = document.getElementById("strava-drawer");
    if (drawer) drawer.innerHTML = "";
  },

  hideDetail() {
    const modal = document.getElementById("strava-detail-modal");
    if (modal) modal.innerHTML = "";
  }
};

window.StravaDrawer = StravaDrawer;
