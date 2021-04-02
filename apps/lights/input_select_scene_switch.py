import appdaemon.plugins.hass.hassapi as hass
from dateutil import parser


class InputSelectSceneSwitch(hass.Hass):
    scene_utils = None

    def initialize(self):
        self.scene_utils = self.get_app('scene_utils')
        self.listen_state(self.switch_scene,
                          self.args["observed_input_select"])

    def switch_scene(self, entity, attribute, oldSceneName, newSceneName, kwargs):
        self.scene_utils.turn_on_current_scene_by_name(self.args["scene_prefix"], newSceneName)
        for to_be_adapted in self.args["adapted_input_selects"]:
            self.log(to_be_adapted)
            self.select_option(to_be_adapted, newSceneName)
