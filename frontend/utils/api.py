"""
Frontend API client: all calls to the FastAPI backend.
"""
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

BACKEND_URL = "http://127.0.0.1:8000"


def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(username: str, email: str, password: str) -> Dict[str, Any]:
    resp = requests.post(
        f"{BACKEND_URL}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=10,
    )
    return {"status_code": resp.status_code, "data": resp.json()}


def check_user_exists(login: str) -> bool | None:
    """
    Returns True if user exists, False if not, None on network error.
    Used to show "Please register first" before attempting login.
    """
    try:
        resp = requests.get(
            f"{BACKEND_URL}/auth/check-user",
            params={"login": login},
            timeout=5,
        )
        if resp.status_code == 200:
            return resp.json().get("exists", None)
        return None
    except Exception:
        return None


def login(username: str, password: str) -> Dict[str, Any]:
    resp = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    return {"status_code": resp.status_code, "data": resp.json()}


def get_me(token: str) -> Dict[str, Any]:
    resp = requests.get(
        f"{BACKEND_URL}/auth/me",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


def create_incident(token: str, query: str) -> Dict[str, Any]:
    resp = requests.post(
        f"{BACKEND_URL}/incidents",
        json={"query": query},
        headers=_headers(token),
        timeout=120,  # LLM can be slow
    )
    if resp.status_code in (200, 201):
        return resp.json()
    raise RuntimeError(f"Create incident failed: {resp.status_code} {resp.text[:200]}")


def resume_incident(
    token: str,
    thread_id: str,
    user_input: str,
    input_type: str,
    resolved: Optional[bool] = None,
) -> Dict[str, Any]:
    payload = {"user_input": user_input, "input_type": input_type, "resolved": resolved}
    resp = requests.post(
        f"{BACKEND_URL}/incidents/{thread_id}/resume",
        json=payload,
        headers=_headers(token),
        timeout=120,
    )
    if resp.status_code == 200:
        return resp.json()
    raise RuntimeError(f"Resume incident failed: {resp.status_code} {resp.text[:200]}")


def delete_incident(token: str, incident_id: str) -> bool:
    """Delete an incident. Returns True on success."""
    try:
        resp = requests.delete(
            f"{BACKEND_URL}/incidents/{incident_id}",
            headers=_headers(token),
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def admin_delete_incident(token: str, incident_id: str) -> bool:
    """Admin delete an incident. Returns True on success."""
    try:
        resp = requests.delete(
            f"{BACKEND_URL}/admin/incidents/{incident_id}",
            headers=_headers(token),
            timeout=10,
        )
        return resp.status_code in (200, 204)
    except Exception:
        return False


def get_incident_history(token: str) -> List[Dict]:
    resp = requests.get(
        f"{BACKEND_URL}/incidents/history",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else []


def get_incident_detail(token: str, incident_id: str) -> Optional[Dict]:
    resp = requests.get(
        f"{BACKEND_URL}/incidents/{incident_id}",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else None


def get_user_stats(token: str) -> Dict:
    resp = requests.get(
        f"{BACKEND_URL}/incidents/stats",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {}


# ── Admin endpoints ──────────────────────────────────────────
def admin_dashboard(token: str) -> Dict:
    resp = requests.get(f"{BACKEND_URL}/admin/dashboard", headers=_headers(token), timeout=10)
    return resp.json() if resp.status_code == 200 else {}


def admin_all_incidents(token: str, **params) -> List[Dict]:
    resp = requests.get(
        f"{BACKEND_URL}/admin/incidents",
        headers=_headers(token),
        params=params,
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else []


def admin_get_incident(token: str, incident_id: str) -> Optional[Dict]:
    resp = requests.get(
        f"{BACKEND_URL}/admin/incidents/{incident_id}",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else None


def admin_get_handoffs(token: str, resolved: Optional[bool] = None) -> List[Dict]:
    params = {}
    if resolved is not None:
        params["resolved"] = resolved
    resp = requests.get(
        f"{BACKEND_URL}/admin/handoffs",
        headers=_headers(token),
        params=params,
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else []


def admin_take_ownership(token: str, incident_id: str) -> Dict:
    resp = requests.post(
        f"{BACKEND_URL}/admin/incidents/{incident_id}/take-ownership",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json()


def admin_take_ownership_by_handoff(token: str, handoff_id: int) -> Dict:
    """Take ownership using the handoff's own integer ID — no incident UUID lookup needed."""
    resp = requests.post(
        f"{BACKEND_URL}/admin/handoffs/{handoff_id}/take-ownership",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {"error": resp.text}


def admin_resolve_handoff(token: str, handoff_id: int) -> Dict:
    """Resolve a handoff directly by its integer ID."""
    resp = requests.post(
        f"{BACKEND_URL}/admin/handoffs/{handoff_id}/resolve",
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {"error": resp.text}


def admin_add_notes_by_handoff(token: str, handoff_id: int, notes: str) -> Dict:
    """Add notes to a handoff directly by its integer ID."""
    resp = requests.post(
        f"{BACKEND_URL}/admin/handoffs/{handoff_id}/notes",
        json={"notes": notes},
        headers=_headers(token),
        timeout=10,
    )
    return resp.json() if resp.status_code == 200 else {"error": resp.text}


def admin_resolve_incident(token: str, incident_id: str, notes: str = "") -> Dict:
    resp = requests.post(
        f"{BACKEND_URL}/admin/incidents/{incident_id}/resolve",
        json={"agent_notes": notes},
        headers=_headers(token),
        timeout=10,
    )
    return resp.json()


def admin_add_notes(token: str, incident_id: str, notes: str) -> Dict:
    resp = requests.post(
        f"{BACKEND_URL}/admin/incidents/{incident_id}/notes",
        json={"notes": notes},
        headers=_headers(token),
        timeout=10,
    )
    return resp.json()


def admin_analytics(token: str) -> Dict:
    resp = requests.get(f"{BACKEND_URL}/admin/analytics", headers=_headers(token), timeout=10)
    return resp.json() if resp.status_code == 200 else {}


def admin_list_users(token: str) -> List[Dict]:
    resp = requests.get(f"{BACKEND_URL}/admin/users", headers=_headers(token), timeout=10)
    return resp.json() if resp.status_code == 200 else []


def admin_update_user(token: str, user_id: int, **kwargs) -> Dict:
    resp = requests.patch(
        f"{BACKEND_URL}/admin/users/{user_id}",
        json=kwargs,
        headers=_headers(token),
        timeout=10,
    )
    return resp.json()


def admin_get_evaluations(token: str) -> Dict:
    resp = requests.get(f"{BACKEND_URL}/admin/evaluations", headers=_headers(token), timeout=30)
    return resp.json() if resp.status_code == 200 else {}


def admin_run_evaluation(token: str) -> Dict:
    resp = requests.post(
        f"{BACKEND_URL}/admin/evaluations/run",
        headers=_headers(token),
        timeout=600,  # Evaluation can take a while
    )
    return resp.json() if resp.status_code == 200 else {"error": resp.text}


def system_health(token: str) -> Dict:
    resp = requests.get(f"{BACKEND_URL}/system/health", headers=_headers(token), timeout=10)
    return resp.json() if resp.status_code == 200 else {"backend": "error"}


def check_backend() -> bool:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False
