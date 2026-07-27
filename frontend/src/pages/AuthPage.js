import { api } from "../services/api.js";

export const AuthPage = {
  render(isRegister = false) {
    return `
      <div style="width: 100%; max-width: 440px; display: flex; flex-direction: column; align-items: center; gap: 2rem; padding: 2rem;" class="fade-in">

        <!-- Logo -->
        <div style="display: flex; flex-direction: column; align-items: center; gap: 0.75rem;">
          <div style="background: var(--gradient-premium); width: 56px; height: 56px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-family: var(--font-display); font-size: 1.6rem; box-shadow: 0 0 32px rgba(99,102,241,0.4);">
            A
          </div>
          <span style="font-family: var(--font-display); font-weight: 800; font-size: 1.8rem; background: var(--gradient-premium); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            AuraRun
          </span>
          <p style="color: var(--text-secondary); font-size: 0.9rem; text-align: center; margin: 0;">
            ${isRegister ? "Create your account to start training smarter." : "Your AI running coach is waiting."}
          </p>
        </div>

        <!-- Auth Card -->
        <div style="width: 100%; background: rgba(15, 23, 42, 0.6); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 2.25rem; backdrop-filter: blur(16px); box-shadow: var(--shadow-lg);">
          <h2 style="font-family: var(--font-display); font-size: 1.5rem; margin-bottom: 1.75rem; text-align: center; font-weight: 700;">
            ${isRegister ? "Create Account" : "Sign In"}
          </h2>

          <form id="auth-form" style="display: flex; flex-direction: column; gap: 1.25rem;">
            ${isRegister ? `
              <div style="display: flex; flex-direction: column; gap: 0.5rem;">
                <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.03em;">Full Name</label>
                <input type="text" id="reg-name" required placeholder="Jane Doe"
                  style="padding: 0.8rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.5); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth); width: 100%; box-sizing: border-box;"
                  onfocus="this.style.borderColor='var(--accent-primary)'" onblur="this.style.borderColor='var(--border-color)'">
              </div>
            ` : ""}

            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.03em;">Email Address</label>
              <input type="email" id="auth-email" required placeholder="jane@example.com"
                style="padding: 0.8rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.5); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth); width: 100%; box-sizing: border-box;"
                onfocus="this.style.borderColor='var(--accent-primary)'" onblur="this.style.borderColor='var(--border-color)'">
            </div>

            <div style="display: flex; flex-direction: column; gap: 0.5rem;">
              <label style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary); letter-spacing: 0.03em;">Password</label>
              <input type="password" id="auth-password" required placeholder="••••••••"
                style="padding: 0.8rem 1rem; border-radius: var(--radius-sm); border: 1px solid var(--border-color); background: rgba(15, 23, 42, 0.5); color: white; outline: none; font-size: 1rem; transition: var(--transition-smooth); width: 100%; box-sizing: border-box;"
                onfocus="this.style.borderColor='var(--accent-primary)'" onblur="this.style.borderColor='var(--border-color)'">
            </div>

            <button type="submit" class="btn btn-primary" style="justify-content: center; margin-top: 0.5rem; font-size: 1.05rem; padding: 0.85rem;">
              ${isRegister ? "Create Account" : "Sign In"}
            </button>
          </form>

          <p style="text-align: center; margin-top: 1.5rem; font-size: 0.9rem; color: var(--text-secondary);">
            ${isRegister
              ? `Already have an account? <a href="#login" style="color: var(--accent-secondary); text-decoration: none; font-weight: 600;">Sign In</a>`
              : `New to AuraRun? <a href="#register" style="color: var(--accent-secondary); text-decoration: none; font-weight: 600;">Create an account</a>`}
          </p>
        </div>
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

      const btn = form.querySelector("button[type=submit]");
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = "Please wait…";

      try {
        if (isRegister) {
          const name = document.getElementById("reg-name").value;
          await api.register(name, email, password);
          await api.login(email, password);
          window.showToast("Account created successfully!");
          navigateTo("#onboarding");
        } else {
          await api.login(email, password);
          window.showToast("Logged in successfully!");
          navigateTo("#current-plan");
        }
      } catch (err) {
        window.showToast(err.message || "Something went wrong. Please try again.", "error");
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  }
};
