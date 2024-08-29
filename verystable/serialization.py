import json
import datetime
import pathlib

from . import script


class VSJson:
    """
    JSON serialization that knows how to deal with bytes, dates, and various bitcoin
    structures.
    """

    # Append to this dynamically as needed to allow certain classes to be
    # serialized/deserialized.
    ALLOWED_CLASSES: dict[str, type] = {}

    @classmethod
    def add_allowed_classes(cls, *classes):
        for c in classes:
            cls.ALLOWED_CLASSES[c.__name__] = c

    class Encoder(json.JSONEncoder):

        def default(self, o):
            if isinstance(o, bytes):
                return {"__hex": o.hex()}
            elif isinstance(o, datetime.datetime):
                return {"__datetime": o.isoformat()}
            elif isinstance(o, pathlib.Path):
                return {"__path": str(o)}
            elif isinstance(o, script.CScript):
                return {"__CScript": o.hex()}
            elif isinstance(o, script.CTransaction):
                return {"__CTransaction": o.tohex()}

            elif cls := VSJson.ALLOWED_CLASSES.get(o.__class__.__name__):
                d = dict(o.__dict__)
                if allowed_fields := getattr(o, "__dataclass_fields__", []):
                    d = {k: v for k, v in o.__dict__.items() if k in allowed_fields}
                for ex in getattr(o, "_json_exclude", []):
                    d.pop(ex)
                d["_class"] = cls.__name__
                return d

            return super().default(o)

    @classmethod
    def object_hook(cls, o: dict) -> object:
        if ObjectClass := cls.ALLOWED_CLASSES.get(o.get("_class", "")):
            o.pop("_class")
            return ObjectClass(**o)

        if len(o) == 1:
            match dict(o).popitem():
                case "__hex", val:
                    return bytes.fromhex(val)
                case "__path", val:
                    return pathlib.Path(val)
                case "__datetime", val:
                    return datetime.datetime.fromisoformat(val)
                case "__CScript", val:
                    return script.CScript(bytes.fromhex(val))
                case "__CTransaction", val:
                    return script.CTransaction.fromhex(val)

        return o

    @classmethod
    def dumps(cls, *args, **kwargs):
        return json.dumps(*args, cls=cls.Encoder, **kwargs)

    @classmethod
    def loads(cls, *args, **kwargs):
        return json.loads(*args, object_hook=VSJson.object_hook, **kwargs)
