import appdaemon.plugins.hass.hassapi as hass


class HassUtils(hass.Hass):

    def initialize(self):
        pass

    def read_state_as_float_from(self, entity):
        return float(self.get_state(entity))
