import datetime
import io
import json
import sys
import traceback

from ..config import Config


def describe_exception(exc) -> str:
    writer = io.StringIO()
    exc_type, exc_obj, exc_tb = sys.exc_info()
    writer.writelines(traceback.format_exception(exc_type, exc_obj, exc_tb))
    writer.writelines([
        str(exc),
        f"Error Type: {exc_type.__name__}",
        f"File Name: {exc_tb.tb_frame.f_code.co_filename}",
        f"Line Number: {exc_tb.tb_lineno}"])
    writer.seek(0)
    return writer.read()


HOUR = 60*60


class ActivityLogPersistence:
    def __init__(self, flush_every=4*HOUR):
        self.flush_every = flush_every
        self.data = {
            "start_time": round(datetime.datetime.now().timestamp()),
            "activity": [],
        }

    def add(self, *args):
        if datetime.datetime.now().timestamp() - self.data['start_time'] > self.flush_every:
            self.persist()
        self.data['activity'].append(args)

    def get_path(self):
        def from_idx(i: int):
            suff = ""
            if i > 0:
                suff = f".{str(i).rjust(2,"0")}"
            return Config.data_dir().joinpath(f"activity_{self.data['end_time']}{suff}.json")
        i = 0
        while from_idx(i).exists():
            i = i + 1
        return from_idx(i)


    def persist(self):
        self.data['end_time'] = round(datetime.datetime.now().timestamp())
        with self.get_path().open("w") as f:
            json.dump(self.data, f)

        self.data = {
            "start_time": round(datetime.datetime.now().timestamp()),
            "activity": [],
        }
