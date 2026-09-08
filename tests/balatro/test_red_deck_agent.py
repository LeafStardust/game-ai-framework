from agents.balatro_deck_agent import BalatroDeckAgent
from agents.red_deck_agent import RedDeckAgent


def test_red_deck_agent_uses_red_profile():

    agent = RedDeckAgent()

    assert isinstance(agent, BalatroDeckAgent)
    assert agent.profile.deck_name == "RED"
    assert agent.profile.stake_name == "WHITE"
    assert agent.profile.search_simulations == 8


def test_red_deck_agent_accepts_stake_profile():

    agent = RedDeckAgent("GREEN")

    assert agent.profile.stake_name == "GREEN"
