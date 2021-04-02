import appdaemon.plugins.hass.hassapi as hass


class SceneUtils(hass.Hass):

    def initialize(self):
        pass

    def turn_on_current_scene_with_transition(self, scene_prefix, scene_input_select, brightness_ratio):
        current_select_scene_display_name = self.get_state(
            scene_input_select)
        scene_entity_id = self.format_scene_name(
            scene_prefix, current_select_scene_display_name)

        self.turn_on(scene_entity_id, transition=100)
        for scene_entity in self.get_state(scene_entity_id, attribute="entity_id"):
            if scene_entity.startswith("light") and self.get_state(scene_entity) == "on":
                brightness = self.get_state(
                    scene_entity, attribute="brightness")
                if brightness:
                    turn_on_brightness = brightness_ratio*brightness
                    self.turn_on(scene_entity, brightness=turn_on_brightness)

    def toggle_scene_brightness_to_room_light_control(self, group_light_intensity_control, scene_prefix, current_select_scene_display_name):
        light_intensity_input = self.format_scene_light_intensity_input_name(
            scene_prefix, current_select_scene_display_name)

        input_number_state = int(
            float(self.get_state_safe(light_intensity_input)))

        self.log("Setting input_number state of %s to %s" %
                 (input_number_state, group_light_intensity_control))

        if input_number_state:
            self.set_value(group_light_intensity_control, input_number_state)

    def turn_on_current_scene_by_name(self, scene_prefix, scene_name):
        scene_entity_id = self.format_scene_name(
            scene_prefix, scene_name)
        self.turn_on(scene_entity_id)

    def turn_on_current_scene(self, scene_prefix, scene_input_select):
        current_select_scene_display_name = self.get_state(
            scene_input_select)
        scene_entity_id = self.format_scene_name(
            scene_prefix, current_select_scene_display_name)
        self.turn_on(scene_entity_id)

    def format_scene_name(self, scene_prefix, scene_friendly_post_fix):
        scene_friendly_post_fix_cleaned = scene_friendly_post_fix.lower().replace(" ", "_")
        scene_prefix_cleaned = scene_prefix.lower()
        return "scene." + scene_prefix_cleaned + "_" + scene_friendly_post_fix_cleaned

    def format_scene_light_intensity_input_name(self, scene_prefix, scene_friendly_post_fix):
        scene_friendly_post_fix_cleaned = scene_friendly_post_fix.lower().replace(" ", "_")
        scene_prefix_cleaned = scene_prefix.lower()
        return "input_number." + scene_prefix_cleaned + "_" + scene_friendly_post_fix_cleaned + "_light_intensity"

    def get_state_safe(self, entity_id):
        try:
            return self.get_state(entity_id)
        except:
            return None

    def read_state_as_float_from(self, input_arg):
        return float(self.get_state(input_arg))
