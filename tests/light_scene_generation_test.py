from apps.lights.scene_generation.light_scene_generation import LightSceneGeneration
from apps.lights.scene_generation.light_scene_generation import HSColorState
from apps.lights.scene_generation.light_scene_generation import XYColorState
from apps.lights.scene_generation.light_scene_generation import RGBColorState
from apps.lights.scene_generation.light_scene_generation import LightState
from apps.lights.scene_generation.light_scene_generation import LightScene

from appdaemontestframework import automation_fixture
from unittest.mock import patch, mock_open
from mock import Mock


@automation_fixture(LightSceneGeneration)
def scene_generator(given_that):
    given_that.passed_arg('homeassistant_base_dir') \
        .is_set_to('/path/to/ha_config')
    given_that.passed_arg('input_select_base_dir') \
        .is_set_to('dir/in/ha_config/input_select')
    given_that.passed_arg('input_number_base_dir') \
        .is_set_to('dir/in/ha_config/input_number')


def test_create_scene(scene_generator, given_that, assert_that, time_travel):
    stored_light_scenes = [{"name": "Bedroom Test Scene",
                            "entities": {"light.test_light": {"state": "off"}}}]
    given_that.state_of("light.group").is_set_to(
        "on", {"entity_id": ["light.1", "light.2"]})
    given_that.state_of("light.1").is_set_to(
        "on", {"brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]})
    given_that.state_of("light.2").is_set_to("off")

    with patch('builtins.open', mock_open(read_data="data")) as open_file_mock:
        with patch('yaml.full_load', side_effect=[stored_light_scenes]):
            with patch('yaml.dump') as yaml_dump_patch:
                with patch('os.path.isfile', side_effect=[False]):
                    event_attributes = {"scene_name": "New Scene",
                                        "scene_group_prefix": "Bedroom",
                                        "light_group": "light.group",
                                        "event_name": "CREATE_SCENE"}

                    scene_generator.delegate_scene_creator_event(
                        "SCENE_CREATOR", event_attributes, None)

                    assert_scene_file_written(open_file_mock, yaml_dump_patch, assert_that,
                                              [{"name": "Bedroom Test Scene",
                                                "entities": {"light.test_light": {"state": "off"}}},
                                                  {"name": "Bedroom New Scene",
                                                   "entities": {"light.1": {"state": "on", "brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]},
                                                                "light.2": {"state": "off"}}}])
                    assert_input_select_written(open_file_mock, yaml_dump_patch, assert_that,
                                                {"bedroom_automatic_light_scene_generated": {"options": ["New Scene", "Test Scene"]},
                                                 "bedroom_light_scene_generated": {"options": ["New Scene", "Test Scene"]},
                                                 "bedroom_scene_generator_light_scene_generated": {"options": ["New Scene", "Test Scene"]}})


def test_create_scene_with_light_intensity_control_and_time_based_scene_control(scene_generator, given_that, assert_that, time_travel):
    stored_light_scenes = [{"name": "Bedroom Test Scene",
                            "entities": {"light.test_light": {"state": "off"}}}]
    stored_light_scene_light_intensitys = {
        "bedroom_test_scene_light_intensity": {"initial": 10, "max": 100, "min": 0, "step": 1}}
    given_that.state_of("light.group").is_set_to(
        "on", {"entity_id": ["light.1", "light.2"]})
    given_that.state_of("light.1").is_set_to(
        "on", {"brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]})
    given_that.state_of("light.2").is_set_to("off")
    given_that.state_of(
        "input_number.light_intensity_control").is_set_to("45.0")
    given_that.state_of(
        "input_select.time_based_scene_control").is_set_to("45.0")
    given_that.state_of('input_select.time_based_scene_control') \
        .is_set_to('work_light_start_time/Work Light',
                   {'options': ['work_light_start_time/work_light_input_select',
                                'night_light_start_time/night_light_input_select']})

    with patch('builtins.open', mock_open(read_data="data")) as open_file_mock:
        with patch('yaml.full_load', side_effect=[stored_light_scenes, stored_light_scene_light_intensitys]):
            with patch('yaml.dump') as yaml_dump_mock:
                with patch('os.path.isfile', side_effect=[True]):
                    event_attributes = {"scene_name": "New Scene",
                                        "scene_group_prefix": "Bedroom",
                                        "light_group": "light.group",
                                        "light_intensity_control": "input_number.light_intensity_control",
                                        "timebased_scene_config": "input_select.time_based_scene_control",
                                        "event_name":  "CREATE_SCENE"}

                    scene_generator.delegate_scene_creator_event(
                        "SCENE_CREATOR", event_attributes, None)

                    assert_scene_file_written(open_file_mock, yaml_dump_mock, assert_that,
                                              [{"name": "Bedroom Test Scene",
                                                "entities": {"light.test_light": {"state": "off"}}},
                                               {"name": "Bedroom New Scene",
                                                "entities": {"light.1": {"state": "on", "brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]},
                                                             "light.2": {"state": "off"},
                                                             "input_number.light_intensity_control": "45"}}])
                    assert_input_select_written(open_file_mock, yaml_dump_mock, assert_that,
                                                {"bedroom_automatic_light_scene_generated": {"options": ["New Scene", "Test Scene"]},
                                                 "bedroom_light_scene_generated": {"options": ["New Scene", "Test Scene"]},
                                                 "bedroom_scene_generator_light_scene_generated": {"options": ["New Scene", "Test Scene"]},
                                                 "work_light_input_select": {"options": ["New Scene", "Test Scene"]},
                                                 "night_light_input_select": {"options": ["New Scene", "Test Scene"]}})
                    assert_input_numbers_written(open_file_mock, yaml_dump_mock, assert_that,
                                                 {"bedroom_test_scene_light_intensity": {"initial": 10, "max": 100, "min": 0, "step": 1},
                                                  "bedroom_new_scene_light_intensity": {"initial": 45, "max": 100, "min": 0, "step": 1}})


def test_delete_scene(scene_generator, given_that, assert_that, time_travel):
    stored_light_scenes = [{"name": "Bedroom Test Scene",
                            "entities": {"light.test_light": {"state": "off"}}},
                           {"name": "Bedroom To Be Kept",
                            "entities": {"light.test_light": {"state": "on", "brightness": 80}},
                            "light.other_light": {"state": "on", "brightness": 80, "xy_color": [0.701, 0.299]}}]
    with patch('builtins.open', mock_open(read_data="data")) as open_file_mock:
        with patch('yaml.full_load', side_effect=[stored_light_scenes]):
            with patch('yaml.dump') as yaml_dump_patch:
                with patch('os.path.isfile', side_effect=[False]) as is_file_path:
                    event_attributes = {"scene_name": "Test Scene",
                                        "scene_group_prefix": "Bedroom",
                                        "event_name":  "DELETE_SCENE"}

                    scene_generator.delegate_scene_creator_event(
                        "SCENE_CREATOR", event_attributes, None)

                    assert_scene_file_written(open_file_mock, yaml_dump_patch, assert_that,
                                              [{"name": "Bedroom To Be Kept",
                                                "entities": {"light.test_light": {"state": "on", "brightness": 80}},
                                                "light.other_light": {"state": "on", "brightness": 80, "xy_color": [0.701, 0.299]}}])
                    assert_input_select_written(open_file_mock, yaml_dump_patch, assert_that,
                                                {"bedroom_automatic_light_scene_generated": {"options": ["To Be Kept"]},
                                                 "bedroom_light_scene_generated": {"options": ["To Be Kept"]},
                                                 "bedroom_scene_generator_light_scene_generated": {"options": ["To Be Kept"]}})
                    is_file_path.assert_called_once_with(
                        "/path/to/ha_config/dir/in/ha_config/input_number/bedroom_generated.yaml")
                    assert_that("input_number/reload").was_not.called()


def test_update_scene(scene_generator, given_that, assert_that, time_travel):
    stored_light_scenes = [{"name": "Bedroom Test Scene",
                            "entities": {"light.1": {"state": "off"}}},
                           {"name": "Bedroom To Be Updated",
                            "entities": {"light.1": {"state": "on", "brightness": 80},
                                         "light.2": {"state": "on", "brightness": 80, "xy_color": [0.701, 0.299]}}}]
    with patch('builtins.open', mock_open(read_data="data")) as open_file_mock:
        with patch('yaml.full_load', side_effect=[stored_light_scenes]):
            with patch('yaml.dump') as yaml_dump_patch:
                with patch('os.path.isfile', side_effect=[False]):
                    given_that.state_of("light.group").is_set_to(
                        "on", {"entity_id": ["light.1", "light.2"]})
                    given_that.state_of("light.1").is_set_to(
                        "on", {"brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]})
                    given_that.state_of("light.2").is_set_to("off")
                    event_attributes = {"scene_name": "To Be Updated",
                                        "scene_group_prefix": "Bedroom",
                                        "light_group": "light.group",
                                        "event_name":  "UPDATE_SCENE"}
                    scene_generator.delegate_scene_creator_event(
                        "SCENE_CREATOR", event_attributes, None)
                    assert_scene_file_written(open_file_mock, yaml_dump_patch, assert_that,
                                              [{"name": "Bedroom Test Scene",
                                                "entities": {"light.1": {"state": "off"}}},
                                               {"name": "Bedroom To Be Updated",
                                                  "entities": {"light.1": {"state": "on", "brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]},
                                                               "light.2": {"state": "off"}}}])


def test_update_scene_with_light_intensity_control(scene_generator, given_that, assert_that, time_travel):
    stored_light_scenes = [{"name": "Bedroom Test Scene",
                            "entities": {"light.1": {"state": "off"},
                                         "input_number.light_intensity_control": "10.0"}},
                           {"name": "Bedroom To Be Updated",
                            "entities": {"light.1": {"state": "on", "brightness": 80},
                                         "light.2": {
                                             "state": "on", "brightness": 80, "xy_color": [0.701, 0.299]},
                                         "input_number.light_intensity_control": "70.0"}}]
    stored_light_scene_light_intensitys = {
        "bedroom_test_scene_light_intensity": {"initial": 10, "max": 100, "min": 0, "step": 1},
        "bedroom_to_be_updated_light_intensity": {"initial": 22, "max": 100, "min": 0, "step": 1}}
    given_that.state_of(
        "input_number.light_intensity_control").is_set_to("45.0")
    with patch('builtins.open', mock_open(read_data="data")) as open_file_mock:
        with patch('yaml.full_load', side_effect=[stored_light_scenes, stored_light_scene_light_intensitys]):
            with patch('yaml.dump') as yaml_dump_mock:
                with patch('os.path.isfile', side_effect=[True]):
                    with patch('appdaemon.plugins.hass.hassapi.Hass.set_value') as set_value_mock:
                        given_that.state_of("light.group").is_set_to(
                            "on", {"entity_id": ["light.1", "light.2"]})
                        given_that.state_of("light.1").is_set_to(
                            "on", {"brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]})
                        given_that.state_of("light.2").is_set_to("off")
                        event_attributes = {"scene_name": "To Be Updated",
                                            "scene_group_prefix": "Bedroom",
                                            "light_group": "light.group",
                                            "light_intensity_control": "input_number.light_intensity_control",
                                            "event_name":  "UPDATE_SCENE"}
                        scene_generator.delegate_scene_creator_event(
                            "SCENE_CREATOR", event_attributes, None)
                        assert_scene_file_written(open_file_mock, yaml_dump_mock, assert_that,
                                                  [{"name": "Bedroom Test Scene",
                                                    "entities": {"light.1": {"state": "off"},
                                                                 "input_number.light_intensity_control": "10.0"}},
                                                   {"name": "Bedroom To Be Updated",
                                                      "entities": {"light.1": {"state": "on", "brightness": 200, "xy_color": [0.5, 0.7], "hs_color": [0.1, 0.44]},
                                                                   "light.2": {"state": "off"},
                                                                   "input_number.light_intensity_control": "45"}}])
                        assert_input_numbers_written(open_file_mock, yaml_dump_mock, assert_that,
                                                     {"bedroom_test_scene_light_intensity": {"initial": 10, "max": 100, "min": 0, "step": 1},
                                                      "bedroom_to_be_updated_light_intensity": {"initial": 45, "max": 100, "min": 0, "step": 1}},
                                                     1)
                        set_value_mock.assert_called_once_with(
                            "input_number.bedroom_to_be_updated_light_intensity", 45)


def assert_input_numbers_written(open_file_mock, yaml_dump_mock, assert_that, expected_input_numbers, input_file_write_call_index=2):
    assert open_file_mock.call_args_list[input_file_write_call_index + 1][0][0] \
        == "/path/to/ha_config/dir/in/ha_config/input_number/bedroom_generated.yaml"
    assert yaml_dump_mock.call_args_list[input_file_write_call_index][0][0] == expected_input_numbers
    assert_that("input_number/reload").was.called()


def assert_scene_file_written(open_file_mock, yaml_dump_mock, assert_that, expected_scene):
    assert open_file_mock.call_args_list[0][0][0] == "/path/to/ha_config/bedroom/scenes.yaml"
    assert open_file_mock.call_args_list[1][0][0] == "/path/to/ha_config/bedroom/scenes.yaml"
    assert yaml_dump_mock.call_args_list[0][0][0] == expected_scene
    assert_that("scene/reload").was.called()


def assert_input_select_written(open_file_mock, yaml_dump_patch, assert_that, exected_input_select, input_file_write_call_index=2):
    assert open_file_mock.call_args_list[input_file_write_call_index][0][0] \
        == "/path/to/ha_config/dir/in/ha_config/input_select/bedroom_generated.yaml"
    assert yaml_dump_patch.call_args_list[1][0][0] == exected_input_select
    assert_that("input_select/reload").was.called()


def test_light_scene_to_dict():
    firstLightState = LightState("light.foo", "on", [RGBColorState(
        200, 100, 200), XYColorState(0.01, 0.15)], None)
    secondLightState = LightState("light.foo2", "on", [], 25)

    actual_scene_dict = LightScene("Test Scene", "Living Room", [
        firstLightState, secondLightState]).to_dict()
    expected_scene_dict = {"name": "Living Room Test Scene", "entities": {}}
    expected_scene_dict["entities"].update(firstLightState.to_dict_value())
    expected_scene_dict["entities"].update(secondLightState.to_dict_value())

    assert actual_scene_dict == expected_scene_dict


def test_light_scene_to_dict_empty_states():
    assert LightScene("Test Scene", "Living Room", []).to_dict() == {
        "name": "Living Room Test Scene", "entities": {}}


def test_light_scene_get_light_scene_name():
    assert LightScene("Test Scene", "Living Room", []
                      ).get_light_scene_name() == "Living Room Test Scene"


def test_light_scene_get_name_normalized():
    assert LightScene("Test Scene", "Living Room", []
                      ).get_name_normalized() == "test_scene"


def test_light_scene_get_group_normalized():
    assert LightScene("Test Scene", "Living Room", []
                      ).get_group_normalized() == "living_room"


def test_light_scene_create_light_scene_input_select_name():
    assert LightScene("Test Scene", "bedroom", []).create_light_scene_input_select_name(
        "post Fix") == "bedroom_post_fix"


def test_light_scene_create_light_scene_path():
    assert LightScene("Test Scene", "bedroom", []).create_light_scene_path(
        "hass/conf") == "hass/conf/bedroom/scenes.yaml"


def test_light_state_create_light_state_with_color_state_and_brightness():
    state_data = {"entity_id": "light.foo", "state": "on",
                  "attributes": {"xy_color": [0.01, 0.15], "brightness": 125}}
    assert LightState.create_light_state(state_data).to_dict_value(
    ) == {"light.foo": {"state": "on", "xy_color": [0.01, 0.15], "brightness": 125}}


def test_light_state_create_light_state():
    state_data = {"entity_id": "light.foo", "state": "on", "attributes": {}}
    assert LightState.create_light_state(state_data).to_dict_value() == {
        "light.foo": {"state": "on"}}


def test_light_state_to_dict_value():
    assert LightState("light.foo", "on", [RGBColorState(200, 100, 200), XYColorState(0.01, 0.15)], None).to_dict_value() \
        == {"light.foo": {"state": "on", "rgb_color": [200, 100, 200], "xy_color": [0.01, 0.15]}}


def test_light_state_to_dict_value_with_no_brightness():
    assert LightState("light.foo", "on", [RGBColorState(200, 100, 200)], None).to_dict_value() \
        == {"light.foo": {"state": "on", "rgb_color": [200, 100, 200]}}


def test_light_state_to_dict_value_with_brightness_and_empty_color_states():
    assert LightState("light.foo", "on", [], 25).to_dict_value() == {
        "light.foo": {"state": "on", "brightness": 25}}


def test_light_state_to_dict_value_with_no_brightness_and_empty_color_states():
    assert LightState("light.foo", "on", [], None).to_dict_value() == {
        "light.foo": {"state": "on"}}


def test_light_state_to_dict_value_with_no_brightness_and_None_color_states():
    assert LightState("light.foo", "on", None, None).to_dict_value() == {
        "light.foo": {"state": "on"}}


def test_color_state_rgb_color_to_dict_value():
    assert RGBColorState(200, 100, 200).to_dict_value() == {
        "rgb_color": [200, 100, 200]}


def test_color_state_xy_color_to_dict_value():
    assert XYColorState(0.01, 0.15).to_dict_value() == {
        "xy_color": [0.01, 0.15]}


def test_color_state_hs_color_to_dict_value():
    assert HSColorState(0.01, 0.15).to_dict_value() == {
        "hs_color": [0.01, 0.15]}
