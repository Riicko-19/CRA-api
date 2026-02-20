class JobNotFoundError(Exception):
    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"Job {job_id!r} not found")


class InvalidStateTransitionError(Exception):
    def __init__(self, from_state: str, to_state: str):
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(f"Cannot transition from '{from_state}' to '{to_state}'")


class InvalidSignatureError(Exception):
    pass
