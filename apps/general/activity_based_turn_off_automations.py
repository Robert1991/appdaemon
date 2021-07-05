import appdaemon.plugins.hass.hassapi as hass


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
        timeout = int(float(self.get_state(self.args["turn_off_timeout"])))
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
        self.cancel_timer_if_running()

    def cancel_timer_if_running(self):
        if self.current_timer:
            self.cancel_timer(self.current_timer)
        self.current_timer = None


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
