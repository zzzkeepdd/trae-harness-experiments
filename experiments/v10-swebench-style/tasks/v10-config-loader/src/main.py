import json
import os
import re

class ConfigLoader:
    def __init__(self, defaults=None):
        self._config = {}
        if defaults:
            for k, v in defaults.items():
                self._config[k] = v
        self._loaded_files = set()
        self._schema = {}

    def set_schema(self, schema):
        self._schema = schema

    def load_json(self, filepath):
        norm = os.path.normpath(os.path.abspath(filepath))
        if norm in self._loaded_files:
            return
        if not os.path.isfile(norm):
            raise FileNotFoundError(f"config file not found: {norm}")
        try:
            with open(norm, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid JSON in {norm}: {e}")
        if not isinstance(data, dict):
            raise ValueError(f"config root must be a dict, got {type(data)}")
        for k, v in data.items():
            expected = self._schema.get(k)
            if expected is not None and not isinstance(v, expected):
                raise TypeError(f"config key '{k}' expected {expected}, got {type(v)}")
        self._config.update(data)
        self._loaded_files.add(norm)

    def load_env_override(self, prefix="APP_"):
        for key, val in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower()
                if val:
                    self._config[config_key] = val

    def get(self, key, default=None):
        return self._config.get(key, default)

    def get_int(self, key, default=0):
        try:
            return int(self._config[key])
        except KeyError:
            return default
        except (ValueError, TypeError):
            return default

    def get_bool(self, key, default=False):
        val = self._config.get(key)
        if val is None:
            return default
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return bool(val)
        return str(val).strip().lower() in ("true", "yes", "1", "on")

    def get_list(self, key, separator=",", default=None):
        val = self._config.get(key)
        if val is None:
            return default if default is not None else []
        if isinstance(val, list):
            return list(val)
        if isinstance(val, str) and separator in val:
            return [x.strip() for x in val.split(separator) if x.strip()]
        return [str(val).strip()] if str(val).strip() else []

    def get_all(self):
        return dict(self._config)

    def validate_required(self, required_keys):
        missing = []
        for k in required_keys:
            if k not in self._config or self._config[k] is None:
                missing.append(k)
        if missing:
            raise ValueError(f"missing required config keys: {missing}")

    def resolve_variables(self):
        pattern = re.compile(r'\$\{(\w+)\}')
        resolved = {}
        for key in list(self._config.keys()):
            val = str(self._config[key])
            def make_replacer(k):
                def replacer(m):
                    ref = m.group(1)
                    return str(self._config.get(ref, ""))
                return replacer
            resolved[key] = pattern.sub(make_replacer(key), val)
        self._config.update(resolved)

    def has_key(self, key):
        return key in self._config
