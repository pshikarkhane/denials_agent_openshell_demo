"""Path guard. Skills read ONLY from CASE_ROOT (task.md + docs/**), POLICY_ROOT (policy library) and, for validating the model's own
output, OUTPUT_ROOT. Defense in depth: any path with `..`, any path outside those roots (after resolving symlinks), and any file or
folder named truth.json, rubric.json, gold or attacks is refused and logged as a denied access event. A root that itself contains such
an entry is refused too, so pointing CASE_ROOT at a raw data/cases/<id> folder (which holds truth.json) fails closed."""
import os
from pathlib import Path, PurePosixPath

DENIED_NAMES = {"truth.json", "rubric.json", "gold", "attacks"}


class AccessDenied(Exception):
    code = "access_denied"


def _parts(rel):
    return PurePosixPath(str(rel).replace("\\", "/")).parts


class PathGuard:
    def __init__(self, case_root=None, policy_root=None, output_root=None, events=None):
        self.events = events
        env = os.environ.get
        self.roots = {"case": case_root or env("CASE_ROOT"), "policy": policy_root or env("POLICY_ROOT"), "output": output_root or env("OUTPUT_ROOT")}
        self.roots = {k: (Path(v).resolve() if v else None) for k, v in self.roots.items()}
        for kind, root in self.roots.items():
            if root is not None:
                self._assert_clean_root(kind, root)

    # ------------------------------------------------------------------ checks
    def _deny(self, kind, rel, reason):
        if self.events is not None:
            self.events.log("path_guard", {"root": kind, "path": str(rel)}, reason, 0, status="denied", error=reason)
        raise AccessDenied(f"access denied ({kind}): {rel!r}: {reason}")

    def _assert_clean_root(self, kind, root):
        if not root.exists():
            return
        for p in [root, *root.rglob("*")]:
            if p.name.lower() in DENIED_NAMES:
                self._deny(kind, p.name, f"root contains a forbidden entry named {p.name!r}; stage a clean copy (task.md + docs/** only)")

    def resolve(self, kind, rel):
        root = self.roots.get(kind)
        if root is None:
            self._deny(kind, rel, f"{kind} root is not configured")
        s = str(rel)
        for part in _parts(s):
            if part == "..":
                self._deny(kind, rel, "path contains '..'")
            if part.lower() in DENIED_NAMES:
                self._deny(kind, rel, f"path contains forbidden name {part!r}")
        cand = Path(s) if os.path.isabs(s) else root / s
        resolved = cand.resolve()
        try:
            inside = resolved.relative_to(root)
        except ValueError:
            self._deny(kind, rel, f"outside the {kind} root")
        for part in inside.parts:
            if part.lower() in DENIED_NAMES:
                self._deny(kind, rel, f"resolves to a forbidden name {part!r}")
        if kind == "case" and inside.parts and inside.parts[0] not in ("task.md", "docs"):
            self._deny(kind, rel, "case root exposes only task.md and docs/**")
        return resolved

    # ------------------------------------------------------------------ reads
    def read_text(self, kind, rel):
        p = self.resolve(kind, rel)
        if not p.is_file():
            raise FileNotFoundError(f"{kind}:{rel} does not exist")
        return p.read_text()

    def list_files(self, kind, subdir=""):
        """Relative POSIX paths of files under root/subdir (sorted); forbidden names never listed."""
        base = self.resolve(kind, subdir) if subdir else self.roots[kind]
        if base is None or not base.exists():
            return []
        root = self.roots[kind]
        out = []
        for p in sorted(base.rglob("*")):
            rel = p.relative_to(root)
            if p.is_file() and not any(x.lower() in DENIED_NAMES for x in rel.parts):
                out.append(rel.as_posix())
        return out

    def exists(self, kind, rel):
        try:
            return self.resolve(kind, rel).is_file()
        except AccessDenied:
            return False
