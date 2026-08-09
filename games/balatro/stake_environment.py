from games.balatro.environment import BalatroEnvironment
from games.balatro.decks import BASE_DECK, BalatroDeck
from games.balatro.stakes import WHITE_STAKE, BalatroStake


BASE_ANTE_REQUIREMENTS = {
    1: 300,
    2: 800,
    3: 2000,
    4: 5000,
    5: 11000,
    6: 20000,
    7: 35000,
    8: 50000,
}


class BalatroStakeEnvironment(BalatroEnvironment):

    def __init__(
        self,
        deck: BalatroDeck = BASE_DECK,
        stake: BalatroStake = WHITE_STAKE,
    ):
        self.stake = stake
        super().__init__(deck)
        self._apply_stake_rules()

    def reset(self) -> None:
        super().reset()
        self._apply_stake_rules()

    def _apply_stake_rules(self) -> None:
        self.state.stake_name = self.stake.name
        self.state.discards_remaining = max(
            0,
            self.deck.starting_discards + self.stake.discard_modifier
        )
        self._apply_stake_blind_requirement()

    def _apply_stake_blind_requirement(self) -> None:
        base_requirement = BASE_ANTE_REQUIREMENTS.get(
            self.state.ante,
            50000 * (2 ** (self.state.ante - 8))
        )
        requirement = self.stake.requirement_for_ante(
            self.state.ante,
            base_requirement
        )

        if self.state.round == 2:
            requirement = int(requirement * 1.5)
        elif self.state.round == 3:
            requirement *= 2

        self.state.blind_requirement = requirement

    def _setup_blind(self) -> None:
        super()._setup_blind()
        self._apply_stake_blind_requirement()

    def copy(self):
        new_environment = super().copy()
        new_environment.__class__ = BalatroStakeEnvironment
        new_environment.stake = self.stake
        return new_environment
