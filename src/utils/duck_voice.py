import random
import re
from typing import Dict, List

DEFAULT_GOAL_SNIPPET = '오늘의 도전'
DEFAULT_CONTEXT = 'NORMAL_GROWTH'

VOICE_TEMPLATES: Dict[str, List[str]] = {
    'NORMAL_GROWTH': [
        '냠냠! "{goal}" 덕분에 오늘도 쑥 자랐어!',
        '"{goal}" 먹고 깃털이 반짝거려!',
        '꽥! "{goal}" 영양분으로 힘이 났어!',
    ],
    'LEVEL_UP': [
        '우와! "{goal}" 먹고 한 단계 진화했어!',
        '"{goal}"의 힘으로 레벨 업 완료!',
        '짠! "{goal}" 덕분에 더 멋진 오리가 됐어!',
    ],
    'SULKY_ENTER': [
        '"{goal}" 냄새는 좋았는데... 나 조금 삐졌어.',
        '"{goal}" 기다렸는데 늦었어. 흥이야!',
        '"{goal}" 먹고 싶었는데 타이밍이 아쉬웠어.',
    ],
    'RUNAWAY_ENTER': [
        '"{goal}"이 너무 그리워서 잠깐 멀리 갔다 올게...',
        '"{goal}" 신호를 못 받아서 집을 나왔어.',
        '"{goal}" 없이는 허전해서 가출 모드야.',
    ],
    'SULKY_RECOVER': [
        '"{goal}"로 달래줘서 기분이 풀렸어!',
        '"{goal}" 먹고 다시 방긋 오리 모드!',
        '"{goal}" 덕분에 다시 같이 걷자!',
    ],
    'RUNAWAY_RECOVER': [
        '"{goal}" 냄새 맡고 집으로 돌아왔어!',
        '"{goal}" 보고 길을 찾아 돌아왔지!',
        '"{goal}" 덕분에 다시 네 곁으로 꽥!',
    ],
    'DONE': [
        '"{goal}"까지 완주! 나 이제 졸업 오리야!',
        '"{goal}" 전부 먹고 최고의 오리로 졸업했어!',
        '"{goal}"의 여정 끝! 정말 대단해!',
    ],
}


def extract_goal_snippet(goal_text: str, max_len: int = 14) -> str:
    """목표 문자열을 대사에 넣기 좋은 짧은 스니펫으로 정제한다."""
    text = (goal_text or '').strip()
    if not text:
        return DEFAULT_GOAL_SNIPPET

    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'<[@#&]!?(\d+)>', ' ', text)
    text = text.replace('`', ' ')
    text = re.sub(r'\s+', ' ', text).strip(' "\'.,!?:;')

    if not text:
        return DEFAULT_GOAL_SNIPPET

    if max_len > 0 and len(text) > max_len:
        text = text[:max_len].rstrip() + '...'

    return text or DEFAULT_GOAL_SNIPPET


def pick_duck_line(context: str, goal_text: str, previous_line: str = None) -> str:
    """컨텍스트 기반 오리 대사를 선택한다."""
    resolved_context = context if context in VOICE_TEMPLATES else DEFAULT_CONTEXT
    goal = extract_goal_snippet(goal_text)

    templates = VOICE_TEMPLATES.get(resolved_context, VOICE_TEMPLATES[DEFAULT_CONTEXT])
    candidates = [template.format(goal=goal) for template in templates]
    if not candidates:
        return f'냠냠! "{goal}" 먹고 힘이 났어!'

    if previous_line and len(candidates) > 1:
        filtered = [line for line in candidates if line != previous_line]
        if filtered:
            candidates = filtered

    return random.choice(candidates)
