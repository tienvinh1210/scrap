"""Walk the cockpit through its controls with Streamlit's own test harness."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

APP = str(REPO_ROOT / "dashboard" / "cockpit" / "nova_app.py")
MART = REPO_ROOT / "outputs" / "monitor" / "monitor_mart.json"

pytestmark = pytest.mark.skipif(
    not MART.exists(), reason="mart not built — run python -m src.monitor.build_mart"
)


def run(**state) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=300)
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    return at


def tiles(at: AppTest) -> dict[str, str]:
    """Label -> value for the four KPI tiles, read back out of their markup."""

    found = {}
    for block in at.get("html"):
        for label, value in re.findall(
            r"nc-kpi-label'>([^<]+)</div><div class='nc-kpi-value'>([^<]+)<", block.body
        ):
            found[label] = value
    return found


def test_default_render_is_the_observed_dataset():
    at = run()
    assert at.segmented_control[0].value == "observed"
    assert [s.value for s in at.selectbox] == ["All", "All", "All"]
    assert len(at.get("plotly_chart")) == 4  # stepper, matrix, trend, buckets

    values = tiles(at)
    assert set(values) == {"Total Cost", "Addressed", "Response Gap", "Attrition Lead Time"}
    assert values["Total Cost"] == "$78.1M"
    assert values["Attrition Lead Time"].endswith("months")


def test_guardrail_banner_is_always_present():
    at = run()
    assert any("Responsible use" in info.value for info in at.info)


def test_synthetic_banner_only_appears_under_a_scenario():
    assert not run().warning
    for scenario in ("scenario_a", "scenario_b"):
        at = run(scenario=scenario)
        assert any("simulation" in w.value for w in at.warning), scenario


def test_entity_filter_moves_the_numbers():
    baseline = tiles(run())
    filtered = tiles(run(entity_choice="Entity_B"))
    assert filtered["Total Cost"] != baseline["Total Cost"]
    assert filtered["Response Gap"] != baseline["Response Gap"]


def test_department_filter_moves_the_numbers():
    baseline = tiles(run())
    filtered = tiles(run(department_choice="Risk & Compliance"))
    assert filtered["Total Cost"] != baseline["Total Cost"]


def test_scenarios_move_the_numbers():
    baseline = tiles(run())
    a = tiles(run(scenario="scenario_a"))
    b = tiles(run(scenario="scenario_b"))
    assert a["Total Cost"] != baseline["Total Cost"]
    assert a["Response Gap"] != b["Response Gap"]


def test_wave_filter_reads_that_wave():
    at = run(wave_choice=3)
    assert "wave 3" in " ".join(block.body for block in at.get("html"))


def test_stale_wave_selection_is_dropped_when_leaving_a_scenario():
    """Wave 8 exists only in the scenarios; going back to observed must not crash."""

    at = AppTest.from_file(APP, default_timeout=300)
    at.session_state["scenario"] = "scenario_a"
    at.session_state["wave_choice"] = 8
    at.run()
    assert not at.exception

    at.segmented_control[0].set_value("observed").run()
    assert not at.exception
    assert at.selectbox[2].value == "All"
