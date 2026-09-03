"""
Kaggriculture submission entry point.

Kaggle unpacks your files to /kaggle_simulations/agent/ and calls `agent(obs)`
every turn. Keep this file thin -- real logic lives in strategy/.
"""

from strategy.planner import decide


def agent(obs):
    return decide(obs)
