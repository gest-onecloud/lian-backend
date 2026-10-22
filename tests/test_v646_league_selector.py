from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'frontend' / 'app.js').read_text(encoding='utf-8')
STYLE = (ROOT / 'frontend' / 'style.css').read_text(encoding='utf-8')
HTML = (ROOT / 'frontend' / 'index.html').read_text(encoding='utf-8')


def test_frontend_syntax_and_version():
    subprocess.run(['node', '--check', str(ROOT / 'frontend' / 'app.js')], check=True)
    assert "const LIAN_VERSION='64.6.0'" in APP
    assert 'LIAN V64.6.0 · DECISION INTELLIGENCE' in HTML


def test_league_selector_is_floating_and_not_a_wraparound_chip_bar():
    assert 'function closeLeagueMenu()' in APP
    assert 'function leagueLabel()' in APP
    assert 'function filterBar(comps)' in APP
    assert 'id="league-menu-toggle"' in APP
    assert 'id="league-menu"' in APP
    assert 'id="league-search"' in APP
    assert 'data-c' in APP
    assert '.league-menu{display:none;position:absolute;' in STYLE
    assert '.league-menu.open{display:flex;flex-direction:column}' in STYLE
    assert '.league-options{overflow:auto;' in STYLE
    assert '@media(max-width:700px)' in STYLE


def test_existing_filter_state_and_match_filter_contract_remain_intact():
    assert "let view='day',data=[],selected=new Set();" in APP
    assert "selected.has(c)?selected.delete(c):selected.add(c)" in APP
    assert "selected.clear();renderDay(comps);filterBar(comps)" in APP
    assert "data.filter(m=>!selected.size||selected.has(m.competition_id))" in APP
    assert "x.matches||[]" in APP
    assert "m.date===d" in APP
