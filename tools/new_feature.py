"""Guided walkthrough for adding a new entry to FEATURE_IDEAS.md.

Run with:
    python tools/new_feature.py

Uses Rich for pretty output and Questionary for interactive prompts.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import questionary
from questionary import Choice
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

console = Console()

REPO_ROOT = Path(__file__).resolve().parent.parent
FEATURE_FILE = REPO_ROOT / "FEATURE_IDEAS.md"
IDEAS_DIR = REPO_ROOT / "ideas"

MAX_NAME_LEN = 20
MAX_DESC_LEN = 50

# tag_key -> (emoji, label shown in FEATURE_IDEAS.md index)
TAGS: dict[str, tuple[str, str]] = {
    "wip": ("🟪", "Work In Progress"),
    "od": ("🟦", "Outdated"),
    "ac": ("🟫", "Archived"),
    "ni": ("🟥", "needs issue"),
    "hp": ("🟨", "High Priority"),
    "lp": ("🟩", "Low Priority"),
    "lt": ("🟧", "Long Term"),
}


def validate_name(name: str) -> bool | str:
    """Questionary validator: name goes inside **...** so keep it short."""
    cleaned = name.strip()
    if not cleaned:
        return "Name can't be empty — give your feature a name!"
    if len(cleaned) > MAX_NAME_LEN:
        return f"Too long! ({len(cleaned)}/{MAX_NAME_LEN}) Keep it under {MAX_NAME_LEN} characters."
    if "**" in cleaned or "`" in cleaned or "\n" in cleaned:
        return "Please avoid `**`, backticks, or newlines — they break the markdown list."
    return True


def validate_description(desc: str) -> bool | str:
    """Questionary validator: short one-liner shown after the bold name."""
    cleaned = desc.strip()
    if not cleaned:
        return "Description can't be empty — one short line is enough!"
    if len(cleaned) > MAX_DESC_LEN:
        return f"Too long! ({len(cleaned)}/{MAX_DESC_LEN}) Keep it under {MAX_DESC_LEN} characters."
    if "`" in cleaned or "\n" in cleaned:
        return "Please avoid backticks or newlines — they break the markdown list."
    return True


def build_line(
    name: str, description: str, tag_keys: list[str], details_rel: str | None = None
) -> str:
    """Build a `- [ ] **Name** description `tags` [details](...)` markdown line."""
    name = name.strip()
    description = description.strip()
    tags_part = " ".join(f"`{TAGS[k][0]} {k}`" for k in tag_keys if k in TAGS)
    line = f"- [ ] **{name}**"
    if description:
        line += f" {description}"
    if tags_part:
        line += f" {tags_part}"
    if details_rel:
        # Forward slashes so the link works on GitHub + Windows checkouts.
        rel = details_rel.replace("\\", "/")
        line += f" [details]({rel})"
    return line


def slugify(name: str) -> str:
    """Turn 'Fishing System!' -> 'fishing-system' for use as ideas/<slug>.md."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    slug = slug.strip("-")
    return slug or "idea"


def unique_idea_path(name: str) -> tuple[Path, str]:
    """Return (absolute path, repo-relative posix path), bumping -2, -3 on clash."""
    base = slugify(name)
    candidate = IDEAS_DIR / f"{base}.md"
    counter = 2
    while candidate.exists():
        candidate = IDEAS_DIR / f"{base}-{counter}.md"
        counter += 1
    rel = f"ideas/{candidate.name}"
    return candidate, rel


def prompt_extended_description() -> str | None:
    """Collect unlimited multiline input. Single '.' on its own line finishes."""
    console.print()
    console.print("[bold]Extended description[/bold] [dim](unlimited, markdown OK)[/dim]")
    console.print(
        "[dim]Write as many lines as you want — blank lines are fine.\n"
        "Finish with a single [bold].[/bold] on its own line, then Enter.[/dim]"
    )
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == ".":
            break
        lines.append(line.rstrip())
    text = "\n".join(lines).strip()
    return text or None


def write_idea_file(
    path: Path, name: str, description: str, tag_keys: list[str], extended: str
) -> None:
    """Write ideas/<slug>.md with short desc + tags + full writeup."""
    tags_part = " ".join(f"`{TAGS[k][0]} {k}`" for k in tag_keys if k in TAGS)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        f"# {name.strip()}\n\n"
        f"> {description.strip()}\n\n"
        f"Tags: {tags_part}\n\n"
        f"## Details\n\n"
        f"{extended.strip()}\n\n"
        f"---\n"
        f"*Back to [FEATURE_IDEAS.md](../FEATURE_IDEAS.md)*\n"
    )
    path.write_text(content, encoding="utf-8")


def feature_name_exists(content: str, name: str) -> bool:
    """Case-insensitive check for an existing `**Name**` entry."""
    pattern = re.compile(r"\*\*" + re.escape(name.strip()) + r"\*\*", re.IGNORECASE)
    return pattern.search(content) is not None


def append_to_feature_file(line: str) -> None:
    """Append the new line under the `## List` section, creating it if needed."""
    if not FEATURE_FILE.exists():
        FEATURE_FILE.write_text("## List\n\n" + line + "\n", encoding="utf-8")
        return

    content = FEATURE_FILE.read_text(encoding="utf-8")

    if "## List" in content:
        # Append at end of file, keeping exactly one trailing newline.
        if not content.endswith("\n"):
            content += "\n"
        content += line + "\n"
    else:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n## List\n\n" + line + "\n"

    FEATURE_FILE.write_text(content, encoding="utf-8")


def main() -> int:
    console.print(Rule("✨ [bold]New MTT Feature Idea[/bold] ✨"))
    console.print(
        Panel(
            "This will walk you through adding one idea to [bold]FEATURE_IDEAS.md[/bold].\n"
            f"• [bold]Name[/bold]: bold text in **...**, max [cyan]{MAX_NAME_LEN}[/cyan] chars\n"
            f"• [bold]Description[/bold]: short one-liner, max [cyan]{MAX_DESC_LEN}[/cyan] chars\n"
            "• [bold]Tags[/bold]: pick any of wip / od / ac / ni / hp / lp / lt\n"
            "• [bold]Extended[/bold] (optional): unlimited writeup saved to [cyan]ideas/&lt;slug&gt;.md[/cyan]\n"
            "[dim]Press Ctrl+C at any time to cancel.[/dim]",
            title="How it works",
            border_style="magenta",
        )
    )

    try:
        name: str | None = questionary.text(
            f"Feature name (bold **...**, max {MAX_NAME_LEN} chars):",
            validate=validate_name,
        ).ask()
        if not name:
            console.print("[yellow]Cancelled — no name given.[/yellow]")
            return 1
        name = name.strip()

        description: str | None = questionary.text(
            f"Short description (max {MAX_DESC_LEN} chars):",
            validate=validate_description,
        ).ask()
        if not description:
            console.print("[yellow]Cancelled — no description given.[/yellow]")
            return 1
        description = description.strip()

        tag_keys: list[str] | None = questionary.checkbox(
            "Pick tag(s) — Space to select, Enter to confirm:",
            choices=[
                Choice(
                    title=f"{emoji} {key} — {label}",
                    value=key,
                )
                for key, (emoji, label) in TAGS.items()
            ],
            validate=lambda sel: True if sel else "Pick at least one tag!",
        ).ask()
        if not tag_keys:
            console.print("[yellow]Cancelled — no tags selected.[/yellow]")
            return 1

        want_extended: bool | None = questionary.confirm(
            "Add an extended description? (saves to ideas/<slug>.md + links it)",
            default=False,
        ).ask()
        extended: str | None = None
        idea_path: Path | None = None
        details_rel: str | None = None
        if want_extended:
            extended = prompt_extended_description()
            if not extended:
                console.print(
                    "[yellow]No extended text given — continuing without details file.[/yellow]"
                )
                extended = None
            else:
                idea_path, details_rel = unique_idea_path(name)

        line = build_line(name, description, tag_keys, details_rel)

        console.print()
        console.print(Rule("[bold]Preview[/bold]"))
        console.print(Panel(line, title="FEATURE_IDEAS.md entry", border_style="green"))
        if extended and idea_path is not None:
            preview_body = extended if len(extended) <= 800 else extended[:800] + "\n…(truncated)"
            console.print(
                Panel(preview_body, title=f"{details_rel} preview", border_style="cyan")
            )
        console.print(
            f"[dim]Name:[/dim] {len(name)}/{MAX_NAME_LEN}  "
            f"[dim]Description:[/dim] {len(description)}/{MAX_DESC_LEN}  "
            f"[dim]Tags:[/dim] {', '.join(tag_keys)}"
        )

        # Warn on duplicates but still allow adding.
        if FEATURE_FILE.exists():
            existing = FEATURE_FILE.read_text(encoding="utf-8")
            if feature_name_exists(existing, name):
                console.print(
                    f"[yellow]⚠ An entry called **{name}** already exists. "
                    "You can still add it, but consider a unique name.[/yellow]"
                )

        confirm: bool | None = questionary.confirm(
            "Add this to FEATURE_IDEAS.md?", default=True
        ).ask()
        if not confirm:
            console.print("[yellow]Not added — cancelled.[/yellow]")
            return 1

        append_to_feature_file(line)
        done_text = f"[green]✔ Added to [bold]FEATURE_IDEAS.md[/bold]![/green]\n{line}"
        if extended and idea_path is not None:
            write_idea_file(idea_path, name, description, tag_keys, extended)
            done_text += f"\n[green]✔ Saved extended writeup to [bold]{details_rel}[/bold]![/green]"
        console.print(
            Panel(
                done_text,
                title="Done 🎉",
                border_style="green",
            )
        )
        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        return 1


if __name__ == "__main__":
    sys.exit(main())
