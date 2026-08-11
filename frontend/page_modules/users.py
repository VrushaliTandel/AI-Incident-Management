"""
Admin User Management page.
"""
import streamlit as st
from datetime import datetime
from frontend.utils import api, auth as auth_utils


def _fmt_date(dt_str) -> str:
    if not dt_str:
        return "—"
    try:
        dt = datetime.fromisoformat(str(dt_str).replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(dt_str)


def render() -> None:
    token = auth_utils.get_token()
    current_user = auth_utils.get_user()
    if not token:
        return

    st.title("👥 User Management")
    st.caption("Manage all platform users.")
    st.markdown("---")

    users = api.admin_list_users(token)
    if not users:
        st.info("No users found.")
        return

    # Table
    table_data = []
    for u in users:
        table_data.append({
            "ID": u.get("id"),
            "Username": u.get("username"),
            "Email": u.get("email"),
            "Role": u.get("role"),
            "Active": "✅" if u.get("is_active") else "❌",
            "Incidents": u.get("incident_count", 0),
            "Created": _fmt_date(u.get("created_at")),
        })
    st.dataframe(table_data, use_container_width=True, hide_index=True)
    st.markdown("---")

    # User actions
    st.subheader("Manage User")
    user_names = [u["username"] for u in users]
    selected = st.selectbox("Select user to manage:", user_names, key="users_select")
    selected_user = next((u for u in users if u["username"] == selected), None)

    if selected_user:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Username:** {selected_user['username']}")
            st.markdown(f"**Email:** {selected_user['email']}")
            st.markdown(f"**Role:** {selected_user['role']}")
            st.markdown(f"**Active:** {'Yes' if selected_user['is_active'] else 'No'}")
            st.markdown(f"**Incidents:** {selected_user.get('incident_count', 0)}")

        with col2:
            is_self = selected_user.get("id") == current_user.get("id") if current_user else False

            new_role = st.selectbox(
                "Change Role:",
                ["user", "admin"],
                index=0 if selected_user["role"] == "user" else 1,
                key="users_role_select",
            )
            new_active = st.checkbox(
                "Active",
                value=selected_user["is_active"],
                disabled=is_self,
                key="users_active_check",
            )

            if st.button("💾 Save Changes", type="primary"):
                if is_self and not new_active:
                    st.error("Cannot deactivate your own account.")
                else:
                    kwargs = {}
                    if new_role != selected_user["role"]:
                        kwargs["role"] = new_role
                    if new_active != selected_user["is_active"]:
                        kwargs["is_active"] = new_active
                    if kwargs:
                        result = api.admin_update_user(token, selected_user["id"], **kwargs)
                        if result.get("id"):
                            st.success("User updated successfully.")
                            st.rerun()
                        else:
                            st.error(f"Update failed: {result}")
                    else:
                        st.info("No changes to save.")
