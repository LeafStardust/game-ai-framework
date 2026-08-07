import random

from games.balatro.blinds.standard import (
    small_blind,
    big_blind,
    boss_blind_requirement
)

from games.balatro.blinds.boss import (
    TheHook,
    TheWall
)


class BlindManager:

    def __init__(self):

        self.boss_pool = [
            TheHook,
            TheWall
        ]

        self.rng = random.Random()


    def get_blind(
        self,
        blind_type: str,
        ante: int
    ):

        if blind_type == "SMALL":

            return small_blind(
                ante
            )


        if blind_type == "BIG":

            return big_blind(
                ante
            )


        return self.get_boss_blind(
            ante
        )


    def get_boss_blind(
        self,
        ante: int
    ):

        boss = self.rng.choice(
            self.boss_pool
        )

        return boss(
            requirement=boss_blind_requirement(
                ante
            )
        )