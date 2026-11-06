import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import pytest


@pytest.fixture(autouse=True)
def _sport_hors_ligne(monkeypatch):
    """Les tests n'interrogent jamais les sources sportives."""
    from signal_matin.journal import sport

    def hors_ligne(url):
        raise OSError("hors ligne (tests)")
    monkeypatch.setattr(sport, "_lire", hors_ligne)
