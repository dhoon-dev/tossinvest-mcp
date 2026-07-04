"""Client factory type definitions."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from tossinvest import TossInvestClient

type ClientContextFactory = Callable[[], AbstractContextManager[TossInvestClient]]
