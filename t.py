from pathlib import Path

from tests.test_integration_replay import _load_log as load
from tests.test_integration_replay import _save_log as save
from datetime import datetime

now = datetime.now

save(load(Path("./activity_latest.json")), Path(f"{round(now().timestamp())}.json"))
