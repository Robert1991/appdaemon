import appdaemon.plugins.hass.hassapi as hass


class ActivityBasedLightSwitch(hass.Hass):
    def initialize(self):
        self.listen_state(self.turn_on_lights,
                          self.args["observed_activity_sensor"], new="on")

    def turn_on_lights(self, entity, attribute, old, new, kwargs):
        if self.get_state(self.args["light_group"]) == "off":
            self.turn_on(self.args["light_group"])


class TurnOnAutomation(hass.Hass):
    scene_utils = None
    hass_utils = None

    def initialize(self):
        self.scene_utils = self.get_app('scene_utils')
        self.hass_utils = self.get_app('hass_utils')
        self.listen_state(self.turn_on_lights,
                          self.args["observed_activity_sensor"], new="on")

    def turn_on_lights(self, entity, attribute, old, new, kwargs):
        if self.read_state_from_input_arg("light_group") == "on":
            return
        automation_start_time = self.read_state_from_input_arg(
            "light_automation_start_time")
        automation_end_time = self.read_state_from_input_arg(
            "light_automation_end_time")
        time_dependend_control_disabled = self.read_state_from_input_arg(
            'enable_time_depended_automation_input') == 'off'
        if self.now_is_between(automation_start_time, automation_end_time) or time_dependend_control_disabled:
            light_sensor_state = self.hass_utils.read_state_as_float(
                self.args["light_sensor"])
            light_threshold = self.hass_utils.read_state_as_float(
                self.args["light_intensity_toggle_threshold"])
            if light_sensor_state <= light_threshold:
                if self.read_state_from_input_arg("enable_automatic_scene_mode") == "on":
                    self.turn_on_scene(light_threshold, light_sensor_state)
                else:
                    self.log("Turning on light", level="DEBUG")
                    self.turn_on(self.args["light_group"])
                self.fire_event("TURN_ON", entity=self.args["light_group"])

    def turn_on_scene(self, light_threshold, light_sensor_state):
        self.log("Turning on scene", level="DEBUG")
        self.scene_utils.turn_on_current_scene(
            self.args["scene_group_prefix"], self.args["scene_input_select"])

    def read_state_from_input_arg(self, input_arg):
        return self.get_state(self.args[input_arg])


class TurnOnAutomationWithSceneTransition(TurnOnAutomation):
    def turn_on_scene(self, light_threshold, light_sensor_state):
        ratio = (light_threshold - light_sensor_state) / light_threshold
        self.log("Turning on scene with ratio: " + str(ratio), level="DEBUG")
        self.scene_utils.turn_on_current_scene_with_transition(
            self.args["scene_group_prefix"], self.args["scene_input_select"], ratio)
