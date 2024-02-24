from client import LightPutRequest, LightGroup
from registry import Action

EMPTY_ACTION = Action(key_paragraphs=[""], light_action=None)
ALL_LIGHTS_OUT = Action(key_paragraphs=["all info out", "all info off"],
                        light_action=LightPutRequest(LightGroup.ALL, on=False))
ALL_LIGHTS_ON = Action(key_paragraphs=["all info out", "all info off"],
                       light_action=LightPutRequest(LightGroup.ALL, on=True))
