from client import LightPutRequest, LightSelector
from registry import Action

ALL: LightSelector = LightSelector(lambda ids: ids)

# ---------- Collection of known actions

ALL_LIGHTS_OUT = Action(key_paragraphs=["all lights out", "all lights off", "make it dark", "the lights off"],
                        light_action=(ALL, LightPutRequest(on=False)))
ALL_LIGHTS_ON = Action(key_paragraphs=["all lights on", "the lights on", "make it bright"],
                       light_action=(ALL, LightPutRequest(on=True)))
