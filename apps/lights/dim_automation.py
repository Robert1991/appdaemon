import appdaemon.plugins.hass.hassapi as hass
import appdaemon.adbase as ad
import threading
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


class DimLights2(ActivityBasedLightControl):
    hass_utils = None

    light_sensor_observer = None
    light_turn_off_listener = None
    light_adjustment_event_listener = None

    current_light_sensor_state = None
    current_threshold_state = None
    turned_off_lights = set()
    fully_turned_on_lights = set()

    terminating = False
    adjusting = False

    adjustment_thread = None

    def initialize(self):
        super().initialize()
        self.hass_utils = self.get_app('hass_utils')

        # self.light_adjustment_event_listener = self.listen_event(self.adjust_light_brightness, "ADJUSTMENT_NEEDED",
        #                                                          entity=self.args["light_group"])

        self.light_turn_off_listener = self.listen_state(self.turn_off_event,
                                                         self.args["light_group"], new="off")

        self.listen_state(self.check_for_light_adjustment,
                          self.args["light_sensor_control"]["light_intensity_toggle_threshold"])
        self.listen_state(self.check_for_light_adjustment,
                          self.args["dim_automation"]["light_turn_off_boundary_brightness"])

    def turn_on_event(self, entity, attribute, old, new, kwargs):
        if super().turn_on_event(entity, attribute, old, new, kwargs):
            self.turned_off_lights = set()
            self.fully_turned_on_lights = set()
            self.check_for_light_adjustment(entity, None, None, new, None)

    def turn_off_event(self, entity, attribute, old, new, kwargs):
        self.turn_off_entity(kwargs)

    async def turn_off_entity(self, kwargs):
        self.cancel_listen_to_light_sensor()
        self.log("terminate")
        self.terminating = True
        self.turned_off_lights = set()
        self.fully_turned_on_lights = set()

        # self.cancel_listen_state(self.light_turn_off_listener)

        if self.adjustment_thread:
            # self.adjustment_thread.join()
            # while not self.adjustment_thread.done():
            self.log("waiting for thread ending")
            await self.adjustment_thread
            self.log("thread ended")
            self.adjustment_thread = None

        while self.get_state(self.args["light_group"]) == "on":
            self.turn_off(self.args["light_group"])
            self.log("turing off")

        self.light_turn_off_listener = self.listen_state(self.turn_off_event,
                                                         self.args["light_group"], new="off")
        self.terminating = False

    async def check_for_light_adjustment(self, entity, attribute, old, new, kwargs):
        light_adjustment_needed = await self.run_in_executor(self.light_adjustment_is_needed, entity, new)

        if light_adjustment_needed:
            if not self.adjustment_thread:
                self.log("starting new adjustment")
                self.cancel_listen_to_light_sensor()

                self.adjustment_thread = self.run_in_executor(
                    self.adjust_light_brightness2, lambda: self.terminating)
                # self.adjustment_thread = self.create_task(
                #     self.adjust_light_brightness2(lambda: self.terminating))
            else:
                await self.adjustment_thread
                self.adjustment_thread = None
        else:
            self.log("no light adjustment needed")
            self.listen_to_light_sensor()

    def adjust_light_brightness2(self, stop_function):
        lights_in_group = self.get_light_to_control_from_light_group()
        light_turn_out_boundary = self.hass_utils.read_state_as_float(
            self.args["dim_automation"]["light_turn_off_boundary_brightness"])

        while not stop_function() \
                and self.light_adjustment_is_needed(None, None) \
                and len(lights_in_group) > 0 \
                and (len(self.fully_turned_on_lights) + len(self.turned_off_lights)) < len(lights_in_group):
            for light in lights_in_group:
                if stop_function():
                    self.log("terminated loop")
                    break
                new_light_brightness = self.calculate_new_light_brightness(
                    light)
                if new_light_brightness > light_turn_out_boundary and new_light_brightness < 255:
                    self.log("adjusting " + light + " " +
                             " to brightness " + str(new_light_brightness)

                             # , level="DEBUG"

                             )
                    if not stop_function():
                        self.turn_on(light, brightness=new_light_brightness
                                     # ,
                                     # transition=self.args["dim_automation"]["dim_time_out"]

                                     )
                    if light in self.fully_turned_on_lights:
                        self.fully_turned_on_lights.remove(light)
                    if light in self.turned_off_lights:
                        self.turned_off_lights.remove(light)
                elif new_light_brightness >= 255.0:
                    if light not in self.fully_turned_on_lights:
                        self.fully_turned_on_lights.add(light)
                        self.log("adjusting " + light + " " +
                                 " to brightness " + str(255.0))
                        if not stop_function():
                            self.turn_on(light, brightness=255.0,
                                         transition=self.args["dim_automation"]["dim_time_out"])
                elif light not in self.turned_off_lights:
                    if new_light_brightness <= light_turn_out_boundary:
                        self.turned_off_lights.add(light)
                        self.turn_off(light)
        self.log("adjustment completed")

    def calculate_new_light_brightness(self, light_entity_id):
        current_light_state = self.get_state(light_entity_id, attribute="all")
        step_size = self.hass_utils.read_state_as_float(
            self.args["dim_automation"]["light_turn_off_step_size"])
        if current_light_state["state"] == "on":
            if (self.read_current_sensor_state_if_none() - self.read_current_threshold_state_if_none()) > 0:
                return float(current_light_state["attributes"]["brightness"] - step_size)
            else:
                return float(current_light_state["attributes"]["brightness"] + step_size)
        return step_size + 1

    def light_adjustment_is_needed(self, entity, new_state):
        if self.get_state(self.args["dim_automation"]["constrain_input_boolean"]) == 'on':
            self.read_current_threshold_state()

            if entity == self.args["light_sensor_control"]["light_sensor"]:
                self.current_light_sensor_state = float(new_state)
            else:
                self.read_current_sensor_state()
            return abs(self.current_light_sensor_state - self.current_threshold_state) \
                >= self.args["dim_automation"]["toggle_delta"]
        return False

    def get_light_to_control_from_light_group(self):
        lights_in_group = self.get_state(
            self.args["light_group"], attribute="entity_id")
        to_be_controlled = []
        for light in lights_in_group:
            light_state = self.get_state(light, attribute="all")
            if light_state["state"] == "on" and "brightness" in light_state["attributes"]:
                to_be_controlled.append(light)
        return to_be_controlled

    def read_current_sensor_state_if_none(self):
        if not self.current_light_sensor_state:
            self.read_current_sensor_state()
        return self.current_light_sensor_state

    def read_current_threshold_state_if_none(self):
        if not self.current_threshold_state:
            self.read_current_threshold_state()
        return self.current_threshold_state

    def read_current_threshold_state(self):
        current_threshold_state = self.hass_utils.read_state_as_float(
            self.args["light_sensor_control"]["light_intensity_toggle_threshold"])
        if not current_threshold_state:
            self.log(
                "Terminated light control: error reading threshold or sensor values")
            return False
        self.current_threshold_state = current_threshold_state
        return True

    def read_current_sensor_state(self):
        current_light_sensor_state = self.hass_utils.read_state_as_float(
            self.args["light_sensor_control"]["light_sensor"])
        if not current_light_sensor_state:
            self.log(
                "Terminated light control: error reading threshold or sensor values")
            return False
        self.current_light_sensor_state = current_light_sensor_state
        return True

    def listen_to_light_sensor(self):
        if not self.light_sensor_observer:
            self.light_sensor_observer = self.listen_state(
                self.check_for_light_adjustment, self.args["light_sensor_control"]["light_sensor"])

    def cancel_listen_to_light_sensor(self):
        if self.light_sensor_observer:
            self.cancel_listen_state(self.light_sensor_observer)
            self.light_sensor_observer = None


class DimLights(hass.Hass):
    is_running = False

    light_sensor_observer = None

    current_light_sensor_state = None
    current_threshold_state = None

    turned_off_lights = set()
    fully_turned_on_lights = set()

    def initialize(self):
        self.listen_event(self.light_adjustment_event, "ADJUSTMENT_NEEDED",
                          entity=self.args["light_group"])
        self.light_sensor_observer = self.listen_state(self.toggle_event,
                                                       self.args["light_sensor"])
        self.listen_state(self.toggle_event,
                          self.args["light_intensity_toggle_threshold"])
        self.listen_state(self.toggle_event,
                          self.args["constrain_input_boolean"])
        self.listen_state(self.toggle_event,
                          self.args["light_turn_off_boundary_brightness"])
        self.listen_state(self.terminate_dim_control,
                          self.args["light_group"], new="off")

    def light_adjustment_event(self, event_name, attributes, trigger):
        self.toggle_event(self.args["light_sensor"], attributes, None,
                          attributes["new_sensor_value"], None)

    def toggle_event(self, entity, attribute, old, new, kwargs):
        if self.light_adjustment_is_needed(entity, new):
            lights_in_group = self.get_light_to_control_from_light_group()
            light_turn_out_boundary = self.read_state_as_float(
                self.args['light_turn_off_boundary_brightness'])

            for light in lights_in_group:
                if light in self.turned_off_lights or light in self.fully_turned_on_lights:
                    continue
                new_light_brightness = self.calculate_new_light_brightness(
                    light)
                self.log("adjusting " + light + " " +
                         " to brightness " + str(new_light_brightness), level="DEBUG")
                if new_light_brightness > light_turn_out_boundary and new_light_brightness < 255:
                    self.turn_on(light, brightness=new_light_brightness,
                                 transition=self.args["dim_time_out"])
                    if light in self.fully_turned_on_lights:
                        self.fully_turned_on_lights.remove(light)
                    if light in self.turned_off_lights:
                        self.turned_off_lights.remove(light)
                elif new_light_brightness >= 255.0:
                    if light not in self.fully_turned_on_lights:
                        self.fully_turned_on_lights.add(light)
                        self.turn_on(light, brightness=255.0,
                                     transition=self.args["dim_time_out"])
                elif light not in self.turned_off_lights:
                    if new_light_brightness <= light_turn_out_boundary:
                        self.turned_off_lights.add(light)
                        self.turn_off(light)
            sleep(1)
            if self.light_adjustment_is_needed(None, None):
                self.cancel_listen_to_light_sensor()
                self.fire_event(
                    "ADJUSTMENT_NEEDED", entity=self.args["light_group"], new_sensor_value=self.current_light_sensor_state)
            else:
                self.listen_to_light_sensor()
        else:
            self.listen_to_light_sensor()

    def light_adjustment_is_needed(self, entity, new_state):
        if self.get_state(self.args["light_group"]) == "on" and \
           self.get_state(self.args["constrain_input_boolean"]) == 'on':
            self.read_current_threshold_state()

            if entity == self.args["light_sensor"]:
                self.current_light_sensor_state = float(new_state)
            else:
                self.read_current_sensor_state()
            return abs(self.current_light_sensor_state - self.current_threshold_state) \
                >= self.args["toggle_delta"]
        return False

    def read_current_threshold_state(self):
        current_threshold_state = self.read_state_as_float(
            self.args["light_intensity_toggle_threshold"])
        if not current_threshold_state:
            self.log(
                "Terminated light control: error reading threshold or sensor values")
            return False
        self.current_threshold_state = current_threshold_state
        return True

    def read_current_sensor_state(self):
        current_light_sensor_state = self.read_state_as_float(
            self.args["light_sensor"])
        if not current_light_sensor_state:
            self.log(
                "Terminated light control: error reading threshold or sensor values")
            return False
        self.current_light_sensor_state = current_light_sensor_state
        return True

    def terminate_dim_control(self, entity, attribute, old, new, kwargs):
        self.log("received turn off event")
        self.turned_off_lights = set()
        self.fully_turned_on_lights = set()
        self.listen_to_light_sensor()

    def cancel_listen_to_light_sensor(self):
        if self.light_sensor_observer:
            self.cancel_listen_state(self.light_sensor_observer)
            self.light_sensor_observer = None

    def listen_to_light_sensor(self):
        if not self.light_sensor_observer:
            self.light_sensor_observer = self.listen_state(
                self.toggle_event, self.args["light_sensor"])

    def get_light_to_control_from_light_group(self):
        lights_in_group = self.get_state(
            self.args["light_group"], attribute="entity_id")
        to_be_controlled = []
        for light in lights_in_group:
            light_state = self.get_state(light, attribute="all")
            if light_state["state"] == "on" and "brightness" in light_state["attributes"]:
                to_be_controlled.append(light)
        return to_be_controlled

    def calculate_new_light_brightness(self, light_entity_id):
        current_light_state = self.get_state(light_entity_id, attribute="all")
        step_size = self.read_state_as_float(
            self.args["light_turn_off_step_size"])
        if current_light_state["state"] == "on":
            if (self.current_light_sensor_state - self.current_threshold_state) > 0:
                return float(current_light_state["attributes"]["brightness"] - step_size)
            else:
                return float(current_light_state["attributes"]["brightness"] + step_size)
        return step_size + 1

    def read_state_as_float(self, entity):
        try:
            return float(self.get_state(entity))
        except ValueError:
            self.log("value error while converting state of " +
                     entity + " to float")
            return None
