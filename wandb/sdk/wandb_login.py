#
# -*- coding: utf-8 -*-
"""
login.
"""

from __future__ import print_function

import logging

import click
import wandb
from wandb.errors.error import UsageError
from wandb.internal.internal_api import Api
from wandb.lib import apikey

from .wandb_settings import Settings

logger = logging.getLogger("wandb")

if wandb.TYPE_CHECKING:  # type: ignore
    from typing import Dict, Optional  # noqa: F401 pylint: disable=unused-import


def login(anonymous=None, key=None, relogin=None, host=None, force=None):
    """Log in to W&B.

    Args:
        settings (dict, optional): Override settings.
        relogin (bool, optional): If true, will re-prompt for API key.
        host (string, optional): The host to connect to
        anonymous (string, optional): Can be "must", "allow", or "never".
            If set to "must" we'll always login anonymously, if set to
            "allow" we'll only create an anonymous user if the user
            isn't already logged in.
    Returns:
        bool: if key is configured

    Raises:
        UsageError - if api_key can not configured and no tty
    """
    kwargs = locals()
    configured = _login(**kwargs)
    return True if configured else False


class _WandbLogin(object):
    def __init__(self):
        self.kwargs: Optional[Dict] = None
        self._settings: Optional[Settings] = None
        self._backend = None
        self._wl = None
        self._key = None

    def setup(self, kwargs):
        self.kwargs = kwargs

        # built up login settings
        login_settings: Settings = wandb.Settings()
        settings_param = kwargs.pop("_settings", None)
        if settings_param:
            login_settings._apply_settings(settings_param)
        login_settings._apply_login(kwargs)

        # make sure they are applied globally
        self._wl = wandb.setup(settings=login_settings)
        self._settings = self._wl._settings

    def is_logged_in(self):
        return apikey.api_key(settings=self._settings) is not None

    def set_backend(self, backend):
        self._backend = backend

    def login(self):
        active_entity = None
        logged_in = self.is_logged_in()
        if self._settings.relogin:
            logged_in = False
        if logged_in:
            # TODO: do we want to move all login logic to the backend?
            if self._backend:
                pass
                # res = self._backend.interface.communicate_login(key, anonymous)
                # active_entity = res.active_entity
            else:
                active_entity = self._wl._get_entity()
        if active_entity:
            login_state_str = "Currently logged in as:"
            login_info_str = "(use `wandb login --relogin` to force relogin)"
            wandb.termlog(
                "{} {} {}".format(
                    login_state_str,
                    click.style(active_entity, fg="yellow"),
                    login_info_str,
                ),
                repeat=False,
            )
        return logged_in

    def configure_api_key(self, key):
        if self._settings._jupyter:
            wandb.termwarn(
                (
                    "If you're specifying your api key in code, ensure this "
                    "code is not shared publically.\nConsider setting the "
                    "WANDB_API_KEY environment variable, or running "
                    "`wandb login` from the command line."
                )
            )
        apikey.write_key(self._settings, key)
        self._key = key

    def update_session(self, key):
        settings: Settings = wandb.Settings()
        settings._apply_source_login(dict(api_key=key))
        self._wl._update(settings=settings)

    def prompt_api_key(self):
        api = Api()
        key = apikey.prompt_api_key(
            self._settings,
            api=api,
            no_offline=self._settings.force,
            no_create=self._settings.force,
        )
        if key is False:
            raise UsageError("api_key not configured (no-tty).  Run wandb login")
        self.update_session(key)
        self._key = key

    def propogate_login(self):
        # TODO(jhr): figure out if this is really necessary
        if self._backend:
            # TODO: calling this twice is gross, this deserves a refactor
            # Make sure our backend picks up the new creds
            # _ = self._backend.interface.communicate_login(key, anonymous)
            pass


def _login(
    anonymous=None, key=None, relogin=None, host=None, force=None, _backend=None
):
    kwargs = locals()

    if wandb.run is not None:
        wandb.termwarn("Calling wandb.login() after wandb.init() has no effect.")
        return True

    wlogin = _WandbLogin()

    _backend = kwargs.pop("_backend", None)
    if _backend:
        wlogin.set_backend(_backend)

    # configure login object
    wlogin.setup(kwargs)

    if wlogin._settings._offline:
        return False

    # perform a login
    logged_in = wlogin.login()

    key = kwargs.get("key")
    if key:
        wlogin.configure_api_key(key)

    if logged_in:
        return logged_in

    if not key:
        wlogin.prompt_api_key()

    # make sure login credentials get to the backend
    wlogin.propogate_login()

    return wlogin._key or False
