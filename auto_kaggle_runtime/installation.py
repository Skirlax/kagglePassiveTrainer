from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Iterable

logger = logging.getLogger(__name__)


class InstallationManager:
    """Install Python packages with the current interpreter."""

    def attempt_install(self, modules: Iterable[str], ignore: Iterable[str] = ()) -> None:
        ignored_modules = set(ignore)
        for module in modules:
            if module in ignored_modules:
                continue
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', module])
            except subprocess.CalledProcessError:
                logger.exception('Failed to install module %s', module)
