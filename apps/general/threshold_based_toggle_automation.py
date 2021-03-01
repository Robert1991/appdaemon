import appdaemon.plugins.hass.hassapi as hass


class ThresholdBasedToggleAutomation(hass.Hass):
    def initialize(self):
        self.listen_state(self.toggle_if_necessary,
                          self.args["observed_sensor"])
        self.listen_state(self.toggle_if_necessary,
                          self.args["threshold_input_number"])

    def toggle_if_necessary(self, entity, attribute, old, new, kwargs):
        current_sensor_value = self.read_state_as_float_from_input_arg(
            "observed_sensor")
        current_threshold_value = self.read_state_as_float_from_input_arg(
            "threshold_input_number")
        if self.args["act_on_over_threshold"]:
            self.toggle_state(current_sensor_value > current_threshold_value)
        else:
            self.toggle_state(current_sensor_value < current_threshold_value)

    def toggle_state(self, condition_met):
        if self.args["toggle_to_on"]:
            if condition_met:
                self.turn_on(self.args["switch"])
            else:
                self.turn_off(self.args["switch"])
        else:
            if condition_met:
                self.turn_off(self.args["switch"])
            else:
                self.turn_on(self.args["switch"])

    def read_state_as_float_from_input_arg(self, input_arg):
        return float(self.read_state_from_input_arg(input_arg))

    def read_state_from_input_arg(self, input_arg):
        return self.get_state(self.args[input_arg])


class ThresholdBasedToggleAutomationWithDelay(ThresholdBasedToggleAutomation):
    state_change_timer_condition_met = None
    state_change_timer_condition_not_met = None

    def toggle_state(self, condition_met):
        toggle_to_on = True if self.args["toggle_to_on"] else False
        if condition_met:
            self.start_condition_met_timer_if_necessary(toggle_to_on)
        else:
            self.start_condition_not_met_timer_if_necessary(toggle_to_on)

    def start_condition_met_timer_if_necessary(self, state_transition_to_on):
        target_state = "on" if state_transition_to_on else "off"
        opposite_state = "off" if state_transition_to_on else "on"
        
        if self.get_state(self.args["switch"]) == opposite_state:
            if self.state_change_timer_condition_not_met:
                self.cancel_timer(
                    self.state_change_timer_condition_not_met)
                self.state_change_timer_condition_not_met = None
            if not self.state_change_timer_condition_met:
                delay = int(float(self.get_state(self.args["state_change_delay"])))
                self.state_change_timer_condition_met = self.run_in(self.toggle_switch_to,
                                                                    delay,
                                                                    state=target_state)

    def start_condition_not_met_timer_if_necessary(self, state_transition_to_on):
        target_state = "off" if state_transition_to_on else "on"
        opposite_state = "on" if state_transition_to_on else "off"

        if self.get_state(self.args["switch"]) == opposite_state:
            if self.state_change_timer_condition_met:
                self.cancel_timer(
                    self.state_change_timer_condition_met)
                self.state_change_timer_condition_met = None
            if not self.state_change_timer_condition_not_met:
                delay = int(float(self.get_state(self.args["state_change_delay"])))
                self.state_change_timer_condition_not_met = self.run_in(self.toggle_switch_to,
                                                                        delay,
                                                                        state=target_state)

    def toggle_switch_to(self, input_args):
        if input_args["state"] == "on":
            self.turn_on(self.args["switch"])
        else:
            self.turn_off(self.args["switch"])
