"""Streamlit Community Cloud entry point.

The actual dashboard lives next to this file at ``frontend/app.py``. This
thin shim exists so that Streamlit Community Cloud picks up the dashboard
*and* automatically uses ``frontend/requirements.txt`` (Streamlit Cloud
prefers a ``requirements.txt`` co-located with the main file before falling
back to repo-root files).

To deploy:
    1. Push this repo to GitHub.
    2. Sign in to https://share.streamlit.io with your GitHub account.
    3. "New app" -> pick this repo and the ``main`` branch.
    4. Main file: ``frontend/streamlit_app.py``
    5. Deploy. Streamlit Cloud will install ``frontend/requirements.txt``
       automatically because it sits beside the main file.

The dashboard reads the bundled World Bank snapshot at
``data/snapshots/country_stats.json`` so it works fully offline (i.e.
without the Node.js backend). When the backend is reachable at
``BACKEND_API_URL`` the dashboard prefers live data.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

runpy.run_path(str(_HERE / "app.py"), run_name="__main__")
