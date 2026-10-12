# cloud_sync.py

class CloudSync:
    """Cloud backup and sharing of tunes (plan section 7). Not implemented yet.

    Downloaded tunes must enter the library as origin 'imported' so they need human approval.
    """

    def upload_tune(self, car_id, tune_data):
        raise NotImplementedError("Cloud sync is not implemented yet")

    def download_tune(self, car_id, tune_name):
        raise NotImplementedError("Cloud sync is not implemented yet")
