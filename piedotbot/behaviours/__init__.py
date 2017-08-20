

from . import activity_log
from . import dice_roll
from . import greet_on_join
from . import ping_pong
from . import script_behaviour


def build_behaviours():
    return [
        dice_roll.Behaviour(),
        greet_on_join.Behaviour(),
        activity_log.Behaviour(),
        ping_pong.Behaviour(),
        script_behaviour.Behaviour(),
    ]
