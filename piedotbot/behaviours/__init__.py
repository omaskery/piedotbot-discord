

from . import activity_log
from . import dice_roll
from . import greet_on_join
from . import ping_pong


def build_behaviours():
    return [
        dice_roll.Behaviour(),
        greet_on_join.Behaviour(),
        activity_log.Behaviour(),
        ping_pong.Behaviour(),
    ]
