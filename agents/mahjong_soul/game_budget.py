"""Count completed matches observed during this agent run, not rounds/history."""
import argparse


def positive_games(value):
    try:number=int(value)
    except (ValueError,TypeError):raise argparse.ArgumentTypeError("Game count must be a positive integer")
    if number<=0:raise argparse.ArgumentTypeError("Game count must be a positive integer")
    return number


class GameBudget:
    def __init__(self,limit=None):
        self.limit=limit;self.active=set();self.completed=set()

    def observe(self,report):
        state=report.get("state") or {}
        key=(report.get("game_connection"),report.get("game_generation",0))
        if not key[0]:return False
        if state.get("status")=="tracking":self.active.add(key)
        if state.get("status")=="match_ended" and key in self.active:
            self.completed.add(key)
        return self.done

    def can_continue(self,report):
        key=(report.get("game_connection"),report.get("game_generation",0))
        return key in self.completed and not self.done

    @property
    def done(self):return self.limit is not None and len(self.completed)>=self.limit
