"""Streamlit Community Cloud entry point.

The actual dashboard lives in ``frontend/app.py``. This thin shim exists so
that Streamlit Cloud's auto-discovery (which looks for ``streamlit_app.py``
at the repo root) finds the app without extra configuration.

To deploy:
    1. Push this repo to GitHub.
    2. Sign in to https://share.streamlit.io with your GitHub account.
    3. "New app" -> pick this repo and the ``main`` branch.
    4. Main file: ``streamlit_app.py``
    5. Advanced settings -> Requirements file: ``frontend/requirements.txt``
    6. Deploy. Done.

The dashboard reads the bundled World Bank snapshot at
``data/snapshots/country_stats.json`` so it works fully offline (i.e. without
the Node.js backend). When the backend is reachable at ``BACKEND_API_URL``
the dashboard prefers live data.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_FRONTEND = Path(__file__).resolve().parent / "frontend"
if str(_FRONTEND) not in sys.path:
    sys.path.insert(0, str(_FRONTEND))

runpy.run_path(str(_FRONTEND / "app.py"), run_name="__main__")
