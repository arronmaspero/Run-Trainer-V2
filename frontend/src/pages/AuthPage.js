import { api } from "../services/api.js";

export const AuthPage = {
  render(isRegister = false) {
    return `
      <div style="max-width: 480px; margin: 4rem auto; padding: 2.5rem;" class="card glass-panel fade-in">
        <h2 style="font-family: var(--font-display); font-size: 2rem; margin-bottom: 0.5rem; text-align: center;">
          ${isRegister ? "Start Your Journey" : "Welcome Back"}
        </h2>
        <p style="color: var(--text-secondary); text-align: center; margin-bottom: 2rem; font-size: 0.95rem;">
          ${isRegister ? "Join AuraRun to build your lovable AI running plan" : "Log in to sync your runs and track your calendar"}
        </p>

        <form id="auth-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
          ${isRegister ? `
            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Full Name</label>
              <input type="text" id="reg-name" required placeholder="Jane Doe" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth);">
            </div>
          ` : ""}

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Email Address</label>
            <input type="email" id="auth-email" required placeholder="jane@example.com" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth);">
          </div>

          <div style="display: flex; flex-direction: column; gap: 0.5rem;">
            <label style="font-size: 0.9rem; font-weight: 500; color: var(--text-secondary);">Password</label>
            <input type="password" id="auth-password" required placeholder="••••••••" style="padding: 0.75rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.4); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth);">
          </div>

          <button type="submit" class="btn btn-primary" style="justify-content: center; margin-top: 1rem; font-size: 1.05rem;">
            ${isRegister ? "Create Account" : "Sign In"}
          </button>
        </form>

        <p style="text-align: center; margin-top: 1.5rem; font-size: 0.9rem; color: var(--text-secondary);">
          ${isRegister 
            ? `Already have an account? <a href="#login" style="color: var(--accent-secondary); text-decoration: none; font-weight: 600;">Sign In</a>` 
            : `New to AuraRun? <a href="#register" style="color: var(--accent-secondary); text-decoration: none; font-weight: 600;">Sign Up</a>`}
        </p>
      </div>
    `;
  },

  init(isRegister = false, navigateTo) {
    const form = document.getElementById("auth-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = document.getElementById("auth-email").value;
      const password = document.getElementById("auth-password").value;
      
      try {
        if (isRegister) {
          const name = document.getElementById("reg-name").value;
          await api.register(name, email, password);
          // Auto login after registration
          await api.login(email, password);
          window.showToast("Account created successfully!");
          navigateTo("#onboarding");
        } else {
          await api.login(email, password);
          window.showToast("Logged in successfully!");
          navigateTo("#current-plan");
        }
      } catch (err) {
        window.showToast(err.message, "error");
      }
    });
  }
};
