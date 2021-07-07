import appdaemon.plugins.hass.hassapi as hass
from time import sleep


class TurnOffAutomation(hass.Hass):
    current_timer = None

    def initialize(self):
        self.listen_state(self.start_turn_off_timer,
                          self.args["observed_activity_sensor"], new="off")
        self.listen_state(self.stop_turn_off_timer,
                          self.args["observed_activity_sensor"], new="on")
        self.listen_state(self.stop_turn_off_timer,
                          self.args["entity"], new="off")

    def start_turn_off_timer(self, entity, attribute, old, new, kwargs):
        self.log("Starting turn off timer for %s",
                 self.args["entity"], level="DEBUG")
        self.cancel_timer_if_running()
        timeout = self.calculate_timeout()
        self.current_timer = self.run_in(
            self.turn_off_entity, int(timeout))

    def stop_turn_off_timer(self, entity, attribute, old, new, kwargs):
        self.log("Stopping turn off timer for %s",
                 self.args["entity"], level="DEBUG")
        self.cancel_timer_if_running()

    def turn_off_entity(self, kwargs):
        entity = self.args["entity"]
        self.turn_off(entity)
        self.fire_event("TURN_OFF", entity=entity)
        self.current_timer = None

    def calculate_timeout(self):
        unit = self.get_state(
            self.args["turn_off_timeout"], attribute="unit_of_measurement")
        timeout = int(float(self.get_state(self.args["turn_off_timeout"])))
        if unit and unit != "s":
            if unit == "min":
                return timeout * 60
            if unit == "h":
                return timeout * 60 * 60
        return timeout

    def cancel_timer_if_running(self):
        if self.current_timer:
            self.cancel_timer(self.current_timer)
        self.current_timer = None


class ActivityBasedEntityControl(TurnOffAutomation):
    scene_utils = None
    hass_utils = None

    def initialize(self):
        self.scene_utils = self.get_app('scene_utils')
        self.hass_utils = self.get_app('hass_utils')

        self.listen_state(self.turn_on_event,
                          self.args["observed_activity_sensor"], new="on")
        self.listen_state(self.stop_turn_off_timer,
                          self.args["observed_activity_sensor"], new="on")
        self.listen_state(self.start_turn_off_timer,
                          self.args["observed_activity_sensor"], new="off")

    def turn_on_event(self, entity, attribute, old, new, kwargs):
        # self.log(self.get_state(
        #     self.args["turn_off_timeout"], attribute="unit_of_measurement"))
        if self.read_state_from_input_arg("entity") == "on":
            return False

        if self.entity_needs_to_be_turned_on():
            self.turn_on_entity()
            return True
        return False

    def turn_on_entity(self):
        self.log("Turning on entity " + self.args["entity"], level="DEBUG")
        if "time_based_scene_mode" in self.args:
            time_based_scene_mode_enabled = self.get_state(
                self.args["time_based_scene_mode"]["constrain_input_boolean"])
            if time_based_scene_mode_enabled == "on":
                self.turn_on_scene()
                return
        self.turn_on(self.args["entity"])

    def entity_needs_to_be_turned_on(self):
        if self.check_time_depended_control() and self.check_light_intensity_control():
            return True
        return False

    def turn_on_scene(self):
        self.log("Turning on scene", level="DEBUG")
        self.scene_utils.turn_on_current_scene(
            self.args["time_based_scene_mode"]["scene_group_prefix"],
            self.args["time_based_scene_mode"]["scene_input_select"])

    def check_time_depended_control(self):
        if "time_depended_control" in self.args:
            automation_start_time = self.get_state(
                self.args["time_depended_control"]["automation_start_time"])
            automation_end_time = self.get_state(
                self.args["time_depended_control"]["automation_end_time"])
            time_dependend_control_disabled = self.get_state(
                self.args["time_depended_control"]["enable_time_depended_automation_input"]) == 'off'
            if automation_start_time and automation_end_time:
                return self.now_is_between(automation_start_time, automation_end_time) or time_dependend_control_disabled
        return True

    def check_light_intensity_control(self):
        if "threshold_control" in self.args:
            light_sensor_state = self.hass_utils.read_state_as_float(
                self.args["threshold_control"]["sensor"])
            light_threshold = self.hass_utils.read_state_as_float(
                self.args["threshold_control"]["threshold"])
            if light_sensor_state <= light_threshold:
                return True
            return False
        return True

    def read_state_from_input_arg(self, input_arg):
        if input_arg in self.args:
            return self.get_state(self.args[input_arg])
        return None


class NoActivityToggleAutomation(hass.Hass):
    current_timer = None

    def initialize(self):
        self.listen_state(self.start_toggle_timer,
                          self.args["observed_activity_sensor"], new="off")
        self.listen_state(self.stop_toggle_timer,
                          self.args["observed_activity_sensor"], new="on")
        self.listen_state(self.stop_toggle_timer,
                          self.args["device_used_sensor"], new="off")

    def start_toggle_timer(self, entity, attribute, old, new, kwargs):
        timeout = int(float(self.get_state(self.args["turn_off_timeout"])))
        self.current_timer = self.run_in(self.toggle_switch, int(timeout))

    def stop_toggle_timer(self, entity, attribute, old, new, kwargs):
        self.cancel_timer(self.current_timer)

    def toggle_switch(self, kwargs):
        self.toggle(self.args["toggle_switch"])
