from apps.general.activity_based_turn_off_automations import TurnOffAutomation
from appdaemontestframework import automation_fixture
from mock import patch
from appdaemon.plugins.hass.hassapi import Hass
from appdaemontestframework.hass_mocks import MockHandler
from mock import Mock


@automation_fixture(TurnOffAutomation)
def turn_off_entity(given_that, hass_mocks):
    hass_mocks._mock_handlers.append(
        MockHandler(Hass, "log"))
    given_that.passed_arg('observed_activity_sensor').is_set_to(
        'binary_sensor.some_activity_sensor')
    given_that.passed_arg('turn_off_timeout').is_set_to(
        'input_number.some_turn_off_time_out')
    given_that.passed_arg('entity').is_set_to('light.some_light_group')

    given_that.state_of('input_number.some_turn_off_time_out') \
        .is_set_to("179.0")


def test_start_turn_off_entity_timer_turns_off_light_after_configured_input(given_that, turn_off_entity, assert_that, time_travel):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        turn_off_entity.start_turn_off_timer(
            None, None, None, None, None)

        time_travel.fast_forward(3).minutes()

        assert_that('light.some_light_group').was.turned_off()
        fire_event_mock.assert_called_with(
            "TURN_OFF", entity="light.some_light_group")


def test_start_turn_off_entity_timer_not_turns_off_when_movement_occurs(given_that, turn_off_entity, assert_that, time_travel):
    with patch('appdaemon.plugins.hass.hassapi.Hass.fire_event') as fire_event_mock:
        turn_off_entity.start_turn_off_timer(
            None, None, None, None, None)

        time_travel.fast_forward(1).minutes()

        turn_off_entity.stop_turn_off_timer(
            None, None, None, None, None)

        time_travel.fast_forward(2).minutes()

        assert_that('light.some_light_group').was_not.turned_off()
        fire_event_mock.assert_not_called()
