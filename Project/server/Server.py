import os
import threading
import time
from xmlrpc.client import ServerProxy, MAXINT

import paramiko

from constatns.Utils import Utils
from constatns.Constants import dl, jobs_collection
from server.Job import Job


class Server:

    def __init__(self, ip_address, user):
        self.lock = threading.Lock()
        self.ip_address = ip_address
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        # with open('private_key.pem', 'rb') as self.password:
        file_path = "/home/puscasu/.ssh/id_rsa"

        with open(file_path, 'r') as file:
            self.password = file.read()
            file.close()  # Close the file
        self.ssh.connect(hostname=ip_address,
                         username=user,
                         key_filename=os.path.join(os.path.expanduser('~'), ".ssh", "id_rsa"),
                         port=22)
        self.supervisor = ServerProxy('http://' + self.ip_address + ':9001')
        self.jobs: list[Job] = []
        self.running_jobs: list[Job] = []
        dl.logger.info(f"Created new server with IP = {ip_address}")

    def append_jobs(self, job):
        job.ip = self.ip_address
        self.jobs.append(job)
        dl.logger.info(f"Added new job in server {self.ip_address}")

    def get_free_ram(self):
        stdin, stdout, stderr = self.ssh.exec_command("free -b | awk 'NR==2{print $4}'")
        # Read the output
        output = stdout.read().decode('utf-8')
        return int(output)

    def get_free_space(self):
        stdin, stdout, stderr = self.ssh.exec_command('df -h')
        # Read the output and extract the free space information
        output = stdout.read().decode('utf-8')
        lines = output.strip().split('\n')[1:]  # Exclude the header line
        # We split the line and get the directory '/'
        for line in lines:
            filesystem, size, used, available, percent, mountpoint = line.split()
            if mountpoint == '/':
                return Utils.convert_to_bytes(available)

    def get_free_core(self):
        stdin, stdout, stderr = self.ssh.exec_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        # Read the output
        output = stdout.read().decode('utf-8')
        value = float(output.strip())
        return 100 - value

    # TODO: find a better name for this function
    def values_server(self):
        return self.get_free_space(), self.get_free_ram(), self.get_free_core()

    # TODO: make this function to store all the process
    #  which failed and theirs errors can be catch by supervisord
    def check_killed_process(self):
        list_of_process = None
        stdin, stdout, stderr = self.ssh.exec_command(
            command="grep 'Killed process' /var/log/syslog", get_pty=True)
        if stderr.channel.recv_exit_status() != 0:
            dl.logger.info(f"Can't execute the command : {stderr.readlines()}")
        else:
            list_of_process = stdout.readlines()
            # dl.logger.info(f"The following was produced: \n {list_of_process}")
        return list_of_process

    def info_processes(self):
        return self.supervisor.supervisor.getAllProcessInfo()

    def update_job_info(self, job: Job):
        with self.lock:
            info = self.supervisor.supervisor.getProcessInfo(job.configuration.name)
            return info

    def start_process(self, job: Job):
        with self.lock:
            self.supervisor.supervisor.startProcess(job.configuration.name, True)

    def append_running_job(self, job: Job):
        thr = threading.Thread(target=self.start_job, args=(job,))
        thr.start()
        # self.start_job(job)
        self.running_jobs.append(job)

    def start_job(self, job: Job):
        job.create_enviroment_to_run_program_in_supervisor()
        self.start_process(job)
        job.information = self.update_job_info(job)
        dl.logger.info(f"Started {job.configuration.name} on server {job.ip} with PID : {job.information['pid']}")
        self.check_if_job_is_running(job)

    def check_if_job_is_running(self, job: Job):
        try:
            dl.logger.info("Start thread")
            job.information = self.update_job_info(job)
            start_pid = job.information["pid"]
            jobs_collection.create_job(job.ip, job.configuration.name + job.configuration.extension,
                                       job.configuration.autorestart, job.information['statename'],
                                       job.information["pid"])
            while job.information['statename'] == 'RUNNING' or job.information['statename'] == 'STARTING':
                if job.information['statename'] == 'STARTING':
                    start_pid = job.information["pid"]
                    directory = job.get_files_from_server()
                    jobs_collection.update_job_with_directory(job.ip,
                                                              job.configuration.name + job.configuration.extension,
                                                              job.information['statename'], job.information["pid"],
                                                              directory)
                if start_pid == job.information["pid"]:
                    dl.logger.info(f"Checked {job.ip} : {job.information['name']} process")
                    time.sleep(5)
                    job.information = self.update_job_info(job)


                else:
                    # first we ll get the info from .err file from server
                    job.information = self.update_job_info(job)
                    jobs_collection.update_job(job.ip, job.configuration.name + job.configuration.extension,
                                               job.information['statename'], job.information["pid"])
                    err: str = self.read_stderr_log(job, 0, MAXINT)
                    if len(err) != 0:
                        dl.logger.error(f"The following message was catch from {job.ip}.{job.configuration.name} : {err}")
                        job.information = self.update_job_info(job)
                        time.sleep(3)
                        if job.configuration.autorestart:
                            start_pid = job.information["pid"]

                    else:
                        output = job.check_linux_killed_processes()

        finally:
            err: str = self.read_stderr_log(job,0, MAXINT)
            dl.logger.info(f"Process {job.ip} : {job.information['name']} stopped working with statement "
                           f"{job.information['statename']}")
            if len(err) != 0:
                dl.logger.error(f"The jos finished with following error :  {err}")
            else:
                dl.logger.info(f"The jos finished without any error ")
            directory = job.get_files_from_server()
            jobs_collection.update_job_with_directory(job.ip, job.configuration.name + job.configuration.extension,
                                                      job.information['statename'], job.information["pid"], directory)
            job.clear_environment()

    def read_stderr_log(self, job:Job, offset, length):
        with self.lock:
            return self.supervisor.supervisor.readProcessStderrLog(job.configuration.name, offset, length)

