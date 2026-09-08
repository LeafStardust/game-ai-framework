from agents.balatro_deck_agent import (
    BalatroDeckAgent,
    BalatroDeckAgentProfile,
)


class RedDeckAgent(BalatroDeckAgent):

    def __init__(
        self,
        stake_name: str = "WHITE"
    ):
        super().__init__(
            BalatroDeckAgentProfile(
                deck_name="RED",
                stake_name=stake_name,
                search_simulations=8
            )
        )
