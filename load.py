# python
import json
from pathlib import Path

def old_load_activity(path: Path) -> dict:
    # Peek at the beginning to understand structure (optional)
    with path.open("r", encoding="utf-8") as f:
        head = f.read(1024)
        # You can log/inspect `head` if needed

    # Load full JSON into a Python dict
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object at top level")
    return data

if __name__ == "__main__":
    activity_path = Path("activity_latest.json")
    activity_dict = old_load_activity(activity_path)
    # Exddddddddample access:
    #print(activity_dict.get("start_time"))
    #print(len(activity_dict.get("activity", [])))
    print(json.dumps(activity_dict, indent=2))
