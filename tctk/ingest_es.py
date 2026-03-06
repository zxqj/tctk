import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional

from elasticsearch import Elasticsearch, helpers

# Index naming convention per event type
INDEX_PREFIX = "tctk"
INDEX_BY_TYPE = {
    "message": f"{INDEX_PREFIX}-message",
    "joined": f"{INDEX_PREFIX}-joined",
    "join": f"{INDEX_PREFIX}-join",
    "left": f"{INDEX_PREFIX}-left",
    "room_state_change": f"{INDEX_PREFIX}-room-state",
    "message_delete": f"{INDEX_PREFIX}-message-delete",
    "sub": f"{INDEX_PREFIX}-sub",
    "ready": f"{INDEX_PREFIX}-ready",
}

# Default mappings for key indices (can be created ahead of time); script will create if missing
MAPPINGS = {
    INDEX_BY_TYPE["message"]: {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "user_id": {"type": "long"},
                "username": {"type": "keyword"},
                "channel": {"type": "keyword"},
                "id": {"type": "keyword"},
                "text": {"type": "text"},  # default analyzer tokenizes
                "bits": {"type": "integer"},
                "first": {"type": "boolean"},
                "reply_parent_user_id": {"type": "long"},
            }
        }
    },
    INDEX_BY_TYPE["room_state_change"]: {
        "mappings": {
            "properties": {
                "timestamp": {"type": "date"},
                "channel": {"type": "keyword"},
                "is_emote_only": {"type": "boolean"},
                "is_subs_only": {"type": "boolean"},
                "is_followers_only": {"type": "boolean"},
                "is_unique_only": {"type": "boolean"},
                "follower_only_delay": {"type": "integer"},
                "slow": {"type": "integer"},
            }
        }
    },
}


def _to_bool(v: Any) -> Any:
    if isinstance(v, str) and v in ("0", "1"):
        return v == "1"
    return v


def _coerce_int(v: Any) -> Any:
    if isinstance(v, str) and v.isdigit():
        try:
            return int(v)
        except ValueError:
            return v
    return v


def _remove_nulls(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _normalize_common(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Convert 0/1 strings to booleans and numeric-looking strings to ints
    norm: Dict[str, Any] = {}
    for k, v in payload.items():
        v = _to_bool(v)
        v = _coerce_int(v)
        norm[k] = v
    norm = _remove_nulls(norm)
    return norm


def _extract_best_timestamp(payload: Dict[str, Any], fallback_ts: float) -> float:
    # Prefer highest precision: choose in order if present: sent_timestamp (int ms), tmi-sent-ts (string ms), timestamp (float)
    if isinstance(payload.get("sent_timestamp"), (int, float)):
        return float(payload["sent_timestamp"])  # assume ms
    tmi = payload.get("tmi-sent-ts")
    if isinstance(tmi, str) and tmi.isdigit():
        return float(int(tmi))
    if isinstance(payload.get("timestamp"), (int, float)):
        return float(payload["timestamp"])  # may be seconds
    return float(fallback_ts)


def _index_name(event_type: str) -> str:
    return INDEX_BY_TYPE.get(event_type, f"{INDEX_PREFIX}-{event_type}")


def _normalize_event(event_type: str, ts: float, payload: Dict[str, Any]) -> Dict[str, Any]:
    p = dict(payload) if payload else {}
    # duplicate timestamps cleanup and select best
    best_ts = _extract_best_timestamp(p, ts)
    # remove duplicate timestamp fields
    for dup in ("tmi-sent-ts", "sent_timestamp", "timestamp"):
        p.pop(dup, None)
    doc: Dict[str, Any] = {"timestamp": best_ts}

    # Common fields
    # Promote nested _parsed data where relevant
    parsed = p.pop("_parsed", None)
    if isinstance(parsed, dict):
        tags = parsed.get("tags") or {}
        source = parsed.get("source") or {}
        command = parsed.get("command") or {}
        doc["channel"] = command.get("channel", "").lstrip("#") if command.get("channel") else doc.get("channel")
        # username can be in display-name or source.nick
        user_login = tags.get("display-name") or source.get("nick", "").lstrip(":")
        if user_login:
            doc["username"] = user_login
        # numeric ids in tags
        for id_key in ("room-id", "user-id"):
            if id_key in tags:
                doc[id_key.replace("-", "_")] = _coerce_int(tags[id_key])
        # remove duplicates we don't want
        # parameters is often the raw text; we prefer top-level text
        parsed.pop("parameters", None)
        parsed.pop("tags", None)
        parsed.pop("source", None)
        parsed.pop("command", None)
        parsed = _remove_nulls(parsed)
        # keep any remaining parsed keys (rare)
        for k, v in parsed.items():
            doc[k] = v

    # Merge remaining payload
    for k, v in p.items():
        doc[k] = v

    # Per-type normalization
    if event_type == "message":
        # ensure text is text field, tokenize by default analyzer
        if "text" in doc and isinstance(doc["text"], str):
            pass  # already fine
        # id, bits, first, reply fields
        for k in ("bits", "first", "reply_parent_user_id", "user_id"):
            if k in doc:
                doc[k] = _coerce_int(_to_bool(doc[k]))
    elif event_type in ("joined", "join", "left"):
        # keep channel and username
        pass
    elif event_type == "room_state_change":
        # normalize booleans
        for k in ("is_emote_only", "is_subs_only", "is_followers_only", "is_unique_only"):
            if k in doc:
                doc[k] = bool(_to_bool(doc[k]))
        for k in ("slow", "follower_only_delay"):
            if k in doc:
                doc[k] = _coerce_int(doc[k])
    # drop nulls one more time
    doc = _remove_nulls(doc)
    return doc


def generate_actions(events: Iterable[Tuple[str, float, Dict[str, Any]]]) -> Iterable[Dict[str, Any]]:
    for event_type, ts, payload in events:
        index = _index_name(event_type)
        doc = _normalize_event(event_type, ts, payload or {})
        # Elasticsearch expects dates in ms by default if mapped accordingly; we keep float ms.
        yield {
            "_index": index,
            "_op_type": "index",
            "_source": doc,
        }


def ensure_indices(es: Elasticsearch):
    for index, body in MAPPINGS.items():
        if not es.indices.exists(index=index):
            es.indices.create(index=index, **body)


def load_activity(path: Path) -> List[Tuple[str, float, Dict[str, Any]]]:
    data = json.loads(path.read_text())
    out: List[Tuple[str, float, Dict[str, Any]]] = []
    for e in data.get("activity", []):
        if not isinstance(e, list) or len(e) < 3:
            continue
        etype = str(e[0]).lower()
        ts = float(e[1])
        payload = e[2] or {}
        out.append((etype, ts, payload))
    return out


def bulk_index(path: Path, es: Optional[Elasticsearch] = None) -> int:
    es = es or Elasticsearch()
    ensure_indices(es)
    events = load_activity(path)
    actions = list(generate_actions(events))
    if not actions:
        return 0
    helpers.bulk(es, actions)
    return len(actions)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Index TCTK activity JSON into Elasticsearch")
    parser.add_argument("json_path", type=str, help="Path to activity JSON file")
    parser.add_argument("--es", dest="es_url", type=str, default=None, help="Elasticsearch URL, e.g. http://localhost:9200")
    args = parser.parse_args()

    es_client = Elasticsearch(args.es_url) if args.es_url else Elasticsearch()
    count = bulk_index(Path(args.json_path), es_client)
    print(f"Indexed {count} events")

