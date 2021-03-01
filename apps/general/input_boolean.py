import appdaemon.plugins.hass.hassapi as hass

from dateutil import parser


class DailyReactivationTimer(hass.Hass):
    current_timer_handle = None

    def initialize(self):
        self.listen_state(self.start_timer,
                          self.args["observed_input_datetime"])
        self.listen_state(self.start_timer,
                          self.args["observed_input_boolean"])

    def start_timer(self, entity, attribute, old, new, kwargs):
        time_string = self.get_state(self.args["observed_input_datetime"])
        reactivation_time = parser.parse(time_string)
        timer_callback = self.run_daily(self.reactivate_input_bool,
                                        reactivation_time.time())
        if self.current_timer_handle:
            self.cancel_timer(self.current_timer_handle)
        self.current_timer_handle = timer_callback

    def reactivate_input_bool(self, kwargs):
        self.log("Reactivated: " + str(self.args["observed_input_boolean"]))
        self.turn_on(self.args["observed_input_boolean"])


class ReactivationTimer(hass.Hass):
    current_timer_handle = None

    def initialize(self):
        self.listen_state(self.start_timer,
                          self.args["observed_input_boolean"], new="off")
        self.listen_state(self.stop_timer,
                          self.args["observed_input_boolean"], new="on")

    def start_timer(self, entity, attribute, old, new, kwargs):
        time_string = self.get_state(self.args["reactivation_timeout"])
        timer_interval_datetime = parser.parse(time_string)

        timer_interval_in_seconds = timer_interval_datetime.hour * 60 * 60 + \
            timer_interval_datetime.minute * 60 + timer_interval_datetime.second

        self.current_timer_handle = self.run_in(
            self.reactivate_input_bool, timer_interval_in_seconds)

    def stop_timer(self, entity, attribute, old, new, kwargs):
        self.cancel_timer(self.current_timer_handle)

    def reactivate_input_bool(self, kwargs):
        self.log("Reactivated: " + str(self.args["reactivation_timeout"]))
        self.turn_on(self.args["observed_input_boolean"])
