"""
AI Incident Management - Main Streamlit Application Entry Point.
Handles login, registration, routing, input guardrails, and voice support.
"""
import sys
import re
from pathlib import Path

# Ensure the project root is in path so `backend` and `frontend` packages resolve
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.sidebar import render_user_sidebar, render_admin_sidebar

st.set_page_config(
    page_title="AI Incident Management",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────
# Guardrails helpers
# ─────────────────────────────────────────────
_BLOCKED_PATTERNS = [
    r"(?i)(ignore|forget|disregard)\s+(previous|all|prior|above)\s+(instructions?|prompts?|rules?)",
    r"(?i)jailbreak",
    r"(?i)act\s+as\s+(a\s+)?(different|evil|unrestricted|dan)\s+",
    r"(?i)you\s+are\s+now\s+(a\s+)?(different|evil|unrestricted)",
    r"(?i)(drop|delete|truncate)\s+table",
    r"(?i)<\s*script",
    r"(?i)prompt\s*injection",
    r"(?i)system\s*prompt",
]

_PROFANITY_PATTERN = r"(?i)\b(fuck|shit|bitch|asshole|bastard|cunt|dick|piss)\b"


def validate_input(text: str) -> tuple[bool, str]:
    """
    Guardrails validation for user inputs.
    Returns (is_valid, error_message).
    """
    if not text or not text.strip():
        return False, "Input cannot be empty."

    stripped = text.strip()

    if len(stripped) < 3:
        return False, "Input is too short. Please provide more detail."

    if len(stripped) > 5000:
        return False, "Input is too long (max 5000 characters)."

    # Prompt injection / jailbreak detection
    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, stripped):
            return False, "⚠️ Input contains disallowed content and cannot be processed."

    # Profanity check (soft warning, still allow)
    if re.search(_PROFANITY_PATTERN, stripped):
        return False, "⚠️ Please keep your language professional. Profanity is not allowed."

    return True, ""


def validate_username(username: str) -> tuple[bool, str]:
    if not username or len(username.strip()) < 3:
        return False, "Username must be at least 3 characters."
    if len(username) > 64:
        return False, "Username must be less than 64 characters."
    if not re.match(r"^[a-zA-Z0-9_\-\.@]+$", username):
        return False, "Username can only contain letters, numbers, underscores, hyphens, dots, and @."
    return True, ""


def validate_email(email: str) -> tuple[bool, str]:
    if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        return False, "Please enter a valid email address."
    if len(email) > 255:
        return False, "Email address is too long."
    return True, ""


def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password is too long (max 128 characters)."
    return True, ""


# ─────────────────────────────────────────────
# Voice HTML component (Web Speech API — no server dependency)
# ─────────────────────────────────────────────
VOICE_WIDGET_HTML = """
<style>
.voice-container {
    display:flex; align-items:center; gap:10px;
    background:#f7f8fa; border:1px solid #e5e7eb;
    border-radius:8px; padding:10px 14px; margin:8px 0;
}
.voice-btn {
    background:#3b82d4; color:#fff; border:none;
    border-radius:6px; padding:6px 14px; cursor:pointer;
    font-size:13px; display:flex; align-items:center; gap:6px;
}
.voice-btn:hover { background:#2563b0; }
.voice-btn.recording { background:#ef4444; animation:pulse 1s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.6} }
.voice-status { font-size:12px; color:#57606a; }
#voice-transcript { font-size:13px; color:#1f2328; min-height:18px; }
.tts-btn {
    background:#7c5cd8; color:#fff; border:none;
    border-radius:6px; padding:6px 12px; cursor:pointer; font-size:12px;
}
.tts-btn:hover { background:#6d44c9; }
</style>

<div class="voice-container" id="voiceWidget">
    <button class="voice-btn" id="micBtn" onclick="toggleMic()">
        🎤 Speak
    </button>
    <div>
        <div class="voice-status" id="voiceStatus">Click 🎤 to speak your issue in any language</div>
        <div id="voice-transcript"></div>
    </div>
</div>

<script>
var recognition = null;
var isRecording = false;

function supportsRecognition() {
    return ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window);
}

function toggleMic() {
    if (!supportsRecognition()) {
        document.getElementById('voiceStatus').textContent = '⚠️ Voice not supported in this browser. Use Chrome.';
        return;
    }
    if (isRecording) {
        stopMic();
    } else {
        startMic();
    }
}

function startMic() {
    var SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'en-US';  // use browser locale

    recognition.onstart = function() {
        isRecording = true;
        document.getElementById('micBtn').classList.add('recording');
        document.getElementById('micBtn').innerHTML = '⏹ Stop';
        document.getElementById('voiceStatus').textContent = '🔴 Recording... speak now';
    };

    recognition.onresult = function(event) {
        var transcript = '';
        for (var i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        document.getElementById('voice-transcript').textContent = transcript;

        if (event.results[event.results.length-1].isFinal) {
            // Send to Streamlit via component value
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: transcript
            }, '*');

            // Also copy to clipboard so user can paste
            if (navigator.clipboard) {
                navigator.clipboard.writeText(transcript).catch(function(){});
            }
            document.getElementById('voiceStatus').textContent = '✅ Transcribed! Paste into the text box below.';
            stopMic();
        }
    };

    recognition.onerror = function(event) {
        document.getElementById('voiceStatus').textContent = '❌ Error: ' + event.error;
        stopMic();
    };

    recognition.onend = function() { stopMic(); };
    recognition.start();
}

function stopMic() {
    isRecording = false;
    if (recognition) { try { recognition.stop(); } catch(e){} }
    document.getElementById('micBtn').classList.remove('recording');
    document.getElementById('micBtn').innerHTML = '🎤 Speak';
}

// TTS function – called by speak buttons generated for AI messages
function speakText(text, lang) {
    if (!('speechSynthesis' in window)) {
        alert('Text-to-speech not supported in your browser.');
        return;
    }
    window.speechSynthesis.cancel();
    var utter = new SpeechSynthesisUtterance(text);
    if (lang) { utter.lang = lang; }
    utter.rate = 0.95;
    utter.pitch = 1.0;
    window.speechSynthesis.speak(utter);
}
</script>
"""

TTS_BUTTON_HTML = """
<button class="tts-btn" onclick="speakText(`{text}`, `{lang}`)">🔊 Listen</button>
<style>.tts-btn{{background:#7c5cd8;color:#fff;border:none;border-radius:6px;padding:4px 10px;cursor:pointer;font-size:12px;margin-left:6px;}}.tts-btn:hover{{background:#6d44c9;}}</style>
"""

# ─────────────────────────────────────────────
# Language detection helper (lightweight)
# ─────────────────────────────────────────────
def detect_language_tag(text: str) -> str:
    """Return a BCP-47 lang tag via a cheap heuristic / Unicode block check."""
    # Check for common non-Latin scripts
    if re.search(r"[\u0600-\u06FF]", text):   return "ar"   # Arabic
    if re.search(r"[\u4E00-\u9FFF]", text):   return "zh"   # Chinese
    if re.search(r"[\u3040-\u30FF]", text):   return "ja"   # Japanese
    if re.search(r"[\uAC00-\uD7AF]", text):   return "ko"   # Korean
    if re.search(r"[\u0900-\u097F]", text):   return "hi"   # Hindi / Devanagari
    if re.search(r"[\u0400-\u04FF]", text):   return "ru"   # Cyrillic
    # Very rough Latin language detection by common stop words
    lower = text.lower()
    if any(w in lower for w in [" es ", " la ", " el ", " de ", " que ", " en "]):
        return "es"
    if any(w in lower for w in [" le ", " la ", " les ", " une ", " est "]):
        return "fr"
    if any(w in lower for w in [" der ", " die ", " das ", " und ", " ist "]):
        return "de"
    if any(w in lower for w in [" il ", " la ", " che ", " di ", " un "]):
        return "it"
    if any(w in lower for w in [" o ", " a ", " os ", " as ", " um ", " uma "]):
        return "pt"
    return "en"


# ─────────────────────────────────────────────
# Login / Register Screen
# ─────────────────────────────────────────────
def _render_login() -> None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align:center;padding:24px 0 16px;'>
                <h1 style='font-size:32px;font-weight:700;'>🤖 AI Incident Management</h1>
                <p style='color:#57606a;font-size:16px;'>Enterprise IT Troubleshooting Platform</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

        # ── LOGIN ──────────────────────────────────────
        with tab1:
            with st.form("login_form"):
                username = st.text_input(
                    "Username or Email",
                    placeholder="your-username or you@company.com",
                    max_chars=255,
                )
                password = st.text_input(
                    "Password",
                    type="password",
                    placeholder="••••••••",
                    max_chars=128,
                )
                submit = st.form_submit_button(
                    "Login", use_container_width=True, type="primary"
                )

            if submit:
                # Guardrails: basic field validation
                if not username.strip() or not password:
                    st.error("⚠️ Please enter both username/email and password.")
                elif len(username.strip()) < 3:
                    st.error("⚠️ Username must be at least 3 characters.")
                else:
                    backend_ok = api.check_backend()
                    if not backend_ok:
                        st.error(
                            "❌ Backend is offline. Please start the backend server:\n"
                            "```\nuvicorn backend.api.main:app --reload\n```"
                        )
                    else:
                        with st.spinner("Authenticating..."):
                            result = api.login(username.strip(), password)

                        if result["status_code"] == 200:
                            data = result["data"]
                            auth_utils.set_auth(
                                token=data["access_token"],
                                user={
                                    "id": data["user_id"],
                                    "username": data["username"],
                                    "role": data["role"],
                                },
                            )
                            if data["role"] == "admin":
                                session_utils.navigate("admin_dashboard")
                            else:
                                session_utils.navigate("user_dashboard")
                            st.rerun()

                        elif result["status_code"] == 404:
                            st.warning(
                                "⚠️ No account found for this username or email. "
                                "**Please register first** using the Register tab above."
                            )
                        elif result["status_code"] == 401:
                            st.error(
                                "❌ Incorrect password. Please try again."
                            )
                        elif result["status_code"] == 403:
                            st.error("🚫 Your account is disabled. Please contact an administrator.")
                        else:
                            error_msg = result["data"].get("detail", "Login failed. Please try again.")
                            st.error(f"❌ {error_msg}")

        # ── REGISTER ───────────────────────────────────
        with tab2:
            with st.form("register_form"):
                reg_username = st.text_input(
                    "Username",
                    placeholder="your-username (min 3 chars)",
                    max_chars=64,
                    key="reg_user",
                )
                reg_email = st.text_input(
                    "Email",
                    placeholder="you@company.com",
                    max_chars=255,
                    key="reg_email",
                )
                reg_password = st.text_input(
                    "Password (min 8 characters)",
                    type="password",
                    max_chars=128,
                    key="reg_pass",
                )
                reg_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    max_chars=128,
                    key="reg_confirm",
                )
                reg_submit = st.form_submit_button(
                    "Register", use_container_width=True, type="primary"
                )

            if reg_submit:
                # Run all guardrail validators
                errors = []

                u_ok, u_err = validate_username(reg_username)
                if not u_ok:
                    errors.append(u_err)

                e_ok, e_err = validate_email(reg_email)
                if not e_ok:
                    errors.append(e_err)

                p_ok, p_err = validate_password(reg_password)
                if not p_ok:
                    errors.append(p_err)

                if reg_password and reg_confirm and reg_password != reg_confirm:
                    errors.append("Passwords do not match.")

                if errors:
                    for err in errors:
                        st.error(f"⚠️ {err}")
                else:
                    with st.spinner("Creating account..."):
                        result = api.register(reg_username.strip(), reg_email.strip(), reg_password)
                    if result["status_code"] == 201:
                        st.success("✅ Account created successfully! You can now login.")
                    elif result["status_code"] == 400:
                        detail = result["data"].get("detail", "Registration failed")
                        if "username" in detail.lower():
                            st.error("❌ That username is already taken. Please choose a different one.")
                        elif "email" in detail.lower():
                            st.error("❌ That email is already registered. Please use a different email or login.")
                        else:
                            st.error(f"❌ {detail}")
                    else:
                        error_msg = result["data"].get("detail", "Registration failed. Please try again.")
                        st.error(f"❌ {error_msg}")

        # Backend status indicator
        st.markdown("---")
        backend_ok = api.check_backend()
        if backend_ok:
            st.success("✅ Backend Online")
        else:
            st.error(
                "❌ Backend Offline — run: `uvicorn backend.api.main:app --reload`"
            )


# ─────────────────────────────────────────────
# Main Router
# ─────────────────────────────────────────────
def main() -> None:
    current_page = session_utils.get_current_page()

    # Not authenticated → login
    if not auth_utils.is_authenticated():
        _render_login()
        return

    role = auth_utils.get_role()

    # ── USER interface ────────────────────────────────────────
    if role == "user":
        incidents = api.get_incident_history(auth_utils.get_token())
        render_user_sidebar(incidents)

        user_pages = {
            "user_dashboard": _import_page("user_dashboard"),
            "new_incident": _import_page("new_incident"),
            "incident_history": _import_page("incident_history"),
            "incident_details": _import_page("incident_details"),
        }

        page_key = current_page if current_page in user_pages else "user_dashboard"
        user_pages[page_key].render()

    # ── ADMIN interface ──────────────────────────────────────
    elif role == "admin":
        render_admin_sidebar()

        admin_pages = {
            "admin_dashboard": _import_page("admin_dashboard"),
            "human_handoffs": _import_page("human_handoffs"),
            "all_incidents": _import_page("all_incidents"),
            "admin_incident_detail": _import_page("admin_incident_detail"),
            "analytics": _import_page("analytics"),
            "evaluation": _import_page("evaluation"),
            "users": _import_page("users"),
            "system": _import_page("system"),
        }

        page_key = current_page if current_page in admin_pages else "admin_dashboard"
        admin_pages[page_key].render()
    else:
        auth_utils.clear_auth()
        st.rerun()


def _import_page(name: str):
    import importlib
    return importlib.import_module(f"frontend.page_modules.{name}")


if __name__ == "__main__":
    main()
