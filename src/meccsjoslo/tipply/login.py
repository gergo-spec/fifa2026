"""Login node – tipp.ly hitelesítés, mentett session újrahasználatával."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

# Login form szelektorok. Provizórikusak – élesben igazolandók; a CSRF token
# automatikusan megy, mert a valódi formot küldjük be, nem kézzel POST-olunk.
EMAIL_SELECTOR = "input[type='email']"
PASSWORD_SELECTOR = "input[type='password']"
REMEMBER_SELECTOR = "input[type='checkbox'][name='remember']"
SUBMIT_SELECTOR = "button[type='submit']"


class AuthenticationError(RuntimeError):
    """A login form beküldése után is bejelentkezetlen a futás."""


class LoginOutcome(BaseModel):
    authenticated: bool
    reused_session: bool


def _is_login_url(url: str) -> bool:
    return "/login" in url


async def ensure_authenticated(browser, config) -> LoginOutcome:
    """Bejelentkezett session elérése a tipp.ly-on.

    Érvényes mentett ``storage_state``-et újrahasznál; különben email/jelszó
    formmal (+ remember-me) bejelentkezik és elmenti az új sessiont.
    """
    state_path = Path(config.storage_state_path)
    have_saved_session = state_path.exists()

    await browser.open(storage_state=str(state_path) if have_saved_session else None)
    await browser.goto(config.bets_url)

    if not _is_login_url(await browser.current_url()):
        return LoginOutcome(authenticated=True, reused_session=True)

    await _submit_login_form(browser, config)

    await browser.goto(config.bets_url)
    if _is_login_url(await browser.current_url()):
        raise AuthenticationError("login form submitted but still redirected to /hu/login")

    await browser.save_storage_state(str(state_path))
    return LoginOutcome(authenticated=True, reused_session=False)


async def _submit_login_form(browser, config) -> None:
    await browser.fill(EMAIL_SELECTOR, config.email)
    await browser.fill(PASSWORD_SELECTOR, config.password.get_secret_value())
    await browser.set_checkbox(REMEMBER_SELECTOR, True)
    await browser.click(SUBMIT_SELECTOR)
