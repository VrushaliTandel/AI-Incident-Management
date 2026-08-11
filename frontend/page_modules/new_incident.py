"""
New Incident page — voice input, English + Indian languages only.

Changes from previous version:
  - TTS "Listen" button REMOVED from AI responses (was reading English letters only)
  - Language list reduced to English + 11 Indian languages
  - Voice widget uses the selected BCP-47 tag for Chrome Speech API
"""
import re
import streamlit as st
from frontend.utils import api, auth as auth_utils, session as session_utils
from frontend.components.chat import render_verification_buttons


# ──────────────────────────────────────────────────────
# Languages: English + Indian only
# ──────────────────────────────────────────────────────
_LANGUAGES = [
    ("English",              "en-US"),
    ("Hindi / हिन्दी",        "hi-IN"),
    ("Tamil / தமிழ்",         "ta-IN"),
    ("Telugu / తెలుగు",       "te-IN"),
    ("Kannada / ಕನ್ನಡ",       "kn-IN"),
    ("Malayalam / മലയാളം",    "ml-IN"),
    ("Bengali / বাংলা",       "bn-IN"),
    ("Gujarati / ગુજરાતી",    "gu-IN"),
    ("Marathi / मराठी",       "mr-IN"),
    ("Punjabi / ਪੰਜਾਬੀ",      "pa-IN"),
    ("Odia / ଓଡ଼ିଆ",          "or-IN"),
    ("Urdu / اردو",           "ur-IN"),
]

_LANG_LABELS = [l[0] for l in _LANGUAGES]
_LANG_TAGS   = [l[1] for l in _LANGUAGES]


def _label_for_tag(tag: str) -> str:
    for label, t in _LANGUAGES:
        if t == tag:
            return label
    return "English"


# ──────────────────────────────────────────────────────
# Guardrails
# ──────────────────────────────────────────────────────
_BLOCKED = [
    r"(?i)(ignore|forget|disregard)\s+(previous|all|prior|above)\s+(instructions?|prompts?|rules?)",
    r"(?i)jailbreak",
    r"(?i)act\s+as\s+(a\s+)?(different|evil|unrestricted|dan)\s+",
    r"(?i)you\s+are\s+now\s+(a\s+)?(different|evil|unrestricted)",
    r"(?i)(drop|delete|truncate)\s+table",
    r"(?i)<\s*script",
    r"(?i)prompt\s*injection",
]
_PROF = r"(?i)\b(fuck|shit|bitch|asshole|bastard|cunt|dick|piss)\b"


def _validate(text: str) -> tuple:
    s = text.strip()
    if not s:         return False, "Please describe your issue."
    if len(s) < 5:    return False, "Please provide more detail (at least 5 characters)."
    if len(s) > 5000: return False, "Too long (max 5000 characters)."
    for p in _BLOCKED:
        if re.search(p, s):
            return False, "⚠️ Input contains disallowed content."
    if re.search(_PROF, s):
        return False, "⚠️ Please keep language professional."
    return True, ""


# ──────────────────────────────────────────────────────
# Voice widget — BCP-47 tag injected from Python
# ──────────────────────────────────────────────────────
def _voice_widget(lang_tag: str, target_key: str = "__vt__", submit_key: str = "__vs__") -> str:
    """
    Render a voice input widget.

    Parameters
    ----------
    lang_tag    : BCP-47 language tag passed to SpeechRecognition (e.g. "hi-IN")
    target_key  : aria-label / label text of the hidden text-input that receives
                  the transcript (default ``"__vt__"`` for the main form;
                  pass ``"__dvt__"`` for the diagnostic voice bridge)
    submit_key  : text of the hidden button that triggers Streamlit re-run
                  (default ``"__vs__"``; pass ``"__dvs__"`` for diagnostics)
    """
    label = _label_for_tag(lang_tag)
    return f"""
<style>
body{{margin:0;padding:0;font-family:-apple-system,"Segoe UI",sans-serif;}}
.vc{{background:#f7f8fa;border:1px solid #e5e7eb;border-radius:10px;padding:12px 14px;}}
.row{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}}
#vbtn{{background:#3b82d4;color:#fff;border:none;border-radius:7px;
  padding:7px 18px;cursor:pointer;font-size:13px;font-weight:600;min-width:100px;}}
#vbtn.rec{{background:#ef4444;animation:bl .75s infinite;}}
#vbtn.ok {{background:#22c55e;}}
@keyframes bl{{0%,100%{{opacity:1}}50%{{opacity:.5}}}}
.info{{flex:1;min-width:160px;}}
#st{{font-size:12px;color:#57606a;margin-bottom:2px;}}
#tx{{font-size:13px;color:#1f2328;font-style:italic;word-break:break-word;}}
.wave{{display:none;align-items:flex-end;gap:2px;height:18px;}}
.wave span{{width:3px;background:#ef4444;border-radius:2px;animation:wv .85s ease-in-out infinite;}}
.wave span:nth-child(2){{animation-delay:.11s;}}
.wave span:nth-child(3){{animation-delay:.22s;}}
.wave span:nth-child(4){{animation-delay:.33s;}}
.wave span:nth-child(5){{animation-delay:.44s;}}
@keyframes wv{{0%,100%{{height:4px}}50%{{height:16px}}}}
</style>
<div class="vc">
  <div class="row">
    <button id="vbtn" onclick="tog()">🎤 Speak</button>
    <div class="info">
      <div id="st">Click 🎤 to speak in <strong>{label}</strong></div>
      <div id="tx"></div>
    </div>
    <div class="wave" id="wave">
      <span></span><span></span><span></span><span></span><span></span>
    </div>
  </div>
</div>
<script>
(function(){{
  var rec=null, going=false;
  var LANG='{lang_tag}';
  var TARGET_KEY='{target_key}';
  var SUBMIT_KEY='{submit_key}';
  function g(id){{return document.getElementById(id);}}
  window.tog=function(){{going?stop():start();}};

  function start(){{
    var SR=window.SpeechRecognition||window.webkitSpeechRecognition;
    if(!SR){{g('st').textContent='⚠️ Use Google Chrome or Edge.';return;}}
    rec=new SR();
    rec.lang=LANG;
    rec.continuous=false;
    rec.interimResults=true;
    rec.maxAlternatives=1;
    rec.onstart=function(){{
      going=true;
      g('vbtn').className='rec';
      g('vbtn').textContent='⏹ Stop';
      g('st').textContent='🔴 Listening in '+LANG+'…';
      g('wave').style.display='flex';
    }};
    rec.onresult=function(e){{
      var interim='',final_='';
      for(var i=e.resultIndex;i<e.results.length;i++){{
        if(e.results[i].isFinal) final_+=e.results[i][0].transcript;
        else interim+=e.results[i][0].transcript;
      }}
      g('tx').textContent=final_||interim;
      if(final_) commit(final_);
    }};
    rec.onspeechend=function(){{try{{rec.stop();}}catch(x){{}}}};
    rec.onerror=function(e){{
      var m={{'not-allowed':'❌ Mic blocked.','no-speech':'⚠️ Nothing heard.','network':'❌ Network error.','aborted':'Stopped.'}};
      g('st').textContent=m[e.error]||'❌ '+e.error;
      stop();
    }};
    rec.onend=stop;
    rec.start();
  }}

  function stop(){{
    going=false;
    if(rec){{try{{rec.stop();}}catch(x){{}}}}
    g('wave').style.display='none';
    var b=g('vbtn');
    if(!b.classList.contains('ok')){{b.className='';b.textContent='🎤 Speak';}}
  }}

  function commit(text){{
    var b=g('vbtn');
    b.className='ok'; b.textContent='✅ Done';
    g('st').textContent='✅ Submitting…';
    setTimeout(function(){{push(text);}},300);
  }}

  function push(text){{
    var doc=window.parent.document;
    function findInput(key){{
      var inputs=doc.querySelectorAll('input[type="text"],input[aria-label]');
      for(var i=0;i<inputs.length;i++){{
        var el=inputs[i];
        if(el.getAttribute('aria-label')===key) return el;
        var lbl=el.closest('[data-testid="stTextInput"]');
        if(lbl){{
          var labelEl=lbl.querySelector('label');
          if(labelEl&&labelEl.textContent.trim()===key) return el;
        }}
      }}
      return null;
    }}
    function setVal(el,val){{
      if(!el) return false;
      var nv=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value');
      if(nv&&nv.set) nv.set.call(el,val); else el.value=val;
      el.dispatchEvent(new Event('input',{{bubbles:true}}));
      el.dispatchEvent(new Event('change',{{bubbles:true}}));
      return true;
    }}
    var vtEl=findInput(TARGET_KEY);
    if(vtEl){{
      setVal(vtEl,text);
      setTimeout(function(){{
        var btns=doc.querySelectorAll('button');
        for(var j=0;j<btns.length;j++){{
          if(btns[j].textContent.trim()===SUBMIT_KEY){{btns[j].click();return;}}
        }}
      }},150);
    }}
  }}
}})();
</script>
"""


# ──────────────────────────────────────────────────────
# Language selector
# ──────────────────────────────────────────────────────
def _language_selector(key: str) -> str:
    saved = st.session_state.get("incident_lang", "en-US")
    idx   = _LANG_TAGS.index(saved) if saved in _LANG_TAGS else 0
    chosen = st.selectbox(
        "🌍 Language",
        _LANG_LABELS,
        index=idx,
        key=key,
        help="Select the language for voice input. AI will respond in this language.",
    )
    tag = _LANG_TAGS[_LANG_LABELS.index(chosen)]
    st.session_state["incident_lang"] = tag
    return tag


# ──────────────────────────────────────────────────────
# Page entry
# ──────────────────────────────────────────────────────
def render() -> None:
    token = auth_utils.get_token()
    user  = auth_utils.get_user()
    if not token or not user:
        return

    st.title("🆕 New Incident")
    st.caption("Describe your IT issue by voice or text.")

    workflow_state = st.session_state.get("workflow_state")
    if not workflow_state:
        _show_form(token)
    else:
        _show_workflow(token, workflow_state)


# ──────────────────────────────────────────────────────
# Form (create new incident)
# ──────────────────────────────────────────────────────
def _show_form(token: str) -> None:
    st.markdown("---")
    lang = _language_selector("lang_form")

    st.markdown("##### 🎤 Voice Input")
    st.caption(f"Speak in **{_label_for_tag(lang)}** — submits automatically.")
    st.components.v1.html(_voice_widget(lang), height=110)

    # Hidden text input + button for JS → Python bridge
    st.markdown(
        "<style>"
        "div[data-testid='stTextInput']:has(label:contains('__vt__')),"
        "div[data-testid='stButton']:has(button:contains('__vs__')){"
        "display:none!important;height:0!important;overflow:hidden!important;"
        "margin:0!important;padding:0!important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    vt_raw    = st.text_input("__vt__", value="", key="__vt__", label_visibility="hidden")
    vs_click  = st.button("__vs__", key="__vs__")

    voice_text = vt_raw.strip()

    st.markdown("##### ✏️ Or Type Your Issue")
    query = st.text_area(
        "issue",
        value=voice_text,
        placeholder="e.g. My VPN is not connecting — or use 🎤 above",
        height=110,
        key="incident_query",
        label_visibility="collapsed",
    )

    n = len(query.strip()) if query else 0
    if n:
        color = "#22c55e" if n <= 4000 else "#ef4444"
        st.markdown(
            f"<div style='font-size:11px;color:{color};text-align:right;'>{n}/5000</div>",
            unsafe_allow_html=True,
        )

    col_btn, _ = st.columns([1, 5])
    with col_btn:
        manual = st.button("🚀 Start", type="primary", disabled=not bool(query.strip()))

    auto = (
        voice_text
        and not st.session_state.get("workflow_state")
        and not st.session_state.get("_voice_submitted")
    )

    if manual or auto or vs_click:
        q = query.strip() or voice_text
        if not q:
            st.warning("Please describe your issue first.")
            return
        ok, err = _validate(q)
        if not ok:
            st.error(err)
            return
        with st.spinner("🔍 AI is analyzing your issue…"):
            try:
                state = api.create_incident(token, q)
                st.session_state["workflow_state"]       = state
                st.session_state["workflow_thread_id"]   = state.get("thread_id")
                st.session_state["workflow_incident_id"] = state.get("incident_id")
                st.session_state["_voice_submitted"]     = True
                st.session_state.pop("__vt__", None)
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to start incident: {exc}")


# ──────────────────────────────────────────────────────
# Active workflow
# ──────────────────────────────────────────────────────
def _show_workflow(token: str, state: dict) -> None:
    st.session_state.pop("_voice_submitted", None)

    incident_id = st.session_state.get("workflow_incident_id", "")
    thread_id   = st.session_state.get("workflow_thread_id", "")
    status      = state.get("status", "IN_PROGRESS")

    lang = _language_selector("lang_workflow")

    if status == "RESOLVED":
        st.success(f"✅ Incident **RESOLVED** — ID: `{incident_id}`")
    elif status == "ESCALATED":
        st.error(f"🚨 Escalated to Human Support — ID: `{incident_id}`")
    else:
        st.info(f"🔄 In progress — ID: `{incident_id}` &nbsp;|&nbsp; 🌍 **{_label_for_tag(lang)}**")

    st.markdown("---")
    _render_history(state.get("conversation_history", []))

    awaiting = state.get("awaiting_user_input", False)
    itype    = state.get("user_input_type", "none")
    cur_node = state.get("current_node", "")

    if awaiting and status == "IN_PROGRESS":
        st.markdown("---")

        if itype == "verification":
            ans = render_verification_buttons(key_prefix=f"v_{cur_node}")
            if ans:
                _do_verify(token, thread_id, ans)

        elif itype == "diagnostic":
            questions  = state.get("diagnostic_questions", [])
            unanswered = [q for q in questions if q.get("answer") is None]
            q_text     = unanswered[-1]["question"] if unanswered else "Please provide more information."

            # Voice input for diagnostic — uses __dvt__/__dvs__ bridge keys
            st.markdown("##### 🎤 Speak Your Answer")
            st.caption(f"Or type below. Voice language: **{_label_for_tag(lang)}**")
            st.components.v1.html(
                _voice_widget(lang, target_key="__dvt__", submit_key="__dvs__"),
                height=110,
            )

            st.markdown(
                "<style>"
                "div[data-testid='stTextInput']:has(label:contains('__dvt__')),"
                "div[data-testid='stButton']:has(button:contains('__dvs__')){"
                "display:none!important;height:0!important;overflow:hidden!important;"
                "margin:0!important;padding:0!important;}"
                "</style>",
                unsafe_allow_html=True,
            )
            dvt_raw  = st.text_input("__dvt__", value="", key="__dvt__", label_visibility="hidden")
            dvs_click = st.button("__dvs__", key="__dvs__")

            voice_diag = dvt_raw.strip()
            ans = _diag_input(q_text, key=f"diag_{len(questions)}", default=voice_diag)

            auto_diag = bool(voice_diag and not st.session_state.get("_diag_submitted"))
            if ans or auto_diag or dvs_click:
                final_ans = ans or voice_diag
                ok, err   = _validate(final_ans)
                if not ok:
                    st.error(err)
                else:
                    st.session_state["_diag_submitted"] = True
                    _do_diag(token, thread_id, final_ans)

    elif status in ("RESOLVED", "ESCALATED"):
        st.session_state.pop("_diag_submitted", None)
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("📋 View Details"):
                session_utils.set_active_incident(incident_id)
                session_utils.navigate("incident_details")
        with c2:
            if st.button("🗑️ Delete", type="secondary"):
                st.session_state["_confirm_del"] = True
        with c3:
            if st.button("➕ New Incident", type="primary"):
                _clear()
                st.rerun()

        if st.session_state.get("_confirm_del"):
            st.warning(f"⚠️ Permanently delete incident `{incident_id}`?")
            y, n = st.columns(2)
            with y:
                if st.button("✅ Yes, Delete", type="primary", key="del_yes"):
                    if api.delete_incident(token, incident_id):
                        st.success("Deleted.")
                        _clear()
                        st.rerun()
                    else:
                        st.error("Delete failed.")
                    st.session_state.pop("_confirm_del", None)
            with n:
                if st.button("❌ Cancel", key="del_no"):
                    st.session_state.pop("_confirm_del", None)
                    st.rerun()


# ──────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────
def _render_history(history: list) -> None:
    """Render conversation — NO TTS button (removed by user request)."""
    for msg in history:
        role    = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            continue
        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(content)
            # TTS removed — was only reading English characters for non-Latin scripts


def _diag_input(question: str, key: str, default: str = "") -> str:
    st.info(f"💬 **{question}**")
    ans = st.text_input(
        "Answer:",
        value=default,
        key=key,
        placeholder="Type your answer — or speak above",
        max_chars=2000,
    )
    if st.button("Submit Answer", key=f"{key}_sub", type="primary"):
        if not ans.strip():
            st.warning("Please provide an answer.")
            return ""
        ok, err = _validate(ans)
        if not ok:
            st.error(err)
            return ""
        return ans.strip()
    return ""


def _do_verify(token: str, tid: str, ans: str) -> None:
    itype = "verification_yes" if ans == "yes" else "verification_no"
    with st.spinner("Processing…"):
        try:
            s = api.resume_incident(token=token, thread_id=tid,
                                    user_input=ans, input_type=itype)
            st.session_state["workflow_state"] = s
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _do_diag(token: str, tid: str, ans: str) -> None:
    # Clear the submitted flag BEFORE the API call so the next diagnostic
    # round's voice answer is not blocked by a stale True value.
    st.session_state.pop("_diag_submitted", None)
    with st.spinner("AI is analyzing…"):
        try:
            s = api.resume_incident(token=token, thread_id=tid,
                                    user_input=ans, input_type="diagnostic")
            st.session_state["workflow_state"] = s
            # Also clear the diagnostic voice bridge input so it doesn't
            # auto-submit again on the next rerun.
            st.session_state.pop("__dvt__", None)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


def _clear() -> None:
    for k in [
        "workflow_state", "workflow_thread_id", "workflow_incident_id",
        "incident_lang", "_voice_submitted", "_diag_submitted",
        "_confirm_del", "__vt__", "__dvt__",
    ]:
        st.session_state.pop(k, None)
