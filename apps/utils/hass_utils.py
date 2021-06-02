import appdaemon.plugins.hass.hassapi as hass


class HassUtils(hass.Hass):

    def initialize(self):
        pass

    def read_state_as_float(self, entity):
        try:
            return float(self.get_state(entity))
        except ValueError:
            self.log("value error while converting state of " +
                     entity + " to float")
            return None
