import { api } from "../services/api.js";

export const AICoachChatDialog = {
  messages: [],
  isSending: false,
  isApplying: false,

  async show() {
    let root = document.getElementById("ai-coach-chat-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "ai-coach-chat-root";
      root.className = "modal-overlay";
      document.body.appendChild(root);
    }

    root.classList.add("active");
    this.renderLoading(root);

    try {
      const res = await api.getChatHistory();
      this.messages = res.messages || [];
      this.renderDialog(root);
    } catch (err) {
      window.showToast("Failed to load chat history", "error");
      this.hide();
    }
  },

  renderLoading(root) {
    root.innerHTML = `
      <div class="modal-container" style="max-width: 600px; height: 80vh; display: flex; flex-direction: column;">
        <div class="modal-header">
          <h3 style="font-family: var(--font-display); font-size: 1.35rem; font-weight: 700; display: flex; align-items: center; gap: 0.5rem;">
            <i data-lucide="sparkles" style="color: var(--accent-secondary); width: 24px; height: 24px;"></i>
            AI Coach Assistant
          </h3>
          <button onclick="AICoachChatDialog.hide()" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer;">
            <i data-lucide="x" style="width: 20px; height: 20px;"></i>
          </button>
        </div>
        <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;">
          <div style="width: 40px; height: 40px; border: 3px solid var(--border-color); border-top: 3px solid var(--accent-primary); border-radius: 50%; animation: spin 1s linear infinite; margin-bottom: 1rem;"></div>
          <p style="color: var(--text-secondary);">Connecting to your AI Coach...</p>
        </div>
      </div>
    `;
    lucide.createIcons();
  },

  renderDialog(root) {
    const renderMessagesHtml = () => {
      if (this.messages.length === 0) {
        return `
          <div style="text-align: center; padding: 2.5rem 1rem; color: var(--text-muted);">
            <div style="width: 50px; height: 50px; background: rgba(99,102,241,0.1); border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; color: var(--accent-secondary);">
              <i data-lucide="bot" style="width: 28px; height: 28px;"></i>
            </div>
            <h4 style="font-size: 1.1rem; color: var(--text-primary); margin-bottom: 0.5rem;">Chat with your AI Coach</h4>
            <p style="font-size: 0.9rem; max-width: 400px; margin: 0 auto 1.5rem; line-height: 1.5;">
              Ask questions about your plan, request schedule adjustments, or discuss fatigue and goals. I have full context of your workouts and profile!
            </p>
          </div>
        `;
      }

      return this.messages.map(m => {
        const isUser = m.sender === "user";
        return `
          <div style="display: flex; flex-direction: column; align-items: ${isUser ? 'flex-end' : 'flex-start'}; margin-bottom: 1.25rem;">
            <div style="font-size: 0.75rem; color: var(--text-muted); margin-bottom: 0.35rem; font-weight: 600;">
              ${isUser ? 'You' : 'AI Coach'}
            </div>
            <div style="
              max-width: 85%;
              padding: 0.9rem 1.1rem;
              border-radius: ${isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px'};
              background: ${isUser ? 'var(--gradient-premium)' : 'rgba(30, 41, 59, 0.7)'};
              color: white;
              border: ${isUser ? 'none' : '1px solid var(--border-color)'};
              box-shadow: var(--shadow-sm);
              font-size: 0.95rem;
              line-height: 1.55;
              white-space: pre-wrap;
            ">${m.text}</div>
            
            ${(!isUser && m.has_proposed_changes) ? `
              <div style="margin-top: 0.75rem; background: rgba(99,102,241,0.12); border: 1px solid rgba(99,102,241,0.3); border-radius: 12px; padding: 1rem; max-width: 85%; width: 100%;">
                <div style="display: flex; align-items: center; gap: 0.5rem; color: var(--accent-secondary); font-weight: 700; font-size: 0.9rem; margin-bottom: 0.5rem;">
                  <i data-lucide="sparkles" style="width: 16px; height: 16px;"></i> Ready to update your plan?
                </div>
                <p style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.75rem; line-height: 1.4;">
                  Click below to update your future calendar sessions based on this conversation.
                </p>
                <button class="btn btn-primary" onclick="AICoachChatDialog.applyAgreedChanges()" style="font-size: 0.85rem; padding: 0.5rem 1rem; width: 100%; justify-content: center; background: var(--gradient-premium);">
                  Apply Agreed Plan Changes <i data-lucide="check"></i>
                </button>
              </div>
            ` : ""}
          </div>
        `;
      }).join("");
    };

    root.innerHTML = `
      <div class="modal-container" style="max-width: 640px; height: 85vh; display: flex; flex-direction: column; padding: 0; overflow: hidden;">
        
        <!-- Header -->
        <div class="modal-header" style="padding: 1.25rem 1.5rem; border-bottom: 1px solid var(--border-color); background: rgba(15,23,42,0.8);">
          <div style="display: flex; align-items: center; gap: 0.75rem;">
            <div style="width: 36px; height: 36px; background: var(--gradient-premium); border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white;">
              <i data-lucide="sparkles" style="width: 20px; height: 20px;"></i>
            </div>
            <div>
              <h3 style="font-family: var(--font-display); font-size: 1.2rem; font-weight: 700; margin: 0;">AI Coach Conversation</h3>
              <span style="font-size: 0.75rem; color: var(--text-secondary);">Informed by your profile, Garmin/Strava, and plan history</span>
            </div>
          </div>
          <button onclick="AICoachChatDialog.hide()" style="background: transparent; border: none; color: var(--text-muted); cursor: pointer;">
            <i data-lucide="x" style="width: 20px; height: 20px;"></i>
          </button>
        </div>

        <!-- Chat Stream Body -->
        <div id="ai-chat-stream" style="flex: 1; overflow-y: auto; padding: 1.5rem; background: rgba(15,23,42,0.4);">
          ${renderMessagesHtml()}
        </div>

        <!-- Quick Suggestion Chips -->
        <div style="padding: 0.75rem 1.5rem 0.25rem; display: flex; gap: 0.5rem; overflow-x: auto; background: rgba(15,23,42,0.6); border-top: 1px solid rgba(255,255,255,0.05);">
          <button onclick="AICoachChatDialog.sendPreset('I am feeling tired. Can we lighten my Thursday runs?')" style="white-space: nowrap; font-size: 0.8rem; padding: 0.35rem 0.75rem; background: rgba(255,255,255,0.06); border: 1px solid var(--border-color); border-radius: 20px; color: var(--text-secondary); cursor: pointer;">
            ⚡ Lighten Thursdays
          </button>
          <button onclick="AICoachChatDialog.sendPreset('Shift my long runs to Saturday')" style="white-space: nowrap; font-size: 0.8rem; padding: 0.35rem 0.75rem; background: rgba(255,255,255,0.06); border: 1px solid var(--border-color); border-radius: 20px; color: var(--text-secondary); cursor: pointer;">
            📅 Saturday Long Runs
          </button>
          <button onclick="AICoachChatDialog.sendPreset('Add more 10K speedwork intervals')" style="white-space: nowrap; font-size: 0.8rem; padding: 0.35rem 0.75rem; background: rgba(255,255,255,0.06); border: 1px solid var(--border-color); border-radius: 20px; color: var(--text-secondary); cursor: pointer;">
            🏃 Focus on 10K Pace
          </button>
        </div>

        <!-- Input Bar -->
        <div style="padding: 1.25rem 1.5rem; background: rgba(15,23,42,0.8); border-top: 1px solid var(--border-color);">
          <form id="ai-chat-form" style="display: flex; gap: 0.75rem; align-items: center;">
            <input type="text" id="ai-chat-input" placeholder="Type your message or request to your AI Coach..." 
              style="flex: 1; padding: 0.85rem 1.1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15,23,42,0.6); color: white; outline: none; font-size: 0.95rem;"
              ${this.isSending ? 'disabled' : ''}>
            <button type="submit" class="btn btn-primary" style="padding: 0.85rem 1.25rem; font-size: 0.95rem; justify-content: center;" ${this.isSending ? 'disabled' : ''}>
              ${this.isSending ? '<span style="width: 16px; height: 16px; border: 2px solid white; border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite; display: inline-block;"></span>' : '<i data-lucide="send" style="width: 18px; height: 18px;"></i>'}
            </button>
          </form>
        </div>

      </div>
    `;

    lucide.createIcons();
    this.scrollToBottom();
    this.bindForm();
  },

  scrollToBottom() {
    const stream = document.getElementById("ai-chat-stream");
    if (stream) {
      stream.scrollTop = stream.scrollHeight;
    }
  },

  bindForm() {
    const form = document.getElementById("ai-chat-form");
    if (!form) return;

    form.onsubmit = async (e) => {
      e.preventDefault();
      const input = document.getElementById("ai-chat-input");
      if (!input || !input.value.trim() || this.isSending) return;

      const text = input.value.trim();
      input.value = "";
      await this.sendMessage(text);
    };
  },

  async sendPreset(text) {
    if (this.isSending) return;
    await this.sendMessage(text);
  },

  async sendMessage(text) {
    this.isSending = true;

    // Optimistically add user message to list
    this.messages.push({
      sender: "user",
      text: text,
      timestamp: new Date().toISOString(),
      has_proposed_changes: false
    });

    const root = document.getElementById("ai-coach-chat-root");
    if (root) this.renderDialog(root);

    try {
      const res = await api.sendChatMessage(text);
      if (res.reply) {
        this.messages.push(res.reply);
      }
    } catch (err) {
      window.showToast(err.message || "Failed to get response from AI Coach", "error");
    } finally {
      this.isSending = false;
      if (root) this.renderDialog(root);
    }
  },

  async applyAgreedChanges() {
    if (this.isApplying) return;
    this.isApplying = true;

    const root = document.getElementById("ai-coach-chat-root");
    if (root) {
      const stream = document.getElementById("ai-chat-stream");
      if (stream) {
        stream.innerHTML += `
          <div style="background: rgba(99,102,241,0.2); padding: 1rem; border-radius: 8px; text-align: center; margin: 1rem 0; color: var(--accent-secondary); font-weight: 600;">
            <span style="width: 16px; height: 16px; border: 2px solid var(--accent-secondary); border-top: 2px solid transparent; border-radius: 50%; animation: spin 1s linear infinite; display: inline-block; margin-right: 0.5rem;"></span>
            Updating your training plan based on conversation...
          </div>
        `;
        this.scrollToBottom();
      }
    }

    try {
      await api.applyChatPlanChanges();
      window.showToast("Training plan updated based on your conversation!", "success");
      this.hide();

      // Refresh calendar page view
      if (window.refreshCurrentPlanView) {
        await window.refreshCurrentPlanView();
      }
    } catch (err) {
      window.showToast(err.message || "Failed to apply plan changes", "error");
    } finally {
      this.isApplying = false;
    }
  },

  hide() {
    const root = document.getElementById("ai-coach-chat-root");
    if (root) {
      root.classList.remove("active");
    }
  }
};

window.AICoachChatDialog = AICoachChatDialog;
