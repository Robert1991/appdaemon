import appdaemon.plugins.hass.hassapi as hass

import yaml
import re
from os import path


class LightSceneGeneration(hass.Hass):
    def initialize(self):
        self.listen_event(self.delegate_scene_creator_event,
                          "SCENE_CREATOR")

    def delegate_scene_creator_event(self, event_name, event_attributes, thread):
        self.log("received scene creator event: %s with attributes %s" %
                 (event_name, event_attributes))
        if "event_name" in event_attributes:
            if event_attributes["event_name"] == "CREATE_SCENE":
                self.create_scene("CREATE_SCENE", event_attributes, thread)
            elif event_attributes["event_name"] == "DELETE_SCENE":
                self.delete_scene("DELETE_SCENE", event_attributes, thread)
            elif event_attributes["event_name"] == "UPDATE_SCENE":
                self.update_scene("UPDATE_SCENE", event_attributes, thread)

    def delete_scene(self, event_name, event_attributes, thread):
        if "scene_name" in event_attributes and "scene_group_prefix" in event_attributes:
            light_scene = LightScene(
                event_attributes["scene_name"], event_attributes["scene_group_prefix"], None)
            light_scene_file_path = light_scene.create_light_scene_path(
                self.args["homeassistant_base_dir"])
            stored_light_scenes = self.read_existing_light_scenes(light_scene)
            new_light_scene_array = []
            for stored_light_scene in stored_light_scenes:
                if light_scene.get_scene_name_normalized() != stored_light_scene["name"].lower().replace(' ', '_'):
                    new_light_scene_array.append(stored_light_scene)
            self.write_yaml_dict_to_file(
                light_scene_file_path, new_light_scene_array)
            self.call_service("scene/reload")

            self.regenerate_scene_input_selects(
                light_scene, new_light_scene_array, event_attributes)
            self.delete_scence_light_intensity_in_input_numbers(light_scene)

    def create_scene(self, event_name, event_attributes, thread):
        if "scene_name" in event_attributes and "light_group" in event_attributes and "scene_group_prefix" in event_attributes:
            light_scene = self.create_light_scene_from_states(event_attributes)
            light_scene_name = light_scene.get_light_scene_name()
            stored_light_scenes = self.read_existing_light_scenes(light_scene)
            for stored_light_scene in stored_light_scenes:
                if light_scene_name == stored_light_scene["name"]:
                    # error or update case!
                    return
            stored_light_scenes.append(light_scene.to_dict())
            light_scene_file_path = light_scene.create_light_scene_path(
                self.args["homeassistant_base_dir"])
            self.log("creating light scene %s in %s" %
                     (light_scene_name, light_scene_file_path))
            self.write_yaml_dict_to_file(
                light_scene_file_path, stored_light_scenes)
            self.call_service("scene/reload")

            self.regenerate_scene_input_selects(
                light_scene, stored_light_scenes, event_attributes)
            if self.light_intensity_control_defined(event_attributes):
                self.add_scence_light_intensity_to_input_numbers(light_scene)

    def update_scene(self, event_name, event_attributes, thread):
        if "scene_name" in event_attributes and "light_group" in event_attributes and "scene_group_prefix" in event_attributes:
            light_scene = self.create_light_scene_from_states(event_attributes)
            light_scene_name = light_scene.get_light_scene_name()
            stored_light_scenes = self.read_existing_light_scenes(light_scene)

            new_light_scene_array = []
            for stored_light_scene in stored_light_scenes:
                if light_scene_name.lower().replace(' ', '_')  \
                        == stored_light_scene["name"].lower().replace(' ', '_'):
                    new_light_scene_array.append(light_scene.to_dict())
                else:
                    new_light_scene_array.append(stored_light_scene)

            light_scene_file_path = light_scene.create_light_scene_path(
                self.args["homeassistant_base_dir"])
            self.write_yaml_dict_to_file(
                light_scene_file_path, new_light_scene_array)
            self.call_service("scene/reload")
            if self.light_intensity_control_defined(event_attributes):
                self.update_scence_light_intensity_in_input_numbers(
                    light_scene)

    def create_light_scene_from_states(self, event_attributes):
        lights_in_group = self.get_state(
            event_attributes["light_group"], attribute="entity_id")
        light_states = []
        for light in lights_in_group:
            light_state = self.get_state(light, attribute="all")
            if light_state:
                light_states.append(self.get_state(light, attribute="all"))
        if self.light_intensity_control_defined(event_attributes):
            light_intensity_state = int(float(self.get_state(
                event_attributes["light_intensity_control"])))
        else:
            light_intensity_state = None
        return LightSceneFactory.create_light_scene(event_attributes, light_states, light_intensity_state)

    def light_intensity_control_defined(self, event_attributes):
        return "light_intensity_control" in event_attributes and len(event_attributes["light_intensity_control"]) > 0

    def regenerate_scene_input_selects(self, new_light_scene, all_light_scenes, event_attributes):
        light_scene_options = self.get_scene_input_select_options(
            new_light_scene.get_group_normalized(), all_light_scenes)

        input_select_names = [
            new_light_scene.create_light_scene_input_select_name(
                "automatic_light_scene_generated"),
            new_light_scene.create_light_scene_input_select_name(
                "light_scene_generated"),
            new_light_scene.create_light_scene_input_select_name("scene_generator_light_scene_generated")]
        if "timebased_scene_config" in event_attributes:
            time_based_scene_options = self.get_state(
                event_attributes["timebased_scene_config"], attribute="options")
            for option in time_based_scene_options:
                option_split = option.split('/')
                if len(option_split) == 2:
                    input_select_names.append(option_split[1])
        input_selects = self.create_scene_input_select_dict(
            light_scene_options, input_select_names)
        generated_input_select_file_path = self.get_generated_input_select_path(
            new_light_scene.get_group_normalized())
        self.write_yaml_dict_to_file(
            generated_input_select_file_path, input_selects)
        self.call_service("input_select/reload")

    def add_scence_light_intensity_to_input_numbers(self, new_light_scene):
        generated_input_numbers = self.get_scene_group_light_intensity_input_numbers(
            new_light_scene.get_group_normalized())

        new_light_scene_input_number_name = new_light_scene.get_scene_name_normalized() + \
            "_light_intensity"
        new_light_scene_input_number = {new_light_scene_input_number_name: {
            "initial": new_light_scene.get_light_intensity(), "max": 100, "min": 0, "step": 1}}
        generated_input_numbers.update(new_light_scene_input_number)

        self.write_yaml_dict_to_file(
            self.get_generated_input_numbers_path(new_light_scene.get_group_normalized()), generated_input_numbers)
        self.call_service("input_number/reload")

    def update_scence_light_intensity_in_input_numbers(self, light_scene):
        generated_input_numbers = self.get_scene_group_light_intensity_input_numbers(
            light_scene.get_group_normalized())

        light_scene_input_number_name = light_scene.get_scene_name_normalized() + \
            "_light_intensity"
        if light_scene_input_number_name in generated_input_numbers:
            generated_input_numbers[light_scene_input_number_name]["initial"] = \
                light_scene.get_light_intensity()

        self.write_yaml_dict_to_file(
            self.get_generated_input_numbers_path(light_scene.get_group_normalized()), generated_input_numbers)
        self.call_service("input_number/reload")
        self.set_value("input_number." + light_scene_input_number_name,
                       light_scene.get_light_intensity())

    def delete_scence_light_intensity_in_input_numbers(self, light_scene):
        generated_input_numbers = self.get_scene_group_light_intensity_input_numbers(
            light_scene.get_group_normalized())

        if generated_input_numbers:
            light_scene_input_number_name = light_scene.get_scene_name_normalized() + \
                "_light_intensity"
            if light_scene_input_number_name in generated_input_numbers:
                del generated_input_numbers[light_scene_input_number_name]
                self.write_yaml_dict_to_file(
                    self.get_generated_input_numbers_path(
                        light_scene.get_group_normalized()), generated_input_numbers)
                self.call_service("input_number/reload")

    def create_scene_input_select_dict(self, input_select_options, input_select_names):
        input_select_dict = {}
        for input_select_name in input_select_names:
            input_select_dict.update(
                {input_select_name: {"options": input_select_options.copy()}})
        return input_select_dict

    def get_scene_input_select_options(self, light_scene_group, light_scene_array):
        light_scene_group_filter = \
            re.compile(
                re.escape(light_scene_group.replace("_", " ")), re.IGNORECASE)
        light_scene_names = []
        for light_scene in light_scene_array:
            light_scene_name = \
                light_scene_group_filter.sub(
                    '', light_scene["name"]).strip(' ')
            light_scene_names.append(light_scene_name)
        light_scene_names.sort()
        return light_scene_names

    def get_scene_group_light_intensity_input_numbers(self, scene_group_name):
        generated_input_number_file_path = self.get_generated_input_numbers_path(
            scene_group_name)
        if path.isfile(generated_input_number_file_path):
            with open(generated_input_number_file_path) as input_number_file:
                return yaml.full_load(input_number_file)
        return None

    def get_generated_input_select_path(self, scene_group_name):
        return path.join(
            self.args["homeassistant_base_dir"],
            self.args["input_select_base_dir"],
            scene_group_name + "_generated.yaml")

    def get_generated_input_numbers_path(self, scene_group_name):
        return path.join(
            self.args["homeassistant_base_dir"],
            self.args["input_number_base_dir"],
            scene_group_name + "_generated.yaml")

    def read_existing_light_scenes(self, light_scene):
        light_scene_file_path = light_scene.create_light_scene_path(
            self.args["homeassistant_base_dir"])
        with open(light_scene_file_path) as light_scene_file:
            return yaml.full_load(light_scene_file)

    def write_yaml_dict_to_file(self, file_path, yaml_dict):
        with open(file_path, 'w') as file:
            yaml.dump(yaml_dict, file)


class LightSceneFactory:
    def create_light_scene(event_attributes, light_raw_states, light_intensity_state=None):
        light_states = []
        for light_state in light_raw_states:
            light_states.append(LightState.create_light_state(light_state))
        if "light_intensity_control" in event_attributes and len(event_attributes["light_intensity_control"]) > 0:
            return LightSceneWithLightIntensityControl(event_attributes["scene_name"],
                                                       event_attributes["scene_group_prefix"],
                                                       light_states,
                                                       event_attributes["light_intensity_control"],
                                                       light_intensity_state)
        return LightScene(event_attributes["scene_name"], event_attributes["scene_group_prefix"], light_states)


class LightScene:
    scene_name = ""
    light_states = []
    scene_group = ""

    def __init__(self, scene_name, scene_group, light_states):
        self.scene_name = scene_name
        self.scene_group = scene_group
        self.light_states = light_states

    def create_light_scene_input_select_name(self, post_fix):
        return self.normalize(self.scene_group) + "_" + self.normalize(post_fix)

    def get_group_normalized(self):
        return self.normalize(self.scene_group)

    def get_name_normalized(self):
        return self.normalize(self.scene_name)

    def create_light_scene_path(self, homeassistant_conf_dir):
        scene_group_normalized = self.normalize(self.scene_group)
        path_to_scenes_file = path.join(
            homeassistant_conf_dir, scene_group_normalized, "scenes.yaml")
        return path_to_scenes_file

    def to_dict(self):
        yaml_entry = {"name": self.get_light_scene_name(), "entities": {}}
        for light_state in self.light_states:
            yaml_entry["entities"].update(light_state.to_dict_value())
        return yaml_entry

    def get_scene_name_normalized(self):
        return self.get_group_normalized() + "_" + self.get_name_normalized()

    def get_light_scene_name(self):
        return self.scene_group + " " + self.scene_name

    def normalize(self, toBeNormalized):
        return toBeNormalized.lower().replace(' ', '_')


class LightSceneWithLightIntensityControl(LightScene):
    light_intensity = None
    light_intensity_control_entity = None

    def __init__(self, scene_name, scene_group, light_states, light_intensity_control_entity, scene_light_intensity):
        super().__init__(scene_name, scene_group, light_states)
        self.light_intensity = scene_light_intensity
        self.light_intensity_control_entity = light_intensity_control_entity

    def to_dict(self):
        dict_values = super().to_dict()
        dict_values["entities"].update(
            {self.light_intensity_control_entity: str(self.light_intensity)})
        return dict_values

    def get_light_intensity(self):
        return self.light_intensity


class LightState:
    entity_id = ""
    state = ""
    color_states = []
    brightess = None
    color_temp = None

    def create_light_state(light_state_attributes):
        entity_id = light_state_attributes["entity_id"]
        light_on_off_state = light_state_attributes["state"]
        color_states = LightState.read_color_states(light_state_attributes)
        brightness = None
        color_temp = None
        if "brightness" in light_state_attributes["attributes"]:
            brightness = light_state_attributes["attributes"]["brightness"]
        if "color_temp" in light_state_attributes["attributes"]:
            color_temp = light_state_attributes["attributes"]["color_temp"]
        return LightState(entity_id, light_on_off_state, color_states, brightness, color_temp)

    def read_color_states(light_state):
        color_states = []
        if "hs_color" in light_state["attributes"]:
            h_value = light_state["attributes"]["hs_color"][0]
            s_value = light_state["attributes"]["hs_color"][1]
            color_states.append(HSColorState(h_value, s_value))
        if "rgb_color" in light_state["attributes"]:
            r_value = light_state["attributes"]["rgb_color"][0]
            g_value = light_state["attributes"]["rgb_color"][1]
            b_value = light_state["attributes"]["rgb_color"][2]
            color_states.append(RGBColorState(r_value, g_value, b_value))
        if "xy_color" in light_state["attributes"]:
            x_value = light_state["attributes"]["xy_color"][0]
            y_value = light_state["attributes"]["xy_color"][1]
            color_states.append(XYColorState(x_value, y_value))
        return color_states

    def __init__(self, entity_id, state, color_states, brightness, color_temp):
        self.entity_id = entity_id
        self.state = state
        self.brightess = brightness
        self.color_temp = color_temp
        if color_states:
            self.color_states = color_states

    def to_dict_value(self):
        dict_entry = {self.entity_id: {"state": self.state}}
        if self.brightess:
            dict_entry[self.entity_id].update({"brightness": self.brightess})
        if self.color_temp:
            dict_entry[self.entity_id].update({"color_temp": self.color_temp})
        for color in self.color_states:
            dict_entry[self.entity_id].update(color.to_dict_value())
        return dict_entry


class ColorState:
    def __init___(self):
        pass

    def to_dict_value(self):
        pass


class HSColorState:
    h_value = 0
    s_value = 0

    def __init__(self, h_value, s_value):
        self.h_value = h_value
        self.s_value = s_value

    def to_dict_value(self):
        return {"hs_color": [self.h_value, self.s_value]}


class XYColorState(ColorState):
    x_value = 0
    y_value = 0

    def __init__(self, x_value, y_value):
        self.x_value = x_value
        self.y_value = y_value

    def to_dict_value(self):
        return {"xy_color": [self.x_value, self.y_value]}


class RGBColorState(ColorState):
    red = 0
    green = 0
    blue = 0

    def __init__(self, red, green, blue):
        self.red = red
        self.green = green
        self.blue = blue

    def to_dict_value(self):
        return {"rgb_color": [self.red, self.green, self.blue]}
