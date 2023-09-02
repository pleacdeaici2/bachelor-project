from pymongo.collection import Collection
from pymongo import MongoClient

from mongodb.Collection_DB import Collection_DB


class MongoDB:
    def __init__(self, database: str, connection_retries=3):
        self.connection = MongoClient("mongodb://root:example@172.19.0.3:27017")
        self.database = self.connection[database]
        connection_ok_flag = True if self.database.command('ping')['ok'] == 1.0 else False

        while connection_retries > 0 and connection_ok_flag is False:
            self.connection = MongoClient("mongodb://root:example@172.19.0.3:27017")
            connection_ok_flag = True if self.database.command('ping')['ok'] == 1.0 else False
            connection_retries -= 1

        print("Connection successful" if connection_ok_flag else "Failed to connect")

    def get_collection(self, collection_name: str) -> Collection:
        return self.database[collection_name]


# small test here to check if the connection it's work properly
if __name__ == '__main__':
    db_mongo = MongoDB("licenta")
    aux = Collection_DB(db_mongo.get_collection("licenta"))
    aux.clean()
    # aux.create_job("192.168.0.0", "ceva_job", ".py", True, "MERGE", 3)
    # aux.update_job("192.168.0.0", "ceva_job", "NU MERGE", 4)
