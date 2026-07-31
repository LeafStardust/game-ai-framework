class Agent:
    """
    Base AI agent.

    An agent observes a state,
    evaluates available actions,
    and selects an action.
    """

    def __init__(self, decision_engine):
        self.decision_engine = decision_engine


    def act(self, state, actions):

        return self.decision_engine.choose_action(
            state,
            actions
        )