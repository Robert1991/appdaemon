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
                          self.args["light_group"], new="off")

    def start_turn_off_timer(self, entity, attribute, old, new, kwargs):
        self.log("Starting turn off timer for %s",
                 self.args["light_group"], level="DEBUG")
        self.cancel_timer_if_running()
        timeout = int(float(self.get_state(self.args["turn_off_timeout"])))
        self.current_timer = self.run_in(
            self.turn_off_entity, int(timeout))

    def stop_turn_off_timer(self, entity, attribute, old, new, kwargs):
        self.log("Stopping turn off timer for %s",
                 self.args["light_group"], level="DEBUG")
        self.cancel_timer_if_running()

    def turn_off_entity(self, kwargs):
        entity = self.args["light_group"]
        self.turn_off(entity)
        self.fire_event("TURN_OFF", entity=entity)
        self.current_timer = None

    def cancel_timer_if_running(self):
        if self.current_timer:
            self.cancel_timer(self.current_timer)
        self.current_timer = None


class ActivityBasedLightControl(TurnOffAutomation):
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
        if self.read_state_from_input_arg("light_group") == "on":
            return False

        if self.light_needs_to_be_turned_on():
            if "light_sensor_control" in self.args:
                light_sensor_state = self.hass_utils.read_state_as_float(
                    self.args["light_sensor_control"]["light_sensor"])
                light_threshold = self.hass_utils.read_state_as_float(
                    self.args["light_sensor_control"]["light_intensity_toggle_threshold"])
                if light_sensor_state <= light_threshold:
                    self.turn_on_light_group()
                    return True
                return False
            else:
                self.turn_on_light_group()
                return True
        return False

    def turn_on_light_group(self):
        self.log("Turning on light", level="DEBUG")
        if "time_based_scene_mode" in self.args:
            time_based_scene_mode_enabled = self.get_state(
                self.args["time_based_scene_mode"]["constrain_input_boolean"])
            if time_based_scene_mode_enabled == "on":
                self.turn_on_scene()
                return
        self.turn_on(self.args["light_group"])

    def light_needs_to_be_turned_on(self):
        automation_start_time = self.read_state_from_input_arg(
            "light_automation_start_time")
        automation_end_time = self.read_state_from_input_arg(
            "light_automation_end_time")
        time_dependend_control_disabled = self.read_state_from_input_arg(
            'enable_time_depended_automation_input') == 'off'
        if automation_start_time and automation_end_time:
            return self.now_is_between(automation_start_time, automation_end_time) or time_dependend_control_disabled
        return True

    def turn_on_scene(self):
        self.log("Turning on scene", level="DEBUG")
        self.scene_utils.turn_on_current_scene(
            self.args["time_based_scene_mode"]["scene_group_prefix"],
            self.args["time_based_scene_mode"]["scene_input_select"])

    def read_state_from_input_arg(self, input_arg):
        if input_arg in self.args:
            return self.get_state(self.args[input_arg])
        return None
class DimLights(hass.Hass):
    is_running = False
    terminated = False

    current_light_sensor_state = None
    current_threshold_state = None

    def initialize(self):
        self.listen_state(self.toggle_event,
                          self.args["light_group"], new="on")
        self.listen_state(self.toggle_event,
                          self.args["light_sensor"])
        self.listen_state(self.toggle_event,
                          self.args["light_intensity_toggle_threshold"])
        self.listen_state(self.toggle_event,
                          self.args["constrain_input_boolean"])
        self.listen_state(self.toggle_event,
                          self.args["light_turn_off_boundary_brightness"])
        self.listen_event(self.terminate_dim_control,
                          "TURN_OFF", entity=self.args["light_group"])

    def toggle_event(self, entity, attribute, old, new, kwargs):
        if not self.check_if_light_needs_to_be_dimmed(entity):
            return
        self.is_running = True

        lights_in_group = self.get_light_to_control_from_light_group()
        light_turn_out_boundary = self.read_state_as_float(
            self.args['light_turn_off_boundary_brightness'])

        turned_off_lights = set()
        while len(turned_off_lights) < len(lights_in_group) and self.light_adjustment_is_needed():
            if self.terminated:
                self.log(
                    "Terminated light control: received turn off event", level="DEBUG")
                self.turn_off(self.args["light_group"])
                self.terminated = False
                break

            for light in lights_in_group:
                if light in turned_off_lights:
                    continue
                new_light_brightness = self.calculate_new_light_brightness(
                    light)
                self.log("adjusting " + light + " " +
                         " to brightness " + str(new_light_brightness), level="DEBUG")
                if new_light_brightness:
                    if new_light_brightness > light_turn_out_boundary and new_light_brightness <= 255:
                        self.turn_on(light, brightness=new_light_brightness,
                                     transition=self.args["dim_time_out"])
                    elif new_light_brightness >= 255.0:
                        turned_off_lights.add(light)
                        self.turn_on(light, brightness=255.0,
                                     transition=self.args["dim_time_out"])
                    else:
                        turned_off_lights.add(light)
                        if new_light_brightness <= light_turn_out_boundary:
                            self.turn_off(light)
                else:
                    turned_off_lights.add(light)
            sleep(self.args["dim_time_out"])

        self.is_running = False
        self.terminated = False

    def read_current_sensor_and_threshold_state(self):
        current_light_sensor_state = self.read_state_as_float(
            self.args["light_sensor"])
        current_threshold_state = self.read_state_as_float(
            self.args["light_intensity_toggle_threshold"])
        if not current_light_sensor_state or not current_threshold_state:
            self.log(
                "Terminated light control: error reading threshold or sensor values")
            return False
        self.current_threshold_state = current_threshold_state
        self.current_light_sensor_state = current_light_sensor_state
        return True

    def light_adjustment_is_needed(self):
        if self.get_state(self.args["constrain_input_boolean"]) == 'on':
            if self.read_current_sensor_and_threshold_state():
                return abs(self.current_light_sensor_state - self.current_threshold_state) \
                    >= self.args["toggle_delta"]
        return False

    def terminate_dim_control(self, entity, attribute, old):
        self.log("received turn off event")
        if self.is_running:
            self.terminated = True

    def get_light_to_control_from_light_group(self):
        lights_in_group = self.get_state(
            self.args["light_group"], attribute="entity_id")
        to_be_controlled = []
        for light in lights_in_group:
            if self.get_state(light) == "on":
                to_be_controlled.append(light)
        return to_be_controlled

    def check_if_light_needs_to_be_dimmed(self, entity):
        if self.is_running:
            return False
        light_group_is_on = self.get_state(self.args["light_group"]) == "on"
        return light_group_is_on

    def calculate_new_light_brightness(self, light_entity_id):
        current_light_brightness = self.get_state(
            light_entity_id, attribute="brightness")
        if current_light_brightness:
            step_size = self.read_state_as_float(
                self.args["light_turn_off_step_size"])
            if (self.current_light_sensor_state - self.current_threshold_state) > 0:
                return float(current_light_brightness - step_size)
            else:
                return float(current_light_brightness + step_size)
        return None

    def read_state_as_float(self, entity):
        try:
            return float(self.get_state(entity))
        except ValueError:
            self.log("value error while converting state of " +
                     entity + " to float")
            return None
