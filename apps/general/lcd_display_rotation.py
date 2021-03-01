import appdaemon.plugins.hass.hassapi as hass


class LCDDisplayRotation(hass.Hass):
    current_display_index = 0
    total_entities_to_display = 0

    def initialize(self):
        self.total_entities_to_display = len(self.args["displayed_entities"])
        self.start_rotation_timer()

    def start_rotation_timer(self):
        self.log("Started display rotation for:" + self.args["mqtt_display"])
        self.log("Displaying: ")
        for displayed in self.args["displayed_entities"]:
            self.log("Entity: " + displayed["entity"])
            self.log("Name: " + displayed["name"])
        self.run_in(self.rotate_screen, int(self.args["rotate_timeout"]))

    def rotate_screen(self, args):
        next_for_display = self.args["displayed_entities"][self.current_display_index]

        current_entity_state = float(
            self.get_state(next_for_display["entity"]))

        unit = next_for_display["unit"].replace("\\\\", "\\")

        display_message = next_for_display["name"] + \
            ":\n" + str(current_entity_state) + " " + unit

        self.call_service("mqtt/publish",
                          topic=self.args["mqtt_display"],
                          payload=display_message,
                          retain=True)

        self.current_display_index += 1
        if self.current_display_index == self.total_entities_to_display:
            self.current_display_index = 0
        self.run_in(self.rotate_screen, int(self.args["rotate_timeout"]))
