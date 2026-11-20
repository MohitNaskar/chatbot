import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "knowledge"

_cached_context: str | None = None


def _load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_md(path: Path) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _build_context() -> str:
    sections: list[str] = []

    # Flat JSON knowledge files
    for name in ("profile", "experience", "skills", "achievements", "education"):
        path = KNOWLEDGE_DIR / f"{name}.json"
        if path.exists():
            try:
                data = _load_json(path)
                sections.append(f"## {name.title()}\n{json.dumps(data, indent=2)}")
            except Exception as e:
                logger.warning("Could not load %s: %s", path, e)

    # Project files
    projects_dir = KNOWLEDGE_DIR / "projects"
    if projects_dir.exists():
        for p in sorted(projects_dir.glob("*.json")):
            try:
                data = _load_json(p)
                label = data.get("name", p.stem) if isinstance(data, dict) else p.stem
                sections.append(f"## Project: {label}\n{json.dumps(data, indent=2)}")
            except Exception as e:
                logger.warning("Could not load %s: %s", p, e)

    # Technical notes markdown
    notes_dir = KNOWLEDGE_DIR / "technical_notes"
    if notes_dir.exists():
        for p in sorted(notes_dir.glob("*.md")):
            try:
                content = _load_md(p)
                title = p.stem.replace("_", " ").title()
                sections.append(f"## Technical Notes: {title}\n{content}")
            except Exception as e:
                logger.warning("Could not load %s: %s", p, e)

    context = "\n\n---\n\n".join(sections)
    logger.info("Knowledge base loaded — %d characters", len(context))
    return context


def get_context() -> str:
    global _cached_context
    if _cached_context is None:
        _cached_context = _build_context()
    return _cached_context
