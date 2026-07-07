import { CalendarDragDrop } from "./CalendarDragDrop.js";
import { api } from "../services/api.js";

export const Calendar = {
  expandedWeeks: null,

  render(plan, sessions, unavailableDaysStr, weeklyEvaluations = []) {
    if (!plan || !sessions.length) return "";

    const evaluationsByWeek = {};
    if (weeklyEvaluations) {
      weeklyEvaluations.forEach(ev => {
        evaluationsByWeek[ev.week_number] = ev.commentary;
      });
    }

    const unavailableDays = (unavailableDaysStr || "").split(",").map(d => d.trim().toLowerCase());

    // 1. Calculate the starting Monday of the training plan
    const planStart = new Date(plan.start_date + "T00:00:00");
    const startDay = planStart.getDay(); // 0 = Sun, 1 = Mon, ..., 6 = Sat
    const distanceToMonday = startDay === 0 ? 6 : startDay - 1;
    const planMonday = new Date(planStart);
    planMonday.setDate(planStart.getDate() - distanceToMonday);

    // 2. Group sessions by week
    // Calculate total weeks from the plan's actual start and end dates
    const planEnd = new Date(plan.end_date + "T00:00:00");
    const planDays = Math.round((planEnd - planMonday) / (1000 * 60 * 60 * 24));
    const totalWeeks = Math.max(1, Math.ceil(planDays / 7));

    const weeks = {};
    for (let w = 1; w <= totalWeeks; w++) {
      weeks[w] = Array(7).fill(null).map(() => []);
    }

    sessions.forEach(s => {
      const sDate = new Date(s.date + "T00:00:00");
      const diffTime = sDate - planMonday;
      const diffDays = Math.round(diffTime / (1000 * 60 * 60 * 24));
      
      const weekNum = Math.floor(diffDays / 7) + 1;
      const dayIndex = (sDate.getDay() + 6) % 7; // 0 = Mon, 1 = Tue, ..., 6 = Sun

      if (weekNum >= 1 && weekNum <= totalWeeks) {
        weeks[weekNum][dayIndex].push(s);
      }
    });

    // 3. Determine current week to expand by default
    const today = new Date();
    today.setHours(0,0,0,0);
    const diffTodayTime = today - planMonday;
    const diffTodayDays = Math.round(diffTodayTime / (1000 * 60 * 60 * 24));
    const currentWeekNum = Math.max(1, Math.min(totalWeeks, Math.floor(diffTodayDays / 7) + 1));

    if (!this.expandedWeeks || this._lastPlanId !== plan.id) {
      this._lastPlanId = plan.id;
      this.expandedWeeks = {};
      this.expandedWeeks[currentWeekNum] = true;
    }

    const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const fullDayNames = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"];

    let html = `
      <div style="margin-top: 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
          <h3 style="font-family: var(--font-display); font-size: 1.5rem; font-weight: 700;">Training Calendar</h3>
          <span style="font-size: 0.85rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.25rem;">
            <i data-lucide="info" style="width: 14px; height: 14px;"></i> Drag cards to rearrange training days
          </span>
        </div>
    `;

    // Render each week
    for (let w = 1; w <= totalWeeks; w++) {
      const isExpanded = !!this.expandedWeeks[w];
      
      // Calculate start and end date of this week
      const weekStartDate = new Date(planMonday);
      weekStartDate.setDate(planMonday.getDate() + (w - 1) * 7);
      
      const weekEndDate = new Date(weekStartDate);
      weekEndDate.setDate(weekStartDate.getDate() + 6);

      const formattedRange = `${weekStartDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} - ${weekEndDate.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`;

      // Calculate weekly planned mileage
      let weeklyMileage = 0;
      weeks[w].forEach(daySessions => {
        daySessions.forEach(s => {
          if (s.distance_miles) weeklyMileage += s.distance_miles;
        });
      });

      html += `
        <div class="calendar-week-container ${isExpanded ? 'expanded' : ''}" data-week="${w}">
          <div class="calendar-week-header" onclick="window.toggleCalendarWeek(${w})">
            <div style="display: flex; align-items: center; gap: 1rem;">
              <i data-lucide="chevron-right" class="chevron-icon" style="width: 20px; height: 20px; transition: var(--transition-smooth); transform: ${isExpanded ? 'rotate(90deg)' : 'rotate(0deg)'};"></i>
              <h4 style="font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; margin: 0;">Week ${w}</h4>
              <span style="font-size: 0.85rem; color: var(--text-secondary); background: rgba(255,255,255,0.06); padding: 0.2rem 0.6rem; border-radius: 20px;">
                ${formattedRange}
              </span>
            </div>
            <div style="display: flex; align-items: center; gap: 1.25rem;">
              <span style="font-size: 0.9rem; font-weight: 600; color: var(--accent-secondary);">
                ${window.formatDistance(weeklyMileage)} Planned
              </span>
              <button class="btn btn-secondary" onclick="window.triggerWeekAIRebalance(event, ${w})" style="font-size: 0.8rem; padding: 0.4rem 1rem; display: flex; align-items: center; gap: 0.25rem; border-radius: 20px; background: rgba(255,255,255,0.05); border: 1px solid var(--border-color); color: var(--text-primary);">
                <i data-lucide="sparkles" style="width: 14px; height: 14px; color: var(--accent-secondary);"></i> AI Rebalance Week
              </button>
            </div>
          </div>
          <div class="calendar-week-content">
            <div class="calendar-grid">
      `;

      // Render 7 days
      for (let d = 0; d < 7; d++) {
        const dayDate = new Date(weekStartDate);
        dayDate.setDate(weekStartDate.getDate() + d);
        const dayDateStr = window.formatLocalDate(dayDate);
        
        const isToday = dayDate.toDateString() === today.toDateString();
        const isUnavailable = unavailableDays.includes(fullDayNames[d]);

        html += `
          <div class="calendar-day-slot ${isUnavailable ? 'unavailable' : ''}" 
               data-date="${dayDateStr}" 
               ondragover="CalendarDragDrop.handleDragOver(event)" 
               ondragleave="CalendarDragDrop.handleDragLeave(event)" 
               ondrop="CalendarDragDrop.handleDrop(event)">
            <div class="calendar-day-label ${isToday ? 'today' : ''}">
              <span>${dayNames[d]}</span>
              <span>${dayDate.getDate()}</span>
            </div>
        `;

        // Render sessions in this day slot
        const daySessions = weeks[w][d];
        daySessions.forEach(s => {
          const typeClass = s.type.toLowerCase().replace(" ", "-");
          const distStr = s.distance_miles ? ` | ${window.formatDistance(s.distance_miles)}` : "";
          
          let statusBadge = "";
          if (s.status === "completed") {
            statusBadge = `
              <span class="workout-status-badge completed" style="background: rgba(16, 185, 129, 0.15); color: var(--color-easy); border: 1px solid rgba(16, 185, 129, 0.3); padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.2rem;">
                <i data-lucide="check" style="width: 10px; height: 10px;"></i> Completed
              </span>
            `;
          } else if (s.status === "skipped") {
            statusBadge = `
              <span class="workout-status-badge skipped" style="background: rgba(239, 68, 68, 0.1); color: var(--color-intervals); border: 1px solid rgba(239, 68, 68, 0.2); padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.2rem;">
                <i data-lucide="x" style="width: 10px; height: 10px;"></i> Skipped
              </span>
            `;
          }

          html += `
            <div class="workout-card" 
                 id="card-${s.id}" 
                 draggable="true" 
                 ondragstart="CalendarDragDrop.handleDragStart(event)" 
                 ondragend="CalendarDragDrop.handleDragEnd(event)" 
                 onclick="window.location.hash='#session/${s.id}'">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <span class="workout-tag ${typeClass}">${s.type}</span>
                ${statusBadge}
              </div>
              <div style="font-weight: 700; font-size: 0.9rem; color: var(--text-primary); line-height: 1.2;">
                ${s.name}
              </div>
              <div style="font-size: 0.75rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.25rem;">
                <i data-lucide="clock" style="width: 12px; height: 12px;"></i>
                ${s.duration_minutes}m${distStr}
              </div>
            </div>
          `;
        });

        html += `
          </div>
        `;
      }

      const weeklyCommentary = evaluationsByWeek[w] || "";

      html += `
            </div>
            ${weeklyCommentary ? `
              <div class="weekly-commentary-box" style="margin-top: 1.5rem; padding: 1.25rem; border-radius: var(--radius-md); background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.15); display: flex; flex-direction: column; gap: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--accent-secondary); font-weight: 700; font-size: 0.95rem;">
                  <i data-lucide="sparkles" style="width: 16px; height: 16px; color: var(--accent-secondary);"></i>
                  <span>Coach's Weekly Feedback</span>
                </div>
                <p style="font-size: 0.9rem; color: var(--text-primary); line-height: 1.5; margin: 0; font-style: italic;">
                  "${weeklyCommentary}"
                </p>
              </div>
            ` : ""}
          </div>
        </div>
      `;
    }

    html += `
      </div>
    `;

    // Global helper for toggling weeks
    window.toggleCalendarWeek = (weekNum) => {
      const container = document.querySelector(`.calendar-week-container[data-week="${weekNum}"]`);
      if (container) {
        const isExpanded = container.classList.contains("expanded");
        const chevron = container.querySelector(".chevron-icon");
        
        if (isExpanded) {
          container.classList.remove("expanded");
          if (chevron) chevron.style.transform = "rotate(0deg)";
          this.expandedWeeks[weekNum] = false;
        } else {
          container.classList.add("expanded");
          if (chevron) chevron.style.transform = "rotate(90deg)";
          this.expandedWeeks[weekNum] = true;
        }
      }
    };

    // Global helper for triggering week rebalance
    window.triggerWeekAIRebalance = async (event, weekNum) => {
      if (event) event.stopPropagation();
      try {
        const activePlan = await api.getActivePlan();
        if (activePlan && activePlan.plan) {
          window.RebalanceDialog.show(activePlan.plan.id, "", weekNum);
        }
      } catch (err) {
        window.showToast("Failed to fetch plan context", "error");
      }
    };

    return html;
  }
};
