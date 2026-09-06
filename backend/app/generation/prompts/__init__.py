from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PromptTemplates:
    """Localized prompt templates used by PromptBuilder."""

    chat_system: str
    no_context: str
    language_instruction: str
    source_header: str
    source_file_label: str
    source_context_label: str

    summary_system: str

    query_rewrite_system: str
    query_rewrite_input_label: str
    query_rewrite_output_label: str
