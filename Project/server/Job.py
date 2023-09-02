import os
import pathlib
import threading
import time
from http.client import CannotSendRequest
from xmlrpc.client import MAXINT

import paramiko
from constatns.Configuration import Configuration
from constatns.Constants import path_for_log_err_files, path_executable, jobs_collection
from constatns.Constants import dl
from server.JobError import JobError

"""
Keeps all information we need about the job
"""


class Job(object):
    def __init__(self, configuration, ssh_server):
        self.configuration: Configuration = configuration
        self.ssh_server: paramiko.SSHClient() = ssh_server.ssh
        self.supervisor = ssh_server.supervisor
        self.password = ssh_server.password
        self.pid = None
        self.information = None
        self.ip = ssh_server.ip_address

    def create_conf_file_supervisor(self, temp_file, file):
        temp_file.write("[program:" + file + "]" + '\n')
        temp_file.write(
            "command=" + self.configuration.command + " /home/server/testsupervisor/" + self.configuration.name + ".py" + '\n')
        temp_file.write("autostart=" + str(self.configuration.autostart) + '\n')
        temp_file.write("autorestart=" + str(self.configuration.autorestart) + '\n')
        temp_file.write("stderr_logfile=" + path_for_log_err_files + self.configuration.name + ".err" + '\n')
        temp_file.write("stdout_logfile=" + path_for_log_err_files + self.configuration.name + ".log" + '\n')
        # temp_file.write("memory_limit=" + str(self.configuration.memory) + '\n')

        temp_file.flush()

    def create_log_and_err_file(self):
        # in case we run a file with the same name on current server we delete .err/.log files
        self.ssh_server.exec_command("rm " + path_for_log_err_files + self.configuration.name + ".err")
        self.ssh_server.exec_command("rm " + path_for_log_err_files + self.configuration.name + ".err")
        self.ssh_server.exec_command("touch " + path_for_log_err_files + self.configuration.name + ".err")
        self.ssh_server.exec_command("touch " + path_for_log_err_files + self.configuration.name + ".log")
        dl.logger.info(f"Create log file for {self.configuration.name}{self.configuration.extension} ")

    def send_conf_file(self, file, sftp_client):
        temp_file = open(self.configuration.name + ".conf", "w")
        self.create_conf_file_supervisor(temp_file, file)
        sftp_client.put(temp_file.name, path_for_log_err_files + self.configuration.name + ".conf")
        os.unlink(file + ".conf")
        self.move_file_in_etc()

    def create_enviroment_to_run_program_in_supervisor(self):
        sftp_client = self.ssh_server.open_sftp()
        self.create_log_and_err_file()
        self.send_conf_file(self.configuration.name, sftp_client)
        sftp_client.put(path_executable + self.configuration.name + ".py",
                        path_for_log_err_files + self.configuration.name + ".py")
        self.update_supervisorctl()
        sftp_client.close()

    def move_file_in_etc(self):
        stdin, stdout, stderr = self.ssh_server.exec_command(
            command="sudo cp /home/server/testsupervisor/" + self.configuration.name + ".conf "
                                                                                       "/etc/supervisor/conf.d")
        stdin.flush()
        stdin.write(self.password + "\n")
        if stderr.channel.recv_exit_status() != 0:
            dl.logger.info(f"Can't execute the command : {stderr.readlines()}")
        else:
            dl.logger.info(f"The following was produced: \n {stdout.readlines()}")
        self.ssh_server.exec_command("rm /home/server/testsupervisor/" + self.configuration.name + ".conf")

    def update_supervisorctl(self):
        stdin, stdout, stderr = self.ssh_server.exec_command(
            command="sudo supervisorctl update")
        stdin.flush()
        stdin.write(self.password + "\n")
        if stderr.channel.recv_exit_status() != 0:
            dl.logger.info(f"Can't execute the command : {stderr.readlines()}")
        else:
            dl.logger.info(f"The following was produced: \n {stdout.readlines()}")

        # # TODO: in case of OOM the supervisord is stopped and this can affect the others process
        # #  what are running on the machine

    def start_job(self):
        try:
            self.create_enviroment_to_run_program_in_supervisor()
            self.start_process()
            self.update_job_info()
            dl.logger.info(f"Started job on server {self.ip} with PID : {self.information['pid']}")
            thr = threading.Thread(target=self.check_jos_is_running)
            thr.start()
        except Exception:
            raise JobError(self.ip, self.configuration.name)

    def get_pid_process(self):
        self.update_job_info()
        return self.information["pid"]

    def check_jos_is_running(self):
        dl.logger.info("Start thread")
        self.update_job_info()
        start_pid = self.information["pid"]
        jobs_collection.create_job(self.ip, self.configuration.name + self.configuration.extension,
                                   self.configuration.autorestart, self.information['statename'],
                                   self.information["pid"])
        while self.information['statename'] == 'RUNNING' or self.information['statename'] == 'STARTING':
            if start_pid == self.information["pid"]:
                dl.logger.info(f"Checked {self.ip} : {self.information['name']} process")
                time.sleep(5)
                self.update_job_info()


            else:
                # first we ll get the info from .err file from server
                self.update_job_info()
                jobs_collection.update_job(self.ip, self.configuration.name + self.configuration.extension,
                                           self.information['statename'], self.information["pid"])
                err: str = self.read_stderr_log(0, MAXINT)
                if len(err) != 0:
                    dl.logger.error(f"The following message was catch from {self.ip}.{self.configuration.name} : {err}")
                    time.sleep(3)
                else:
                    output = self.check_linux_killed_processes()
        err: str = self.read_stderr_log(0, MAXINT)
        dl.logger.info(f"Process {self.ip} : {self.information['name']} stopped working with statement "
                       f"{self.information['statename']}")
        if len(err) != 0:
            dl.logger.error(f"The jos finished with following error :  {err}")
        else:
            dl.logger.info(f"The jos finished without any error ")
        directory = self.get_files_from_server()
        jobs_collection.update_job_with_directory(self.ip, self.configuration.name + self.configuration.extension,
                                   self.information['statename'], self.information["pid"], directory)
        # self.clear_enviroment()

    def clear_environment(self):
        dl.logger.info(f"Start clear environment: {self.ip}")

        self.ssh_server.exec_command("rm " + path_for_log_err_files + self.configuration.name + ".err")
        self.ssh_server.exec_command("rm " + path_for_log_err_files + self.configuration.name + ".log")
        self.ssh_server.exec_command(
            "rm " + path_for_log_err_files + self.configuration.name + self.configuration.extension)

        stdin, stdout, stderr = self.ssh_server.exec_command(
            command="sudo rm /etc/supervisor/conf.d/" + self.configuration.name + ".conf ")
        stdin.flush()
        stdin.write(self.password + "\n")
        if stderr.channel.recv_exit_status() != 0:
            dl.logger.info(f"Can't execute the command : {stderr.readlines()}")
        else:
            dl.logger.info(f"The following was produced: \n {stdout.readlines()}")
        self.ssh_server.exec_command("rm /home/server/testsupervisor/" + self.configuration.name + ".conf")

    def get_files_from_server(self):
        # create the dir for files
        directory = "log_files/" + self.configuration.name + "-" + self.ip
        pathlib.Path(directory).mkdir(parents=True, exist_ok=True)
        sftp_client = self.ssh_server.open_sftp()

        sftp_client.get(path_for_log_err_files + self.configuration.name + ".err", directory + "/"
                        + self.configuration.name + ".err")
        sftp_client.get(path_for_log_err_files + self.configuration.name + ".log", directory + "/"
                        + self.configuration.name + ".log")

        sftp_client.close()
        return directory
        #
        # # move files from server to local-host
        # self.ssh_server.exec_command(
        #     command="sudo cp /home/server/testsupervisor/" + self.configuration.name + ".conf " + "/etc/supervisor/conf.d",
        #     get_pty=True)

    def check_linux_killed_processes(self):
        list_of_process = None
        stdin, stdout, stderr = self.ssh_server.exec_command(
            command="journalctl --list-boots | \
                        awk '{ print $1 }' | \
                        xargs -I{} journalctl --utc --no-pager -b {} -kqg 'killed process' -o verbose --output-fields=MESSAGE",
            get_pty=True)
        if stderr.channel.recv_exit_status() != 0:
            dl.logger.info(f"Can't execute the command : {stderr.readlines()}")
        else:
            list_of_process = stdout.readlines()
            dl.logger.info(f"The following was produced: \n {list_of_process}")
        return list_of_process

    def start_process(self):
        self.supervisor.supervisor.startProcess(self.configuration.name, True)

    def stop_process(self):
        self.supervisor.supervisor.stopProcess(self.configuration.name, True)

    def signal_process(self):
        self.supervisor.supervisor.signalProcess(self.configuration.name, 'HUP')

    def update_job_info(self):
        self.information = self.supervisor.supervisor.getProcessInfo(self.configuration.name)
        return self.information

    def get_state(self):
        return self.supervisor.supervisor.getState()

    def clear_log(self):
        self.supervisor.supervisor.clearProcessLogs(self.configuration.name)

    def read_stdout_log(self, offset, length):
        return self.supervisor.supervisor.readProcessStdoutLog(self.configuration.name, offset, length)

    def read_stderr_log(self, offset, length):
        return self.supervisor.supervisor.readProcessStderrLog(self.configuration.name, offset, length)

    def tail_process_stdout_log(self, offset, length):
        return self.supervisor.supervisor.tailProcessStdoutLog(self.configuration.name, offset, length)

    def tail_process_stderr_log(self, offset, length):
        return self.supervisor.supervisor.tailProcessStderrLog(self.configuration.name, offset, length)
