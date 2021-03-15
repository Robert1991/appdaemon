from apps.lights.activity_based_light_control_automations import TurnOnAutomation
from apps.lights.activity_based_light_control_automations import TurnOnAutomationWithSceneTransition
from apps.lights.activity_based_light_control_automations import ActivityBasedLightSwitch
from appdaemontestframework import automation_fixture
from appdaemon.plugins.hass.hassapi import Hass
from appdaemontestframework.hass_mocks import MockHandler
from mock import patch
from mock import Mock


@automation_fixture(ActivityBasedLightSwitch)
def activity_based_light_switch(given_that):
    given_that.passed_arg('observed_activity_sensor').is_set_to(
        'binary_sensor.some_activity_sensor')
    given_that.passed_arg('light_group').is_set_to(
        'light.some_light_group')


def test_turn_on_lights_light_group_is_turned_on_when_off(activity_based_light_switch, given_that, assert_that):
    given_that.state_of('light.some_light_group').is_set_to('off')
    activity_based_light_switch.turn_on_lights(None, None, None, None, None)
    assert_that('light.some_light_group').was.turned_on()


def test_turn_on_lights_light_group_is_not_turned_on_when_on(activity_based_light_switch, given_that, assert_that):
    given_that.state_of('light.some_light_group').is_set_to('on')
    activity_based_light_switch.turn_on_lights(None, None, None, None, None)
    assert_that('light.some_light_group').was_not.turned_on()


@automation_fixture(TurnOnAutomation)
def turn_on_lights(given_that, hass_mocks):
    setup_turn_on_automation(given_that, hass_mocks)


def test_turn_on_lights_when_time_dependend_control_is_deactivated(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_false):
            given_that.state_of('input_boolean.some_enable_time_automatic_switch') \
                .is_set_to('off')
            given_that.state_of('light.some_light_group').is_set_to('off')
            mock_light_sensor_and_threshold_state(
                turn_on_lights, light_sensor_state_lower_than_threshold)

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_scene_was_turned_on(
                turn_on_lights, assert_that, fire_event_mock)


def test_turn_on_lights_when_there_is_movement_and_insufficient_lights(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_true):
            given_that.state_of('light.some_light_group').is_set_to('off')
            mock_light_sensor_and_threshold_state(
                turn_on_lights, light_sensor_state_lower_than_threshold)

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_scene_was_turned_on(
                turn_on_lights, assert_that, fire_event_mock)


def assert_scene_was_turned_on(turn_on_lights, assert_that, fire_event_mock):
    turn_on_lights.scene_utils.turn_on_current_scene.assert_called_once_with(
        "some_room", "input_select.some_scene_input_select")
    assert_that('light.some_light_group').was_not.turned_on()
    fire_event_mock.assert_called_with(
        "TURN_ON", entity="light.some_light_group")


def test_turn_on_lights_when_there_is_movement_and_insufficient_lights_scene_mode_disabled(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_true):
            given_that.state_of('light.some_light_group').is_set_to('off')
            given_that.state_of('input_boolean.bedroom_automatic_scene_mode_enabled') \
                .is_set_to('off')
            mock_light_sensor_and_threshold_state(
                turn_on_lights, light_sensor_state_lower_than_threshold)

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_light_turned_on(
                turn_on_lights, assert_that, fire_event_mock)


def test_turn_on_lights_when_there_is_movement_and_sufficient_lights(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_true):
            given_that.state_of('light.some_light_group').is_set_to('off')
            mock_light_sensor_and_threshold_state(
                turn_on_lights, light_sensor_state_higher_than_threshold)

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_no_toggle(
                turn_on_lights, assert_that, fire_event_mock)


def light_sensor_state_higher_than_threshold(input_arg_name):
    if input_arg_name == "sensor.some_light_sensor":
        return 45.0
    if input_arg_name == "input_number.some_threshold":
        return 35.0


def test_turn_on_lights_when_there_is_movement_and_sufficient_lights_sensor_state_equals_intensity(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_true):
            given_that.state_of('input_boolean.bedroom_automatic_scene_mode_enabled') \
                .is_set_to('off')
            given_that.state_of('light.some_light_group').is_set_to('off')
            mock_light_sensor_and_threshold_state(
                turn_on_lights, light_sensor_state_and_threshold_are_equal)

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_light_turned_on(
                turn_on_lights, assert_that, fire_event_mock)


def light_sensor_state_and_threshold_are_equal(input_arg_name):
    if input_arg_name == "sensor.some_light_sensor" or input_arg_name == "input_number.some_threshold":
        return 45.0


def assert_light_turned_on(turn_on_lights, assert_that, fire_event_mock):
    assert_that('light.some_light_group').was.turned_on()
    turn_on_lights.scene_utils.turn_on_current_scene.assert_not_called()
    fire_event_mock.assert_called_with(
        "TURN_ON", entity="light.some_light_group")


def test_turn_on_lights_when_there_is_movement_and_insufficient_lights_but_already_on(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        given_that.state_of('light.some_light_group').is_set_to('on')

        turn_on_lights.turn_on_lights(
            'binary_sensor.some_activity_sensor', None, None, None, None)

        assert_no_toggle(turn_on_lights, assert_that, fire_event_mock)


def test_turn_on_lights_when_there_is_movement_and_insufficient_but_time_span_not_met(given_that, turn_on_lights, assert_that):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_false):
            given_that.state_of('light.some_light_group').is_set_to('off')

            turn_on_lights.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            assert_no_toggle(
                turn_on_lights, assert_that, fire_event_mock)


def now_is_between_patched_return_false(from_time, to_time):
    if from_time == "09:00:00" and to_time == "23:00:00":
        return False
    return True


def assert_no_toggle(turn_on_lights, assert_that, fire_event_mock):
    turn_on_lights.scene_utils.turn_on_current_scene.assert_not_called()
    assert_that('light.some_light_group').was_not.turned_on()
    fire_event_mock.assert_not_called()


@automation_fixture(TurnOnAutomationWithSceneTransition)
def turn_on_lights_with_scene_transition(given_that, hass_mocks):
    setup_turn_on_automation(given_that, hass_mocks)


def test_turn_on_lights_with_scene_transition(turn_on_lights_with_scene_transition, given_that, assert_that):
    given_that.state_of(
        'input_boolean.bedroom_automatic_scene_mode_enabled').is_set_to('on')
    given_that.state_of('light.some_light_group').is_set_to('off')

    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        with patch('appdaemon.plugins.hass.hassapi.Hass.now_is_between', side_effect=now_is_between_patched_return_true):
            mock_light_sensor_and_threshold_state(
                turn_on_lights_with_scene_transition, light_sensor_state_lower_than_threshold)

            turn_on_lights_with_scene_transition.turn_on_lights(
                'binary_sensor.some_activity_sensor', None, None, None, None)

            turn_on_lights_with_scene_transition.scene_utils.turn_on_current_scene_with_transition.assert_called_once_with(
                "some_room", "input_select.some_scene_input_select", (40.0 - 35.0) / 40.0)
            assert_that("light.some_light_group").was_not.turned_on()
            fire_event_mock.assert_called_with(
                "TURN_ON", entity="light.some_light_group")


def light_sensor_state_lower_than_threshold(input_arg_name):
    if input_arg_name == "sensor.some_light_sensor":
        return 35.0
    if input_arg_name == "input_number.some_threshold":
        return 40.0


def now_is_between_patched_return_true(from_time, to_time):
    if from_time == "09:00:00" and to_time == "23:00:00":
        return True
    return False


def mock_light_sensor_and_threshold_state(light_turn_on_instance, side_effect_function):
    hass_utils = {
        "read_state_as_float_from.side_effect": side_effect_function}
    light_turn_on_instance.hass_utils.configure_mock(**hass_utils)


def setup_turn_on_automation(given_that, hass_mocks):
    hass_mocks._mock_handlers.append(
        MockHandler(Hass, "get_app", side_effect=[Mock(), Mock()]))
    given_that.passed_arg('enable_automatic_scene_mode').is_set_to(
        'input_boolean.bedroom_automatic_scene_mode_enabled')
    given_that.passed_arg('enable_time_depended_automation_input').is_set_to(
        'input_boolean.some_enable_time_automatic_switch')
    given_that.passed_arg('light_group').is_set_to(
        'light.some_light_group')
    given_that.passed_arg('observed_activity_sensor').is_set_to(
        'binary_sensor.some_activity_sensor')
    given_that.passed_arg('light_intensity_toggle_threshold').is_set_to(
        'input_number.some_threshold')
    given_that.passed_arg('light_sensor').is_set_to(
        'sensor.some_light_sensor')
    given_that.passed_arg('scene_input_select').is_set_to(
        'input_select.some_scene_input_select')
    given_that.passed_arg('scene_group_prefix').is_set_to(
        'some_room')
    given_that.passed_arg('light_automation_start_time').is_set_to(
        'input_datetime.light_automation_start')
    given_that.passed_arg('light_automation_end_time').is_set_to(
        'input_datetime.light_automation_end')
    given_that.state_of('input_boolean.some_enable_time_automatic_switch').is_set_to(
        'on')
    given_that.state_of(
        'input_datetime.light_automation_start').is_set_to('09:00:00')
    given_that.state_of(
        'input_datetime.light_automation_end').is_set_to('23:00:00')
    given_that.state_of(
        'input_boolean.bedroom_automatic_scene_mode_enabled').is_set_to('on')
