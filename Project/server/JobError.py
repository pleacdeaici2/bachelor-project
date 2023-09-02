class JobError(Exception):

    def __init__(self, ip, job_name):
        self.ip = ip
        self.job_name = job_name
        self.message = f"Can create the job {self.ip}:{self, job_name}"
        super().__init__(self.message)

    "Can not create the job"
