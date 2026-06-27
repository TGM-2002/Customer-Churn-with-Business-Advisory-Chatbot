from __future__ import annotations

from functools import lru_cache

from huggingface_hub.errors import HfHubHTTPError

from src.ai_advisor.advisor import ChurnAdvisor
from config.settings import HF_MODEL

_QUERY_SYSTEM_PROMPT = (
    "You are a senior banking analyst and customer retention specialist at a South African retail bank. "
    "You will be given a customer profile including their churn risk, key drivers, and financial details. "
    "Answer the analyst's question concisely, grounding every claim in the provided customer data. "
    "Write in professional prose. Do not invent facts not present in the data."
)


@lru_cache(maxsize=1)
def _get_advisor() -> ChurnAdvisor:
    return ChurnAdvisor()


def generate_advisory(customer_id: str) -> str:
    """Generate the full 8-section retention memo for a customer."""
    return _get_advisor().advise(customer_id)


def answer_query(customer_id: str, query: str) -> str:
    """Answer a free-form analyst question about a specific customer."""
    advisor = _get_advisor()
    context = advisor.context_builder.build_context(customer_id)

    if context.get("context") == "No data available to build context":
        raise ValueError(f"No data found for customer {customer_id}")

    summary = advisor._build_customer_summary(context)

    messages = [
        {"role": "system", "content": _QUERY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"## Customer data:\n{summary}\n\n"
                f"## Analyst question:\n{query}"
            ),
        },
    ]

    try:
        response = advisor.client.chat_completion(
            messages=messages,
            model=HF_MODEL,
            max_tokens=1500,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except HfHubHTTPError as exc:
        raise RuntimeError("AI advisor temporarily unavailable. Please retry.") from exc
