"""RIFT Held-Out Evaluation Guard — Phase 3.6 §19.

Prevents accidental access to held-out test set labels during development.

Every access to held-out ground truth MUST pass through this guard.
If any non-oracle code attempts to read held-out labels, the guard
raises HeldOutLeakageError.

Authority: Phase 3.6 §19, docs/PHASE_3_SPEC_FREEZE.md §16.
"""
from __future__ import annotations

import inspect
import warnings
from pathlib import Path
from typing import Any, Callable, List, Optional


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class HeldOutLeakageError(Exception):
    """
    Raised when held-out test set labels are accessed by non-oracle code.

    This exception is a hard stop — it must never be caught silently.
    Any suppression of this exception invalidates the evaluation.
    """
    pass


# ---------------------------------------------------------------------------
# Guard
# ---------------------------------------------------------------------------

class HeldOutGuard:
    """
    Leakage detection guard for the held-out test set.

    Usage:
        guard = HeldOutGuard()
        guard.allow_oracle("ORACLE_UPPER_BOUND_RUN_2024")
        guard.check_access(caller_name="some_baseline")
        data = guard.load_held_out(path)  # raises if not allowed

    The guard maintains a registry of allowed oracle evaluation runs.
    Any other call to load held-out labels raises HeldOutLeakageError.
    """

    def __init__(self):
        self._allowed_tokens: List[str] = []
        self._active_token: Optional[str] = None
        self._access_log: List[dict] = []

    def allow_oracle(self, oracle_token: str) -> None:
        """
        Register an oracle token for a privileged final evaluation run.

        oracle_token must be a unique identifier for the evaluation run
        (e.g., "ORACLE_FINAL_EVAL_PHASE_8_2024_001").
        """
        self._allowed_tokens.append(oracle_token)

    def activate_token(self, oracle_token: str) -> None:
        """Activate a pre-registered oracle token for the current run."""
        if oracle_token not in self._allowed_tokens:
            raise HeldOutLeakageError(
                f"Token '{oracle_token}' is not registered. "
                "Call allow_oracle(token) before activating. "
                "Attempted held-out access denied."
            )
        self._active_token = oracle_token

    def deactivate_token(self) -> None:
        """Deactivate the active oracle token after evaluation."""
        self._active_token = None

    def check_access(self, caller_name: str = "unknown") -> None:
        """
        Check that the current context is authorized to access held-out labels.

        Raises HeldOutLeakageError if no active oracle token is set.
        Logs the access for audit.
        """
        frame = inspect.currentframe()
        caller_info = ""
        if frame and frame.f_back:
            caller_info = (
                f"{frame.f_back.f_code.co_filename}:{frame.f_back.f_lineno}"
            )

        self._access_log.append({
            "caller": caller_name,
            "caller_info": caller_info,
            "active_token": self._active_token,
            "authorized": self._active_token is not None,
        })

        if self._active_token is None:
            raise HeldOutLeakageError(
                f"HELD-OUT LEAKAGE DETECTED: '{caller_name}' attempted to access "
                "held-out test set labels without an active oracle token. "
                "This access is FORBIDDEN during development and tuning. "
                "The held-out test set must remain sealed until final evaluation. "
                f"Caller location: {caller_info}. "
                "Authority: docs/PHASE_3_SPEC_FREEZE.md §16."
            )

    def load_held_out(self, path: Path) -> Any:
        """
        Load held-out test set data. Raises HeldOutLeakageError if not authorized.

        Parameters
        ----------
        path : Path to held-out data file

        Returns
        -------
        dict : parsed JSON content of the held-out file
        """
        import json

        frame = inspect.currentframe()
        caller_name = "unknown"
        if frame and frame.f_back:
            caller_name = frame.f_back.f_code.co_name

        self.check_access(caller_name=caller_name)

        if not path.exists():
            raise FileNotFoundError(f"Held-out file not found: {path}")

        with open(path) as f:
            return json.load(f)

    def get_access_log(self) -> List[dict]:
        """Return the full access log for audit."""
        return list(self._access_log)

    def assert_no_unauthorized_access(self) -> None:
        """
        Assert that no unauthorized access occurred.
        Call at the end of each test suite.
        Raises AssertionError if any unauthorized access was logged.
        """
        unauthorized = [e for e in self._access_log if not e["authorized"]]
        if unauthorized:
            raise AssertionError(
                f"HELD-OUT LEAKAGE DETECTED: {len(unauthorized)} unauthorized "
                f"access attempts:\n" +
                "\n".join(
                    f"  {e['caller']} at {e['caller_info']}"
                    for e in unauthorized
                )
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

# Global guard instance — shared across the entire evaluation pipeline
_global_guard = HeldOutGuard()


def get_guard() -> HeldOutGuard:
    """Return the global held-out guard instance."""
    return _global_guard
