from typing import Optional

from vcm_os.schemas import ContextPack


class PromptComposer:
    def compose(self, pack: ContextPack, user_query: str) -> str:
        sections = []
        for sec in pack.sections:
            if sec.content.strip():
                sections.append(f"## {sec.section_name.upper().replace('_', ' ')}\n{sec.content}")

        if pack.warnings:
            sections.append(f"## WARNINGS\n" + "\n".join(f"- {w}" for w in pack.warnings))

        if pack.forbidden_context:
            sections.append(f"## FORBIDDEN CONTEXT\n" + "\n".join(f"- {f}" for f in pack.forbidden_context))

        sections.append(f"## USER QUERY\n{user_query}")
        sections.append(
            "## ANSWER REQUIREMENTS\n"
            "- Give a concrete actionable response.\n"
            "- Cite memory IDs when relying on memory.\n"
            "- Do not claim files were changed unless tool output confirms it."
        )

        return "\n\n".join(sections)
