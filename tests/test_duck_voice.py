import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from utils.duck_voice import DEFAULT_GOAL_SNIPPET, extract_goal_snippet, pick_duck_line


def test_extract_goal_snippet_strips_noise_and_limits_length():
    goal = "  <@12345> 매일 새벽 6시 러닝 3km!!! https://example.com  "
    snippet = extract_goal_snippet(goal, max_len=14)
    assert '<@' not in snippet
    assert 'http' not in snippet
    assert len(snippet) <= 17  # 14 + '...'
    assert snippet


def test_extract_goal_snippet_uses_fallback_when_empty():
    assert extract_goal_snippet('', max_len=14) == DEFAULT_GOAL_SNIPPET
    assert extract_goal_snippet('   ', max_len=14) == DEFAULT_GOAL_SNIPPET
    assert extract_goal_snippet('`   `', max_len=14) == DEFAULT_GOAL_SNIPPET


@pytest.mark.parametrize(
    'context',
    [
        'NORMAL_GROWTH',
        'LEVEL_UP',
        'SULKY_ENTER',
        'RUNAWAY_ENTER',
        'SULKY_RECOVER',
        'RUNAWAY_RECOVER',
        'DONE',
    ],
)
def test_pick_duck_line_returns_non_empty_for_all_contexts(context):
    line = pick_duck_line(context=context, goal_text='특이한 도전 ###@@@')
    assert isinstance(line, str)
    assert line.strip() != ''


def test_pick_duck_line_includes_personalized_goal_snippet():
    line = pick_duck_line(context='NORMAL_GROWTH', goal_text='영어 단어 30개 외우기')
    assert '영어 단어' in line


def test_pick_duck_line_avoids_previous_line_if_possible(monkeypatch):
    # random.choice를 항상 첫 후보로 고정해도 previous_line 필터링이 동작해야 한다.
    monkeypatch.setattr('utils.duck_voice.random.choice', lambda items: items[0])
    previous = pick_duck_line(context='LEVEL_UP', goal_text='독서 20분')
    current = pick_duck_line(context='LEVEL_UP', goal_text='독서 20분', previous_line=previous)
    assert current != previous


def test_pick_duck_line_falls_back_on_unknown_context():
    line = pick_duck_line(context='UNKNOWN_CONTEXT', goal_text='일기 쓰기')
    assert line
