import threading
import time

from constatns.Configuration import Configuration
from constatns.Constants import dl
from server.Job import Job
from server.Server import Server


class ServerManager:
    __instance = None

    @staticmethod
    def getInstance():
        if ServerManager.__instance is None:
            ServerManager()
        return ServerManager.__instance

    def __init__(self):
        if ServerManager.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            ServerManager.__instance = self
            self.servers: list[Server] = []

    def add_server(self, server_configuration):

        try:
            server = Server(server_configuration["ip"], server_configuration["user"])
            self.servers.append(server)
            # make here the list elements unique but use list for future tasks
            self.servers = list(tuple(self.servers))
            dl.logger.info(f"Added new server {server.ip_address} in manager ")
        except Exception:
            dl.logger.error(f"Can't connect server with ip : {server_configuration['ip']}")

    def start_job(self, json_file):
        try:
            configuration = Configuration(json_file)
            good_server_for_task: Server = self.find_best_server_for_job(configuration)
            job = Job(configuration, good_server_for_task)
            # good_server_for_task.append_jobs(job)
            # job.start_job()
            good_server_for_task.append_running_job(job)

            # dl.logger.error(f"Can not start job on server {good_server_for_task.ip_address} with PID : {job.pid} {str(e)}")
        except FileNotFoundError:
            dl.logger.error("The file receive doesn't exist on the disk")

    # check if servers has enough space for executable, if a server has not enough space we ll delete it from
    # good_servers
    def find_best_server_for_job(self, configuration) -> Server:
        # store the list of good servers.
        # check if servers has enough space for executable, if a server has not enough space we ll delete it from
        # good_servers
        flag_no_server = True
        while flag_no_server:
            dl.logger.info("Find the best server")
            good_servers = self.servers.copy()
            for server in good_servers:
                if server.get_free_space() < configuration.file_dimension:
                    good_servers.remove(server)
                if server.get_free_ram() < configuration.memory:
                    good_servers.remove(server)
                if server.get_free_core() < 50.0:
                    good_servers.remove(server)
            if good_servers:
                return good_servers[0]
            else:
                dl.logger.info("Can not find a good server for job")
                time.sleep(5)

        # def good_servers(servers):
        #     good_servers = servers
        #     for server in servers:
        #         if server.get_free_space() < configuration.file_dimension:
        #             good_servers.remove(server)
        #         if server.get_free_core() < 90.0:
        #             good_servers.remove(server)
        #     return good_servers
        #
        # capable_servers = good_servers(self.servers)
        # while len(capable_servers) == 0:
        #     capable_servers = good_servers(self.servers)
        #     time.sleep(15)
        #
        # memory_servers = [(server, server.get_free_core()) for server in capable_servers]
        # sorted_server = sorted(memory_servers, key=lambda x: x[1], reverse=True)
        # perfect_server = sorted_server[0]
        # return perfect_server[0]
