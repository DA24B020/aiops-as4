import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx


def session_id():
    ctx = get_script_run_ctx()
    if ctx is None:
        return "unknown"
    return ctx.session_id[:8]


def client_ip():
    try:
        ip = getattr(st.context, "ip_address", None)
        if ip:
            return ip
        headers = st.context.headers
        forwarded = headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        host = headers.get("Host", "")
        if host.startswith(("localhost", "127.0.0.1")):
            return "127.0.0.1"
    except Exception:
        pass
    return "unknown"
