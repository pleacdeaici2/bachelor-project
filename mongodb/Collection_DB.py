from pymongo.collection import Collection


class Collection_DB:
    def __init__(self, collection):
        self.collection: Collection = collection

    def delete_all(self):
        self.collection.delete_many({})

    def create_job(self, ip_server, job_name, auto_restart, status, pid):
        self.collection.insert_one(
            {
                "ip": ip_server,
                "job_name": job_name,
                "autor_restart": auto_restart,
                "status": status,
                "pid": [pid],
                "directory": ""
            }
        )

    def update_job(self, ip, job_name, status, pid):
        document = self.collection.find_one(
            {"ip": ip, "job_name": job_name})

        list_pids = document["pid"]
        list_pids.append(pid)

        self.collection.update_one(
            {"ip": ip, "job_name": job_name},
            {"$set": {"status": status, "pid": list_pids}}
        )

    def update_job_with_directory(self, ip, job_name, status, pid, directory):
        document = self.collection.find_one(
            {"ip": ip, "job_name": job_name})

        list_pids = document["pid"]
        list_pids.append(pid)

        self.collection.update_one(
            {"ip": ip, "job_name": job_name},
            {"$set": {"status": status, "pid": list_pids, "directory": directory}}
        )

    def clean(self):
        self.collection.delete_many({})
