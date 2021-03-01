import appdaemon.plugins.hass.hassapi as hass
from dateutil import parser


class TurnOnOffInterval(hass.Hass):
    current_timer = None
    start_execution_timer = None
    end_execution_timer = None

    initialize_on_creation = True

    def initialize(self):
        self.listen_state(self.initalize_timers,
                          self.args["on_interval_length"])
        self.listen_state(self.initalize_timers,
                          self.args["off_interval_length"])
        self.listen_event(self.initalize_timers, "homeassistant_start")
        if "interval_start" in self.args and "interval_end" in self.args:
            self.listen_state(self.initalize_timers,
                              self.args["interval_start"])
            self.listen_state(self.initalize_timers, self.args["interval_end"])
        if self.initialize_on_creation:
            self.initalize_timers(None, None, None, None, None)
    
    def initalize_timers_on_event(self, entity, attribute, old):
        self.initalize_timers(entity, attribute, old, None, None)

    def initalize_timers(self, entity, attribute, old, new, kwargs):
        self.cancel_timer_if_running(self.current_timer)
        if "interval_start" in self.args and "interval_end" in self.args:
            start_time = self.get_interval_time(self.args["interval_start"])
            end_time = self.get_interval_time(self.args["interval_end"])
            self.log(start_time)
            self.log(end_time)
            if self.now_is_between(str(start_time), str(end_time)):
                self.log("starting on off interval immediatley")
                self.start_execution(None)
            self.cancel_timer_if_running(self.start_execution_timer)
            self.cancel_timer_if_running(self.end_execution_timer)
            self.start_execution_timer = self.run_daily(self.start_execution,
                                                        start_time)
            self.end_execution_timer = self.run_daily(self.cancel_execution,
                                                      end_time,)
        else:
            self.start_execution(None)
        self.log("Successfully started OnOff interval")
    def start_execution(self, input_args):
        self.cancel_timer_if_running(self.current_timer)
        minutes = self.get_minutes_from_input_number(
            self.args["on_interval_length"])
        self.current_timer = self.run_in(self.turn_off_entity, 60 * minutes)
        self.turn_on(self.args["toggled_entity"])

    def cancel_execution(self, input_args):
        self.cancel_timer_if_running(self.current_timer)
        self.turn_off(self.args["toggled_entity"])

    def turn_off_entity(self, input_args):
        self.log("off")
        minutes = self.get_minutes_from_input_number(
            self.args["off_interval_length"])
        self.current_timer = self.run_in(self.turn_on_entity, 60 * minutes)
        self.turn_off(self.args["toggled_entity"])

    def turn_on_entity(self, input_args):
        self.log("on")
        minutes = self.get_minutes_from_input_number(
            self.args["on_interval_length"])
        self.current_timer = self.run_in(self.turn_off_entity, 60 * minutes)
        self.turn_on(self.args["toggled_entity"])

    def get_minutes_from_input_number(self, input_number_entity):
        current = self.get_state(input_number_entity)
        return int(float(current))

    def get_interval_time(self, time_entity):
        time_as_str = self.get_state(time_entity)
        return parser.parse(time_as_str).time()

    def cancel_timer_if_running(self, timer_handle):
        if timer_handle:
            self.cancel_timer(timer_handle)


class TimeBasedToggleAutomation(hass.Hass):
    turn_on_timer = None
    turn_off_timer = None

    initialize_on_creation = True

    def initialize(self):
        self.listen_state(self.initalize_timers,
                          self.args["time_interval_start"])
        self.listen_state(self.initalize_timers,
                          self.args["time_interval_end"])
        self.listen_event(self.initalize_timers_on_event,
                          "homeassistant_start")
        if self.initialize_on_creation:
            self.initalize_timers(None, None, None, None, None)

    def initalize_timers_on_event(self, entity, attribute, old):
        self.initalize_timers(entity, attribute, old, None, None)

    def initalize_timers(self, entity, attribute, old, new, kwargs):
        interval_start_time = self.get_interval_time(
            self.args["time_interval_start"])
        interval_end_time = self.get_interval_time(
            self.args["time_interval_end"])

        self.log("running 'on' daily timer at: " + str(interval_start_time))
        self.turn_on_timer = self.restart_timer(
            self.turn_on_timer, interval_start_time, True)

        self.log("running 'off' daily timer at: " + str(interval_end_time))
        self.turn_off_timer = self.restart_timer(
            self.turn_off_timer, interval_end_time, False)

        self.toggle_entity_if_necessary(interval_start_time, interval_end_time)
        self.log("successfully initialized timebased toggle automation")

    def restart_timer(self, timer_handle, executed_time, toggle_state):
        self.cancel_timer_if_running(timer_handle)
        return self.run_daily(self.toggle, executed_time, toState=toggle_state)

    def toggle_entity_if_necessary(self, interval_start_time, interval_end_time):
        if self.time() < interval_start_time:
            # next day
            if interval_end_time < interval_start_time and self.time() < interval_end_time:
                self.turn_on(self.args["toggled_entity"])
            else:
                self.turn_off(self.args["toggled_entity"])
        elif self.time() > interval_start_time:
            if self.time() < interval_end_time:
                self.turn_on(self.args["toggled_entity"])
            else:
                # ends next day
                if interval_end_time < interval_start_time:
                    self.turn_on(self.args["toggled_entity"])
                else:
                    self.turn_off(self.args["toggled_entity"])

    def cancel_timer_if_running(self, timer_handle):
        if timer_handle:
            self.cancel_timer(timer_handle)

    def get_interval_time(self, time_entity):
        time_as_str = self.get_state(time_entity)
        return parser.parse(time_as_str).time()

    def toggle(self, input_args):
        self.log("toggled to " + str(input_args["toState"]))
        if input_args["toState"]:
            self.turn_on(self.args["toggled_entity"])
        else:
            self.turn_off(self.args["toggled_entity"])
