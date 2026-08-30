from types import SimpleNamespace

from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner


class _Evaluator:
    def __init__(self):
        self.action_generator = object()
        self._outer_d1_projection_cache = {}

    @staticmethod
    def _action_key(action):
        return "candidate"

    def _ensure_outer_d1_cache(self, state):
        self._outer_d1_projection_cache = {
            "candidate": SimpleNamespace(
                clear_probability=0.75,
                expected_hand_score=321.0,
                hand_score=300,
            )
        }

    def _hand_for_cards(self, state, cards):
        raise AssertionError("fresh outer D1 cache should avoid literal fallback scoring")


class _Action:
    cards = (object(), object())


def test_root_priority_reads_cache_after_ensure_cache_replaces_it():
    evaluator = _Evaluator()
    planner = LiveBlindClearPlanner(evaluator)

    priority = planner._root_play_priority(SimpleNamespace(), _Action())

    assert priority == (0.75, 321.0, 300, -2)
