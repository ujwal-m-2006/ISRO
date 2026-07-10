"""
Authenticates against ISRO's PRADAN portal, which uses Keycloak
(idp.issdc.gov.in) for OpenID Connect login in front of the JSF/PrimeFaces
application at pradan1.issdc.gov.in. This automates the same login a browser
performs — GET the protected page, follow the redirect to Keycloak's login
form, parse the session-bound form action (session_code/execution/tab_id),
POST credentials to it, then follow the redirect chain back so PRADAN
completes the OIDC code exchange server-side and issues an authenticated
JSESSIONID.

Credentials are read from environment variables (PRADAN_USERNAME /
PRADAN_PASSWORD) — never hardcoded, never logged. Set them in backend/.env
(gitignored) or your shell environment.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PRADAN_BASE = "https://pradan1.issdc.gov.in/al1"
PROTECTED_URL = f"{PRADAN_BASE}/protected/payload.xhtml"

FORM_ACTION_RE = re.compile(r'<form id="kc-form-login"[^>]*action="([^"]+)"', re.IGNORECASE)


class PradanAuthError(Exception):
    pass


def _get_credentials() -> tuple[str, str]:
    username = os.getenv("PRADAN_USERNAME")
    password = os.getenv("PRADAN_PASSWORD")
    if not username or not password:
        raise PradanAuthError(
            "PRADAN_USERNAME / PRADAN_PASSWORD not set. Add them to backend/.env "
            "(see backend/.env.example) — this integration is disabled until then."
        )
    return username, password


def login() -> requests.Session:
    """Returns an authenticated requests.Session with valid PRADAN cookies.

    Raises PradanAuthError on any failure (missing credentials, bad login,
    unexpected page structure, or a WAF/bot-detection challenge page).
    """
    username, password = _get_credentials()

    session = requests.Session()
    session.headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
    )

    login_page = session.get(PROTECTED_URL, timeout=30)
    login_page.raise_for_status()

    match = FORM_ACTION_RE.search(login_page.text)
    if not match:
        raise PradanAuthError(
            "Could not find the Keycloak login form on PRADAN's page — the portal's "
            "login flow may have changed, or a bot-protection challenge page was served."
        )
    action_url = match.group(1).replace("&amp;", "&")

    auth_response = session.post(
        action_url,
        data={"username": username, "password": password, "credentialId": ""},
        timeout=30,
        allow_redirects=True,
    )
    auth_response.raise_for_status()

    if "kc-form-login" in auth_response.text:
        raise PradanAuthError(
            "PRADAN login rejected the credentials (still on the login form after "
            "submitting) — check PRADAN_USERNAME/PRADAN_PASSWORD in backend/.env."
        )

    if not session.cookies.get("JSESSIONID", domain="pradan1.issdc.gov.in"):
        raise PradanAuthError(
            "Login POST did not error, but no authenticated PRADAN session cookie was "
            "issued — the portal may require additional verification (MFA/CAPTCHA) "
            "that this automated flow can't complete."
        )

    logger.info("PRADAN login succeeded for user %s", username)
    return session
