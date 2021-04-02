from apps.general.time_based_toggle_automations import TimeBasedToggleAutomation
from apps.general.time_based_toggle_automations import TurnOnOffInterval


from datetime import time
from mock import patch
from appdaemontestframework import automation_fixture


@automation_fixture(TurnOnOffInterval)
def turn_on_off_interval(given_that):
    given_that.passed_arg('toggled_entity')  \
        .is_set_to('switch.toggled_entity')
    given_that.passed_arg('on_interval_length')  \
        .is_set_to('input_number.on_interval_length')
    given_that.passed_arg('off_interval_length')  \
        .is_set_to('input_number.off_interval_length')
    given_that.state_of('input_number.on_interval_length')  \
        .is_set_to('60', {'unit_of_measurement': 's'})
    given_that.state_of('input_number.off_interval_length')  \
        .is_set_to('120', {'unit_of_measurement': 's'})
    TurnOnOffInterval.initialize_on_creation = False


def test_initialize_timers_on_off_interval_without_time_restriction(turn_on_off_interval, given_that, assert_that, time_travel):
    turn_on_off_interval.initalize_timers(None, None, None, None, None)
    assert_that('switch.toggled_entity').was.turned_on()
    given_that.mock_functions_are_cleared()
    time_travel.fast_forward(61).seconds()
    assert_that('switch.toggled_entity').was.turned_off()
    time_travel.fast_forward(118).seconds()
    given_that.mock_functions_are_cleared()
    assert_that('switch.toggled_entity').was_not.turned_on()
    time_travel.fast_forward(3).seconds()
    assert_that('switch.toggled_entity').was.turned_on()


def test_initialize_timers_without_time_restriction_timer_reinitialized_on_event(turn_on_off_interval, given_that, assert_that, time_travel):
    turn_on_off_interval.initalize_timers(None, None, None, None, None)
    assert_that('switch.toggled_entity').was.turned_on()
    given_that.mock_functions_are_cleared()
    time_travel.fast_forward(30).seconds()
    turn_on_off_interval.initalize_timers(None, None, None, None, None)
    time_travel.fast_forward(31).seconds()
    assert_that('switch.toggled_entity').was_not.turned_off()
    given_that.mock_functions_are_cleared()
    time_travel.fast_forward(30).seconds()
    assert_that('switch.toggled_entity').was.turned_off()


@automation_fixture(TimeBasedToggleAutomation)
def toggle_automation(given_that):
    given_that.passed_arg('time_interval_start')  \
        .is_set_to('input_datetime.interval_start')
    given_that.passed_arg('time_interval_end')  \
        .is_set_to('input_datetime.interval_end')
    given_that.passed_arg('toggled_entity')  \
        .is_set_to('switch.toggled_switch')
    TimeBasedToggleAutomation.initialize_on_creation = False


def test_initalize_timers_both_timer_activated_and_switch_not_turned_on_because_earlier_as_start_time(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=16))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('02:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=2, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_off()


def test_initalize_timers_both_timer_activated_and_switch_turned_on_because_earlier_as_end_time(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=1))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('02:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=2, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_on()


def test_initalize_timers_both_timer_activated_and_switch_turned_off_because_earlier_as_start_time_on_same_day(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=18))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('20:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=20, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_off()


def test_initalize_timers_both_timer_activated_and_switch_turned_because_later_as_start_time_on_same_day(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=19))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('02:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=2, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_on()


def test_initalize_timers_both_timer_activated_and_switch_turned_because_later_as_start_time_on_the_next_day(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=1))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('02:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=2, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_on()


def test_initalize_timers_both_timer_activated_and_switch_turned_off_because_later_as_end_time_on_the_next_day(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=3))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('18:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('02:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=18, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=2, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_off()


def test_initalize_timers_both_timer_activated_and_switch_turned_off_because_later_as_end_time_on_the_same_day(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=17))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('10:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('16:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=10, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=16, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_off()


def test_initalize_timers_on_event_check_timer_cancelled_when_new_event_occurs(given_that, toggle_automation, assert_that, time_travel):
    given_that.time_is(time(hour=17))

    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('10:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('16:30:00')

    toggle_automation.initalize_timers(None, None, None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=10, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=16, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_off()

    given_that.mock_functions_are_cleared()

    given_that.time_is(time(hour=17))
    given_that.state_of('input_datetime.interval_start') \
        .is_set_to('10:30:00')
    given_that.state_of('input_datetime.interval_end') \
        .is_set_to('17:30:00')

    toggle_automation.initalize_timers_on_event(None, None, None)

    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=10, minute=30), toState=True) \
        .with_callback(toggle_automation.toggle)
    assert_that(toggle_automation) \
        .registered.run_daily(time(hour=17, minute=30), toState=False) \
        .with_callback(toggle_automation.toggle)
    assert_that("switch.toggled_switch").was.turned_on()
