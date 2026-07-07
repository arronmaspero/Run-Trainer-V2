import { api } from "../services/api.js";
import { RebalanceDialog } from "./RebalanceDialog.js";

export const CalendarDragDrop = {
  draggedCard: null,
  originalParent: null,

  handleDragStart(event) {
    this.draggedCard = event.currentTarget;
    this.originalParent = this.draggedCard.parentElement;
    
    // Add dragging styling class
    this.draggedCard.classList.add("dragging");
    event.dataTransfer.setData("text/plain", this.draggedCard.id);
    event.dataTransfer.effectAllowed = "move";
  },

  handleDragEnd(event) {
    if (this.draggedCard) {
      this.draggedCard.classList.remove("dragging");
    }
  },

  handleDragOver(event) {
    event.preventDefault();
    const slot = event.currentTarget.closest(".calendar-day-slot");
    if (slot) {
      slot.classList.add("drag-over");
    }
  },

  handleDragLeave(event) {
    const slot = event.currentTarget.closest(".calendar-day-slot");
    if (slot) {
      slot.classList.remove("drag-over");
    }
  },

  async handleDrop(event) {
    event.preventDefault();
    
    const slot = event.currentTarget.closest(".calendar-day-slot");
    if (!slot || !this.draggedCard) return;

    slot.classList.remove("drag-over");

    const newDate = slot.getAttribute("data-date");
    const cardId = event.dataTransfer.getData("text/plain");
    const sessionId = cardId.replace("card-", "");

    // Check if there is an existing workout card in the target slot
    const targetCard = slot.querySelector(".workout-card");
    const hadTargetCard = !!targetCard;

    // 1. Optimistic Update: swap the elements in the DOM immediately
    if (hadTargetCard) {
      this.originalParent.appendChild(targetCard);
    }
    slot.appendChild(this.draggedCard);

    try {
      // 2. Call backend move API — optimistic swap already updated the DOM
      await api.moveSession(sessionId, newDate);

      // Don't re-render the full calendar — it would wipe out the visual swap.
      // Just quietly update data state and stats in the background.
      if (window.refreshCurrentPlanDataOnly) window.refreshCurrentPlanDataOnly();
      window.showToast("Workout rescheduled successfully!");
    } catch (err) {
      // 3. Rollback: swap the cards back to their original slots
      if (hadTargetCard) {
        slot.appendChild(targetCard);
      }
      if (this.originalParent) {
        this.originalParent.appendChild(this.draggedCard);
      }
      window.showToast(err.message || "Failed to reschedule session", "error");
    } finally {
      this.draggedCard = null;
      this.originalParent = null;
    }
  }
};

// Bind to window to allow inline element calls
window.CalendarDragDrop = CalendarDragDrop;
