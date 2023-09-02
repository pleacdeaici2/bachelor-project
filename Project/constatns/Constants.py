import logging

import dummylog

from mongodb.Collection_DB import Collection_DB
from mongodb.MongoDB import MongoDB

units = {
    'B': 1,
    'K': 1024,
    'M': 1024 ** 2,
    'G': 1024 ** 3,
    'T': 1024 ** 4
}

dl = dummylog.DummyLog()

log = logging.getLogger(__name__)


persist = MongoDB("licenta")
jobs_collection = Collection_DB(persist.get_collection("licenta"))


path_executable = "files/"

path_for_log_err_files = "/home/server/testsupervisor/"
