# ota_update.py

class OTAUpdate:
    """Over-the-air software updates (plan section 8). Not implemented yet.

    Tune updates are not delivered this way: tunes arrive through import and need human approval.
    """

    def check_for_updates(self):
        raise NotImplementedError("OTA updates are not implemented yet")

    def apply_update(self):
        raise NotImplementedError("OTA updates are not implemented yet")
