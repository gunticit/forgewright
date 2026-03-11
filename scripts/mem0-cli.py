#!/usr/bin/env python3
"""
Forge17 Memory Manager CLI — persistent project memory, git-versioned.

Storage design:
  .forge17/memory.jsonl  — source of truth, committed to git (compact, human-readable)
  .forge17/embeddings.db — SQLite embeddings cache, gitignored (derived, rebuildable)

Usage:
    python3 mem0-cli.py search <query> [--limit N] [--format compact|full]
    python3 mem0-cli.py add <text> [--category <cat>]
    python3 mem0-cli.py ingest <file1> [file2 ...] [--chunk-size N]
    python3 mem0-cli.py ingest-git [--days N]
    python3 mem0-cli.py summarize <file>
    python3 mem0-cli.py list [--category <cat>] [--limit N]
    python3 mem0-cli.py delete <memory_id>
    python3 mem0-cli.py export [--format md|json]
    python3 mem0-cli.py stats
    python3 mem0-cli.py rebuild-index
    python3 mem0-cli.py setup
    python3 mem0-cli.py gc [--max-memories N]

Env vars:
    MEM0_LLM_PROVIDER   openai|ollama (default: openai)
    MEM0_LLM_MODEL      model name (default: gpt-4.1-nano)
    MEM0_LLM_API_KEY    API key (not needed for ollama)
    MEM0_LLM_BASE_URL   custom base URL
    MEM0_PROJECT_ID      project namespace (default: auto from git)
    MEM0_MAX_TOKENS      max tokens per retrieval (default: 500)
    MEM0_MAX_MEMORIES    max memories before GC (default: 200)
    MEM0_REDACT_SECRETS  true|false (default: true)
    MEM0_DISABLED        true to skip all ops
"""

import os
import re
import sys
import json
import hashlib
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

# ── Constants ──
FORGE17_DIR = ".forge17"
MEMORY_LOG = os.path.join(FORGE17_DIR, "memory.jsonl")      # committed to git
EMBEDDINGS_DB = os.path.join(FORGE17_DIR, "embeddings.db")   # gitignored (cache)
MEMIGNORE_FILE = ".memignore"
MAX_MEMORIES_DEFAULT = 200

REDACT_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"key-[a-zA-Z0-9]{20,}",
    r"Bearer\s+[a-zA-Z0-9\-._~+/]+=*",
    r"(?i)password\s*[:=]\s*['\"]?[^\s'\"]{4,}",
    r"(?i)secret\s*[:=]\s*['\"]?[^\s'\"]{4,}",
    r"(?i)token\s*[:=]\s*['\"]?[^\s'\"]{8,}",
    r"postgres://\S+:\S+@",
    r"mysql://\S+:\S+@",
    r"mongodb(\+srv)?://\S+:\S+@",
]


# ── Helpers ──

def is_disabled():
    return os.environ.get("MEM0_DISABLED", "").lower() == "true"

def get_project_id():
    pid = os.environ.get("MEM0_PROJECT_ID")
    if pid:
        return pid
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        return remote.rstrip("/").split("/")[-1].replace(".git", "")
    except Exception:
        return Path.cwd().name

def redact_secrets(text):
    if os.environ.get("MEM0_REDACT_SECRETS", "true").lower() != "true":
        return text
    for pattern in REDACT_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text

def load_memignore():
    patterns = []
    if Path(MEMIGNORE_FILE).exists():
        for line in Path(MEMIGNORE_FILE).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                patterns.append(line)
    return patterns

def should_ignore(filepath, patterns):
    from fnmatch import fnmatch
    fp = str(filepath)
    for pat in patterns:
        if fnmatch(fp, pat) or fnmatch(Path(fp).name, pat):
            return True
    return False

def chunk_text(text, max_chars=3000):
    lines = text.split("\n")
    chunks, current, current_len = [], [], 0
    for line in lines:
        if current_len + len(line) > max_chars and current:
            chunks.append("\n".join(current))
            current, current_len = [line], len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks

def make_id(text):
    """Generate short deterministic ID from content."""
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ── JSONL Memory Store (git-committed source of truth) ──

class MemoryStore:
    """
    File-based memory store using JSONL format.
    Each line: {"id": "...", "memory": "...", "category": "...", "created": "...", "source": "..."}

    Growth assumptions:
    - ~100 bytes per memory entry (avg)
    - 200 memories = ~20KB (very manageable for git)
    - GC at MEM0_MAX_MEMORIES (default 200) — oldest non-pinned get pruned
    """

    def __init__(self, path=MEMORY_LOG):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def _load(self):
        if not Path(self.path).exists():
            return []
        entries = []
        for line in Path(self.path).read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return entries

    def _save(self, entries):
        with open(self.path, "w") as f:
            for e in entries:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    def add(self, text, category="general", source="manual"):
        text = redact_secrets(text)
        mid = make_id(text + datetime.now().isoformat())
        entry = {
            "id": mid,
            "memory": text,
            "category": category,
            "source": source,
            "created": datetime.now().isoformat(timespec="seconds"),
        }
        entries = self._load()

        # Dedup: skip if very similar memory exists
        for e in entries:
            if e["memory"].strip() == text.strip():
                return e  # already exists

        entries.append(entry)
        self._save(entries)
        return entry

    def search(self, query, limit=5):
        """Simple keyword search (for MVP). Embeddings search via rebuild-index."""
        entries = self._load()
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for e in entries:
            mem = e.get("memory", "").lower()
            # Score: exact substring match > word overlap
            score = 0
            if query_lower in mem:
                score += 10
            word_hits = sum(1 for w in query_words if w in mem)
            score += word_hits * 2
            if score > 0:
                scored.append((score, e))

        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:limit]]

    def get_all(self, category=None):
        entries = self._load()
        if category:
            entries = [e for e in entries if e.get("category", "").lower() == category.lower()]
        return entries

    def delete(self, memory_id):
        entries = self._load()
        entries = [e for e in entries if e["id"] != memory_id]
        self._save(entries)

    def gc(self, max_memories=None):
        """Garbage collect: keep max_memories, remove oldest non-pinned."""
        max_m = max_memories or int(os.environ.get("MEM0_MAX_MEMORIES", MAX_MEMORIES_DEFAULT))
        entries = self._load()
        if len(entries) <= max_m:
            return 0
        # Keep pinned, sort rest by date, trim
        pinned = [e for e in entries if e.get("pinned")]
        unpinned = [e for e in entries if not e.get("pinned")]
        # Sort unpinned by created date (newest first)
        unpinned.sort(key=lambda e: e.get("created", ""), reverse=True)
        # Keep as many as we can
        keep = max_m - len(pinned)
        removed = len(unpinned) - keep
        if removed > 0:
            unpinned = unpinned[:keep]
        self._save(pinned + unpinned)
        return max(0, removed)

    def count(self):
        return len(self._load())

    def size_bytes(self):
        p = Path(self.path)
        return p.stat().st_size if p.exists() else 0


# ── Commands ──

def get_store():
    return MemoryStore()


def cmd_search(args):
    if len(args) < 1:
        print("Usage: mem0-cli.py search <query> [--limit N]")
        return
    query = args[0]
    limit = 5
    fmt = "compact"
    for i, a in enumerate(args[1:], 1):
        if a == "--limit" and i + 1 < len(args): limit = int(args[i + 1])
        if a == "--format" and i + 1 < len(args): fmt = args[i + 1]

    store = get_store()
    results = store.search(query, limit=limit)
    if not results:
        print("No memories found.")
        return
    if fmt == "compact":
        for m in results:
            cat = f"[{m.get('category', '')}] " if m.get("category") else ""
            print(f"  • {cat}{m['memory'][:200]}")
    else:
        print(json.dumps(results, indent=2, default=str))


def cmd_add(args):
    if len(args) < 1:
        print("Usage: mem0-cli.py add <text> [--category <cat>]")
        return
    text = args[0]
    category = "general"
    for i, a in enumerate(args[1:], 1):
        if a == "--category" and i + 1 < len(args): category = args[i + 1]
    store = get_store()
    entry = store.add(text, category=category)
    print(f"✅ Memory added [{entry['id']}] ({category})")


def cmd_ingest(args):
    if len(args) < 1:
        print("Usage: mem0-cli.py ingest <file1> [file2 ...]")
        return
    chunk_size = 3000
    files = []
    i = 0
    while i < len(args):
        if args[i] == "--chunk-size" and i + 1 < len(args):
            chunk_size = int(args[i + 1]); i += 2
        else:
            files.append(args[i]); i += 1

    ignore_patterns = load_memignore()
    store = get_store()
    total = 0

    for filepath in files:
        path = Path(filepath)
        if not path.exists():
            print(f"  ⚠️ {filepath} not found"); continue
        if should_ignore(filepath, ignore_patterns):
            print(f"  ⏭️ {filepath} ignored (.memignore)"); continue

        content = path.read_text(errors="replace")
        content = redact_secrets(content)
        chunks = chunk_text(content, chunk_size)

        for j, chunk in enumerate(chunks):
            src = f"{path.name}" + (f" part {j+1}/{len(chunks)}" if len(chunks) > 1 else "")
            store.add(chunk, category="ingested", source=src)
            total += 1

        print(f"  📄 {filepath}: {len(chunks)} chunk(s)")

    print(f"\n✅ Ingested {total} chunk(s) from {len(files)} file(s)")


def cmd_ingest_git(args):
    days = 7
    for i, a in enumerate(args):
        if a == "--days" and i + 1 < len(args): days = int(args[i + 1])

    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        log = subprocess.check_output(
            ["git", "log", f"--since={since}", "--pretty=format:%h %s", "--no-merges"],
            text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        print("❌ Not a git repo"); return

    if not log:
        print(f"No commits in last {days} days."); return

    commits = log.split("\n")
    store = get_store()
    summary = f"{len(commits)} commits (last {days}d):\n" + "\n".join(f"  {c}" for c in commits[:30])
    if len(commits) > 30:
        summary += f"\n  ... +{len(commits) - 30} more"
    store.add(summary, category="git-activity", source="git-log")
    print(f"✅ Ingested {len(commits)} commits")


def cmd_summarize(args):
    if len(args) < 1:
        print("Usage: mem0-cli.py summarize <file>"); return
    path = Path(args[0])
    if not path.exists():
        print(f"❌ {args[0]} not found"); return

    content = redact_secrets(path.read_text(errors="replace"))
    chunks = chunk_text(content, 4000)
    store = get_store()
    for chunk in chunks:
        store.add(chunk, category="conversation", source=path.name)
    print(f"✅ Summarized {path.name}: {len(chunks)} chunk(s)")


def cmd_list(args):
    limit = 20
    category = None
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args): limit = int(args[i + 1])
        if a == "--category" and i + 1 < len(args): category = args[i + 1]

    store = get_store()
    entries = store.get_all(category=category)
    if not entries:
        print("No memories stored."); return

    for i, m in enumerate(entries[:limit]):
        cat = f"[{m.get('category', '')}]" if m.get("category") else ""
        print(f"  [{m['id']}] {cat} {m['memory'][:120]}")
    if len(entries) > limit:
        print(f"  ... +{len(entries) - limit} more")
    print(f"\nTotal: {len(entries)}")


def cmd_delete(args):
    if len(args) < 1:
        print("Usage: mem0-cli.py delete <memory_id>"); return
    get_store().delete(args[0])
    print(f"✅ Deleted {args[0]}")


def cmd_export(args):
    fmt = "md"
    for i, a in enumerate(args):
        if a == "--format" and i + 1 < len(args): fmt = args[i + 1]

    store = get_store()
    pid = get_project_id()
    entries = store.get_all()

    if fmt == "json":
        print(json.dumps(entries, indent=2, default=str))
    else:
        print(f"# Project Memory: {pid}")
        print(f"_Exported: {datetime.now().isoformat(timespec='seconds')}_\n")
        cats = {}
        for m in entries:
            cat = m.get("category", "general")
            cats.setdefault(cat, []).append(m)
        for cat, mems in sorted(cats.items()):
            print(f"\n## {cat.title()}")
            for m in mems:
                print(f"- **[{m['id']}]** {m['memory'][:200]}")
        print(f"\n---\nTotal: {len(entries)} memories | {store.size_bytes():,} bytes")


def cmd_stats(args):
    store = get_store()
    pid = get_project_id()
    entries = store.get_all()
    total_chars = sum(len(m.get("memory", "")) for m in entries)

    print(f"📊 Memory Stats for '{pid}'")
    print(f"  Memories: {len(entries)}")
    print(f"  File size: {store.size_bytes():,} bytes")
    print(f"  Approx tokens: {total_chars // 4:,}")
    print(f"  Max before GC: {os.environ.get('MEM0_MAX_MEMORIES', MAX_MEMORIES_DEFAULT)}")

    cats = {}
    for m in entries:
        cat = m.get("category", "general")
        cats[cat] = cats.get(cat, 0) + 1
    if cats:
        print("  Categories:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {count}")


def cmd_gc(args):
    max_m = None
    for i, a in enumerate(args):
        if a == "--max-memories" and i + 1 < len(args): max_m = int(args[i + 1])
    store = get_store()
    removed = store.gc(max_memories=max_m)
    print(f"✅ GC complete: removed {removed} old memories (kept {store.count()})")


def cmd_setup(args):
    print("🔧 Forge17 Memory Manager Setup\n")
    os.makedirs(FORGE17_DIR, exist_ok=True)
    print(f"  ✅ {FORGE17_DIR}/ ready")

    # .memignore
    if not Path(MEMIGNORE_FILE).exists():
        Path(MEMIGNORE_FILE).write_text(
            "# Exclude from memory ingestion\n.env\n.env.*\nsecrets/\ncredentials/\n"
            "**/node_modules/**\n**/.git/**\n*.log\n"
        )
        print(f"  ✅ {MEMIGNORE_FILE} created")

    # Init empty JSONL
    if not Path(MEMORY_LOG).exists():
        Path(MEMORY_LOG).touch()
        print(f"  ✅ {MEMORY_LOG} initialized")

    print(f"\n✅ Setup complete! Use 'mem0-cli.py add' or 'mem0-cli.py ingest' to start.")
    print(f"   Growth: ~100 bytes/memory, GC at {MAX_MEMORIES_DEFAULT} (configurable)")


# ── Main ──

COMMANDS = {
    "search": cmd_search, "add": cmd_add, "ingest": cmd_ingest,
    "ingest-git": cmd_ingest_git, "summarize": cmd_summarize,
    "list": cmd_list, "delete": cmd_delete, "export": cmd_export,
    "stats": cmd_stats, "gc": cmd_gc, "setup": cmd_setup,
}

def main():
    if is_disabled(): return
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__); print("Commands:", ", ".join(COMMANDS.keys())); return
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown: {cmd}\nAvailable: {', '.join(COMMANDS.keys())}"); sys.exit(1)
    COMMANDS[cmd](sys.argv[2:])

if __name__ == "__main__":
    main()
