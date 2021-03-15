from apps.lights.dim_automation import DimLights
from appdaemon.plugins.hass.hassapi import Hass
from appdaemontestframework.hass_mocks import MockHandler
from mock import patch
from mock import Mock
from appdaemontestframework import automation_fixture


@automation_fixture(DimLights)
def dim_lights(given_that, hass_mocks):
    hass_mocks._mock_handlers.append(
        MockHandler(Hass, "get_app", side_effect=[Mock()]))
    given_that.passed_arg('dim_time_out').is_set_to(0.1)
    given_that.passed_arg('toggle_delta').is_set_to(1.0)
    given_that.passed_arg('light_group').is_set_to('group.some_light_group')
    given_that.passed_arg('light_sensor').is_set_to(
        'sensor.light_intensity_in_percent')
    given_that.passed_arg('constrain_input_boolean').is_set_to(
        'input_boolean.constraint')
    given_that.passed_arg('light_intensity_toggle_threshold').is_set_to(
        'input_number.light_intensity_threshold')
    given_that.passed_arg('light_turn_off_step_size').is_set_to(
        "input_number.automatic_dim_step_size")
    given_that.passed_arg('light_turn_off_boundary_brightness').is_set_to(
        "input_number.light_turn_off_boundary_brightness")

    given_that.state_of(
        'input_boolean.constraint').is_set_to('on')
    given_that.state_of(
        'input_number.light_turn_off_boundary_brightness').is_set_to('20.0')
    given_that.state_of(
        'input_number.automatic_dim_step_size').is_set_to('20.0')


def test_toggle_event_when_light_group_is_off(given_that, dim_lights, assert_that):
    given_that.state_of('group.some_light_group').is_set_to('off')
    dim_lights.toggle_event(
        'input_number.light_intensity_threshold', None, None, None, None)
    assert_that('light.some_light').was_not.turned_on()


def test_toggle_event_when_current_light_intensity_less_than_threshold(given_that, dim_lights, assert_that):
    given_that.state_of("light.some_light").is_set_to("on")
    given_that.state_of('group.some_light_group').is_set_to('on',
                                                            {'entity_id': ["light.some_light"],
                                                             'brightness': 100})
    given_that.state_of('sensor.light_intensity_in_percent').is_set_to('70.0')
    given_that.state_of(
        'input_number.light_intensity_threshold').is_set_to('80.0')
    dim_lights.toggle_event(
        'group.some_light_group', None, None, None, None)
    assert_that('light.some_light').was_not.turned_on()


def test_toggle_event_when_current_light_intensity_less_than_threshold(given_that, dim_lights, assert_that):
    given_that.state_of("light.some_light").is_set_to("on")
    given_that.state_of('group.some_light_group').is_set_to('on',
                                                            {'entity_id': ["light.some_light"],
                                                             'brightness': 100})
    given_that.state_of('sensor.light_intensity_in_percent').is_set_to('70.0')
    given_that.state_of(
        'input_number.light_intensity_threshold').is_set_to('80.0')
    dim_lights.toggle_event(
        'group.some_light_group', None, None, None, None)
    assert_that('light.some_light').was_not.turned_on()


def test_toggle_event_when_light_is_at_max_brightness(given_that, dim_lights, assert_that):
    given_that.state_of("light.some_light").is_set_to("on")
    given_that.state_of('group.some_light_group').is_set_to('on',
                                                            {'entity_id': ["light.some_light"],
                                                             'brightness': 100})
    given_that.state_of('sensor.light_intensity_in_percent').is_set_to('70.0')
    given_that.state_of(
        'input_number.light_intensity_threshold').is_set_to('65.0')
    dim_lights.toggle_event(
        'group.some_light_group', None, None, None, None)
    assert_that('light.some_light').was_not.turned_on()


called_light_sensor = 0
dim_light_iteration = 0


def resetGlobals():
    globals()["called_light_sensor"] = 0
    globals()["dim_light_iteration"] = 0
    globals()["dim_light_iteration_light_1"] = 0
    globals()["dim_light_iteration_light_2"] = 0


def fetch_from_globals_with_count_increase(return_args, global_key):
    returned_in_this_iteration = return_args[globals()[global_key]]
    globals()[global_key] = globals()[global_key] + 1
    return returned_in_this_iteration


def test_toggle_light_when_light_intensity_is_underneith_threshold_light_is_increased(given_that, dim_lights, assert_that):
    def get_state_patched(*args, **kwargs):
        entity_name = args[0]
        len_kwargs = len(kwargs)

        if entity_name == 'input_boolean.constraint':
            return "on"
        if entity_name == 'input_number.light_turn_off_boundary_brightness':
            return "20.0"
        if entity_name == 'input_number.automatic_dim_step_size':
            return "20.0"
        if entity_name == 'group.some_light_group':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'entity_id':
                return ['light.some_light']
        if entity_name == 'light.some_light':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'brightness':
                return_args = [80, 100]
                return fetch_from_globals_with_count_increase(return_args, 'dim_light_iteration')
        if entity_name == 'input_number.light_intensity_threshold':
            # light threshold
            return 90.0
        if entity_name == 'sensor.light_intensity_in_percent':
            return_args = [85.0, 87.5, 89.5]
            return fetch_from_globals_with_count_increase(return_args, 'called_light_sensor')
        return "None"

    with patch('appdaemon.plugins.hass.hassapi.Hass.get_state', side_effect=get_state_patched):
        resetGlobals()
        dim_lights.toggle_event(
            'group.some_light_group', None, None, None, None)
        assert globals()['called_light_sensor'] == 3
        assert_that('light.some_light').was.turned_on(
            brightness=100, transition=0.1)
        assert_that('light.some_light').was.turned_on(
            brightness=120, transition=0.1)


def test_toggle_light_when_light_intensity_is_underneith_threshold_and_light_can_not_be_increased_anymore(given_that, dim_lights, assert_that):
    def get_state_patched(*args, **kwargs):
        entity_name = args[0]
        len_kwargs = len(kwargs)

        if entity_name == 'input_boolean.constraint':
            return "on"
        if entity_name == 'input_number.light_turn_off_boundary_brightness':
            return "20.0"
        if entity_name == 'input_number.automatic_dim_step_size':
            return "20.0"
        if entity_name == 'group.some_light_group':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'entity_id':
                return ['light.some_light']
        if entity_name == 'light.some_light':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'brightness':
                return_args = [235.0, 255.0]
                return fetch_from_globals_with_count_increase(return_args, 'dim_light_iteration')
        if entity_name == 'input_number.light_intensity_threshold':
            # light threshold
            return 90.0
        if entity_name == 'sensor.light_intensity_in_percent':
            return_args = [85.0, 87.5, 87.5]
            return fetch_from_globals_with_count_increase(return_args, 'called_light_sensor')
        return "None"

    with patch('appdaemon.plugins.hass.hassapi.Hass.get_state', side_effect=get_state_patched):
        resetGlobals()
        dim_lights.toggle_event(
            'group.some_light_group', None, None, None, None)
        assert globals()['called_light_sensor'] == 2
        assert_that('light.some_light').was.turned_on(
            brightness=255.0, transition=0.1)
        assert_that('light.some_light').was_not.turned_on(
            brightness=275, transition=0.1)


def test_toggle_light_when_light_intensity_is_over_threshold_light_is_dimmed(given_that, dim_lights, assert_that):
    def get_state_patched(*args, **kwargs):
        entity_name = args[0]
        len_kwargs = len(kwargs)

        if entity_name == 'input_boolean.constraint':
            return "on"
        if entity_name == 'input_number.light_turn_off_boundary_brightness':
            return "20.0"
        if entity_name == 'input_number.automatic_dim_step_size':
            return "20.0"
        if entity_name == 'group.some_light_group':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'entity_id':
                return ['light.some_light']
        if entity_name == 'light.some_light':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'brightness':
                return_args = [100, 80]
                return fetch_from_globals_with_count_increase(return_args, 'dim_light_iteration')
        if entity_name == 'input_number.light_intensity_threshold':
            return 90.0
        if entity_name == 'sensor.light_intensity_in_percent':
            return_args = [95.0, 92.0, 89.5]
            return fetch_from_globals_with_count_increase(return_args, 'called_light_sensor')
        return "None"

    with patch('appdaemon.plugins.hass.hassapi.Hass.get_state', side_effect=get_state_patched):
        resetGlobals()
        dim_lights.toggle_event(
            'group.some_light_group', None, None, None, None)
        assert globals()['called_light_sensor'] == 3
        assert_that('light.some_light').was.turned_on(
            brightness=80, transition=0.1)
        assert_that('light.some_light').was.turned_on(
            brightness=60, transition=0.1)


dim_light_iteration_light_1 = 0
dim_light_iteration_light_2 = 0


def test_toggle_light_stop_to_dim_when_all_lights_off(given_that, dim_lights, assert_that):
    def get_state_patched(*args, **kwargs):
        entity_name = args[0]
        len_kwargs = len(kwargs)

        if entity_name == 'input_boolean.constraint':
            return "on"
        if entity_name == 'input_number.light_turn_off_boundary_brightness':
            return "20.0"
        if entity_name == 'input_number.automatic_dim_step_size':
            return "20.0"
        if entity_name == 'group.some_light_group':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'entity_id':
                return ['light.some_light', 'light.some_light_2']
        if entity_name == 'light.some_light_2':
            if len_kwargs == 0:
                return_args = ['on', 'off']
                return fetch_from_globals_with_count_increase(return_args, 'dim_light_iteration_light_2')
            elif kwargs['attribute'] == 'brightness':
                return 30
        if entity_name == 'light.some_light':
            if len_kwargs == 0:
                return 'on'
            elif kwargs['attribute'] == 'brightness':
                return_args = [50, 30]
                return fetch_from_globals_with_count_increase(return_args, 'dim_light_iteration_light_1')
        if entity_name == 'input_number.light_intensity_threshold':
            return 90.0
        if entity_name == 'sensor.light_intensity_in_percent':
            return_args = [95.0, 92.0, 91.0]
            return fetch_from_globals_with_count_increase(return_args, 'called_light_sensor')
        return "None"
    with patch('appdaemon.plugins.hass.hassapi.Hass.get_state', side_effect=get_state_patched):
        resetGlobals()
        dim_lights.toggle_event(
            'group.some_light_group', None, None, None, None)

        assert globals()['called_light_sensor'] == 2
        assert_that('light.some_light').was.turned_on(
            brightness=30, transition=0.1)
        assert_that('light.some_light').was.turned_off()
        assert_that('light.some_light_2').was.turned_off()
