# manual_override.py

class ManualOverride:
    def __init__(self):
        self.override_active = False
        self.selected_tune = None

    def activate_override(self, tune_name):
        self.override_active = True
        self.selected_tune = tune_name
        print(f"Manual override activated: {tune_name}")

    def deactivate_override(self):
        self.override_active = False
        self.selected_tune = None
        print("Manual override deactivated.")

    def get_status(self):
        return {
            "override_active": self.override_active,
            "selected_tune": self.selected_tune
        }

if __name__ == "__main__":
    mo = ManualOverride()
    mo.activate_override("Race Mode")
    print(mo.get_status())
    mo.deactivate_override()
    print(mo.get_status())
