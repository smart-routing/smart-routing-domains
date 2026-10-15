"""Generate services.json from a pinned domain-list-community checkout (stdlib only)."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "https://github.com/v2fly/domain-list-community"


class Parser:
    def __init__(self, data):
        self.data = Path(data)
        self.cache = {}
        self.affiliations = {}
        for path in self.data.iterdir():
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                parts = line.split("#", 1)[0].split()
                if not parts:
                    continue
                token, *options = parts
                kind, value = token.split(":", 1) if ":" in token else ("domain", token)
                targets = [o[1:] for o in options if o.startswith("&")]
                if targets and kind not in {"domain", "full", "keyword", "regexp"}:
                    raise ValueError(f"Unsupported affiliation on {token}")
                attrs = frozenset(o[1:].lower() for o in options if o.startswith("@"))
                for target in targets:
                    self.affiliations.setdefault(target, set()).add((kind, value.lower() if kind in {"domain", "full"} else value, attrs))

    def read(self, name, stack=()):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_.!-]*", name):
            raise ValueError(f"Invalid list name: {name!r}")
        if name in stack:
            raise ValueError(f"Include cycle: {' -> '.join((*stack, name))}")
        if name in self.cache:
            return self.cache[name]
        rules = set(self.affiliations.get(name, ()))
        path = self.data / name
        if not path.exists() and name not in self.affiliations:
            raise ValueError(f"Missing source list: {name}")
        lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        for number, line in enumerate(lines, 1):
            parts = line.split("#", 1)[0].split()
            if not parts:
                continue
            token, *options = parts
            kind, value = token.split(":", 1) if ":" in token else ("domain", token)
            if any(not option.startswith(("@", "&")) for option in options):
                raise ValueError(f"{name}:{number}: unknown option")
            attrs = frozenset(option[1:].lower() for option in options if option.startswith("@"))
            if kind == "include":
                included = self.read(value, (*stack, name))
                for rule in included:
                    if all((a[1:] not in rule[2]) if a.startswith("-") else (a in rule[2]) for a in attrs):
                        rules.add(rule)
            elif kind in {"domain", "full", "keyword", "regexp"} and value:
                if kind in {"domain", "full"}:
                    value = value.lower()
                    if not re.fullmatch(r"[a-z0-9_-]+(?:\.[a-z0-9_-]+)*", value):
                        raise ValueError(f"{name}:{number}: invalid domain {value!r}")
                rules.add((kind, value, attrs))
            else:
                raise ValueError(f"{name}:{number}: unknown or empty rule {token!r}")
        self.cache[name] = frozenset(rules)
        return self.cache[name]


def generate(config, checkout, revision):
    parser = Parser(Path(checkout) / "data")
    services = []
    ids = set()
    for entry in config["services"]:
        if entry["id"] in ids:
            raise ValueError(f"Duplicate service ID: {entry['id']}")
        ids.add(entry["id"])
        rules = parser.read(entry["sourceList"])
        service = {key: value for key, value in entry.items() if key != "sourceList"}
        service["domains"] = sorted({value for kind, value, _ in rules if kind == "domain"})
        service["exactDomains"] = sorted({value for kind, value, _ in rules if kind == "full"})
        if not service["domains"] and not service["exactDomains"]:
            raise ValueError(f"Empty domain list for {entry['id']}")
        service["source"] = f"https://raw.githubusercontent.com/v2fly/domain-list-community/{revision}/data/{entry['sourceList']}"
        service["omittedRules"] = len({(kind, value) for kind, value, _ in rules if kind in {"keyword", "regexp"}})
        services.append(service)
    return {"revision": revision, "source": SOURCE, "services": services}


def git(*args):
    return subprocess.check_output(["git", *map(str, args)], text=True).strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=ROOT / "services.config.json")
    ap.add_argument("--output", type=Path, default=ROOT / "services.json")
    ap.add_argument("--revision", default="master", help="Upstream branch, tag or commit")
    ap.add_argument("--checkout", type=Path, help="Use an existing upstream Git checkout without fetching")
    args = ap.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8-sig"))
    if config["source"] != SOURCE:
        raise ValueError(f"Only {SOURCE} is supported")
    with tempfile.TemporaryDirectory(prefix="domain-lists-") as directory:
        checkout = args.checkout
        if checkout is None:
            checkout = Path(directory) / "upstream"
            git("init", "--quiet", checkout)
            git("-C", checkout, "fetch", "--quiet", "--depth=1", SOURCE + ".git", args.revision)
            git("-C", checkout, "checkout", "--quiet", "--detach", "FETCH_HEAD")
        revision = git("-C", checkout, "rev-parse", "HEAD")
        if args.checkout and git("-C", checkout, "status", "--porcelain"):
            raise ValueError("Upstream checkout must be clean so revision matches the data")
        result = generate(config, checkout, revision)
    old = json.loads(args.output.read_text(encoding="utf-8-sig")) if args.output.exists() else None
    comparable = {key: value for key, value in (old or {}).items() if key != "updatedAt"}
    if result == comparable:
        print("services.json is unchanged")
        return
    result["updatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    # Replace only after every list has parsed and validated successfully.
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"Updated {args.output} from {revision}; {len(result['services'])} services")


if __name__ == "__main__":
    main()
