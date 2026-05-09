import streamlit as st

from backend.app import create_app

st.set_page_config(page_title="ProctorAI Streamlit", page_icon="🎓", layout="wide")


@st.cache_resource
def _get_client():
    app = create_app("production")
    return app.test_client()


def _api_request(method: str, path: str, token: str | None = None, payload: dict | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return _get_client().open(path=path, method=method, json=payload, headers=headers)


def _json(resp):
    try:
        return resp.get_json()
    except Exception:
        return {"error": "Invalid response"}


st.title("🎓 ProctorAI (Streamlit Deployment)")
st.caption("Streamlit wrapper for backend health, auth, exams, and admin monitoring endpoints.")

if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

with st.sidebar:
    st.header("Authentication")
    if st.session_state.token:
        st.success(f"Logged in as {st.session_state.user.get('email')} ({st.session_state.user.get('role')})")
        if st.button("Logout", use_container_width=True):
            st.session_state.token = None
            st.session_state.user = None
            st.rerun()
    else:
        email = st.text_input("Email", value="admin@proctor.local")
        password = st.text_input("Password", type="password")
        if st.button("Login", use_container_width=True):
            resp = _api_request("POST", "/api/auth/login", payload={"email": email, "password": password})
            data = _json(resp)
            if resp.status_code == 200 and data.get("token"):
                st.session_state.token = data["token"]
                st.session_state.user = data.get("user")
                st.success("Login successful")
                st.rerun()
            else:
                st.error(data.get("error", "Login failed"))

tab_health, tab_exams, tab_sessions, tab_alerts = st.tabs(["Health", "Exams", "Sessions", "Alerts/Stats"])

with tab_health:
    resp = _api_request("GET", "/api/health")
    st.write({"status_code": resp.status_code, "data": _json(resp)})

with tab_exams:
    if not st.session_state.token:
        st.info("Login to use this section.")
    else:
        resp = _api_request("GET", "/api/exams/", token=st.session_state.token)
        st.write({"status_code": resp.status_code, "data": _json(resp)})

with tab_sessions:
    if not st.session_state.token:
        st.info("Login to use this section.")
    else:
        resp = _api_request("GET", "/api/exams/sessions/", token=st.session_state.token)
        st.write({"status_code": resp.status_code, "data": _json(resp)})

with tab_alerts:
    if not st.session_state.token:
        st.info("Login to use this section.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            alerts_resp = _api_request("GET", "/api/proctor/alerts", token=st.session_state.token)
            st.write({"alerts_status_code": alerts_resp.status_code, "alerts": _json(alerts_resp)})
        with col2:
            stats_resp = _api_request("GET", "/api/proctor/stats", token=st.session_state.token)
            st.write({"stats_status_code": stats_resp.status_code, "stats": _json(stats_resp)})
