from __future__ import annotations


def build_topic_prompts(
    *,
    topic: str,
    additional_instructions: str,
    grounding_context: str = "",
    require_citations: bool = False,
) -> tuple[str, str]:
    normalized_topic = topic.strip()
    normalized_instructions = additional_instructions.strip()
    normalized_grounding = grounding_context.strip()

    system_prompt = (
        "You are an expert educator and technical writer. "
        "Provide accurate, highly informative, and well-structured explanations. "
        "When useful, include definitions, context, key concepts, examples, and practical applications."
    )
    if normalized_grounding:
        system_prompt += (
            " Source-grounded mode is enabled. Base claims on the provided sources and avoid unsupported assertions."
        )

    user_prompt = (
        f"Topic: {normalized_topic}\n\n"
        "Write a detailed, informative explanation that is easy to follow but deep enough for serious learning. "
        "Use clear section headings and concise paragraphs.\n"
        "Include: overview, core concepts, how it works, real-world use cases, benefits, limitations, "
        "and what to learn next."
    )
    if normalized_grounding:
        user_prompt += (
            "\n\nUse only the following sources as grounding context. "
            "When you use a source-backed claim, cite it inline with markers like [S1], [S2].\n\n"
            f"{normalized_grounding}"
        )
        if require_citations:
            user_prompt += (
                "\n\nCitation requirement:\n"
                "- Every major section should contain source citations.\n"
                "- Do not invent source IDs beyond those provided."
            )
    if normalized_instructions:
        user_prompt += f"\n\nAdditional instructions from user:\n{normalized_instructions}"
    return system_prompt, user_prompt
