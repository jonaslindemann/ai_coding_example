# -*- coding: utf-8 -*-
"""
Simulated-user tests for the web application (NiceGUI user fixture).

Run with ``pytest`` from this directory. These test the application
layer only: that the inputs reach the model and the design search can be
run and applied. The engineering results are tested in the parent
directory.
"""

import pytest
from nicegui import ui
from nicegui.testing import User

import frame_app

@pytest.fixture
def app_page():
    created = []

    @ui.page("/")
    def index():
        created.append(frame_app.FrameApp())

    return created


async def wait_for_solve(user, text):
    for _ in range(50):
        try:
            await user.should_see(text, retries=1)
            return
        except AssertionError:
            pass
    await user.should_see(text)


async def test_pinned_reference_frame_fails_drift(user: User, app_page):
    await user.open("/")
    await wait_for_solve(user, "As modelled")
    app = app_page[0]
    app.base.value = "pinned"
    await wait_for_solve(user, "pinned bases")
    await user.should_see("h/221")


async def test_design_search_and_apply(user: User, app_page):
    await user.open("/")
    await wait_for_solve(user, "As modelled")
    app = app_page[0]
    app.base.value = "pinned"
    await wait_for_solve(user, "pinned bases")

    app.tabs.value = "Design"
    await app.run_design_search()
    await user.should_see("Solved 64 combinations")
    assert sum(r["ok"] for r in app.design["rows"]) == 14
    best = next(r for r in app.design["rows"] if r["ok"])
    assert (best["column"], best["beam"]) == ("HEA 280", "IPE 360")

    # Clicking a table row sends (event, row, index)
    row = {"rank": 1, "column": best["column"], "beam": best["beam"]}
    app.apply_design(type("Event", (), {"args": [{}, row, 0]})())
    await wait_for_solve(user, "HEA 280 / IPE 360")
    assert app.frame.column_section == "HEA 280"
    assert app.frame.summary_values["drift_ok"]
