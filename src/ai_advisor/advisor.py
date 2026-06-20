"""
advisor.py
----------
AI business advisor for customer churn — combines a personalised SHAP-driven
customer context with retrieved banking strategy documents to produce a full
analytical retention memo via a hosted LLM.

Pipeline per customer
---------------------
1. CustomerContextBuilder fetches the customer's profile, churn score, and
   personalised SHAP drivers from the database and the trained classifier
2. A structured plain-text summary is built from that context
3. RAGDocumentStore retrieves the most relevant strategy chunks, biased
   toward the customer's risk tier and segment
4. Both are assembled into a prompt and sent to the LLM
5. The LLM returns a full 8-section analytical essay

Dependencies
------------
    pip install huggingface_hub loguru

Usage
-----
    from src.ai_advisor.advisor import ChurnAdvisor

    advisor = ChurnAdvisor()
    print(advisor.advise("10eb03a7-efed-44d5-bb08-a23f9af1df08"))
"""

from huggingface_hub.errors import HfHubHTTPError
from huggingface_hub import InferenceClient
from loguru import logger

from src.ai_advisor.rag.document_store import RAGDocumentStore
from src.ai_advisor.context_builder import CustomerContextBuilder
from config.settings import HF_TOKEN, HF_MODEL


# ---------------------------------------------------------------------------
# System prompt — the 8-section analytical essay format
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a senior banking analyst and customer retention 
specialist at a South African retail bank. Your role is to produce deep, 
insightful written reports on individual customers who are at risk of churning.

You will be given a churn risk tier and probability, personalised SHAP feature 
importance values, a customer profile drawn from the bank's database, and 
excerpts from internal financial advisory and retention strategy documents.

Your output must be a single, well-structured analytical essay — NOT a 
conversation, NOT bullet points, NOT a Q&A. Write in flowing, professional 
prose organised into clearly labelled sections.

The essay must cover ALL of the following sections in order:

1. EXECUTIVE SUMMARY
   A concise paragraph summarising the customer's churn risk, the confidence 
   of the prediction, and the single most critical factor driving it.

2. CUSTOMER PROFILE OVERVIEW
   Describe who this customer is — their lifecycle stage, segment, tenure, 
   activity level, and product holdings — in business terms a relationship 
   manager would immediately recognise.

3. WHY THIS CUSTOMER MAY LEAVE
   A detailed analysis of the behavioural, financial, and experiential signals 
   that indicate this customer is considering leaving. Explain each major SHAP 
   driver in plain business language — what it means, why it matters, and what 
   it tells us about the customer's state of mind or financial situation.

4. CONTRIBUTING FACTORS IN DEPTH
   Go deeper on the interplay between factors. Explain how the combination of 
   signals (e.g. zero balance + inactivity + single product) compounds the risk 
   beyond what each factor alone would suggest. Reference the strategy 
   documents where relevant to support the analysis.

5. FINANCIAL IMPACT ASSESSMENT
   Estimate the potential revenue impact of losing this customer based on their 
   salary, balance, product holdings, and segment. Frame this in terms of 
   lifetime value and opportunity cost to the bank.

6. RETENTION STRATEGY AND REMEDIES
   Recommend a specific, prioritised retention plan for this customer. Each 
   recommendation must be directly tied to one or more of the identified risk 
   factors. Include short-term actions (next 7 days), medium-term actions 
   (next 30 days), and longer-term relationship-building strategies.

7. ESCALATION AND URGENCY
   State clearly whether this case requires immediate escalation, which team 
   should own it, and what the consequence is of inaction within a given 
   timeframe.

8. CONCLUSION
   A closing paragraph summarising the overall assessment and the single most 
   important action the relationship manager must take.

Write with authority, precision, and empathy. Ground every claim in the data 
provided. Do not invent facts not supported by the customer data or documents."""


class ChurnAdvisor:
    """
    End-to-end churn advisory for a single customer, built around a
    CustomerContextBuilder and a RAGDocumentStore.
    """

    def __init__(
        self,
        persist_dir: str = "data/chroma_db",
        model_type: str  = "random_forest",
    ):
        self.store            = RAGDocumentStore(persist_dir=persist_dir)
        self.client            = InferenceClient(api_key=HF_TOKEN)
        self.context_builder   = CustomerContextBuilder(model_type=model_type)

    # ------------------------------------------------------------------
    # Summary builder — banking domain, SHAP-aware
    # ------------------------------------------------------------------

    def _build_customer_summary(self, context: dict) -> str:
        """Build a structured natural-language summary from the context dict."""
        account  = context.get("account_info", {})
        product  = context.get("product_signals", {})
        support  = context.get("support_signals", {})
        behavior = context.get("behavioral_signals", {})
        drivers  = context.get("top_churn_drivers", [])

        if drivers:
            driver_lines = "\n".join(
                f"  {i+1}. {d['feature']:28s}  SHAP={d['value']:+.4f}  "
                f"{'▲' if d['value'] > 0 else '▼'} {d['direction']}"
                for i, d in enumerate(drivers)
            )
        else:
            driver_lines = "  No personalised SHAP drivers available for this customer."

        return (
            f"Customer ID:          {context.get('customer_id', 'Unknown')}\n"
            f"Churn Probability:    {context.get('churn_probability', 0):.0%}\n"
            f"Risk Tier:            {context.get('risk_tier', 'N/A')}\n"
            "\n── Customer Profile ──\n"
            f"  Surname:            {account.get('surname', 'N/A')}\n"
            f"  Province:           {account.get('geography', 'N/A')}\n"
            f"  Gender / Age:       {account.get('gender', 'N/A')}, {account.get('age', 'N/A')}\n"
            f"  Tenure (months):    {account.get('tenure_months', 'N/A')}\n"
            f"  Card Type:          {account.get('card_type', 'N/A')}\n"
            f"  Credit Score:       {account.get('credit_score', 'N/A')}\n"
            f"  Segment:            {account.get('customer_segment', 'N/A')}\n"
            f"  Lifecycle Stage:    {account.get('lifecycle_stage', 'N/A')}\n"
            f"  Estimated Salary:   R{account.get('estimated_salary', 0):,.0f}\n"
            "\n── Product Holdings ──\n"
            f"  Number of Products: {product.get('num_products', 'N/A')}\n"
            f"  Total Balance:      R{product.get('total_balance', 0):,.0f}\n"
            f"  Single Product:     {product.get('is_single_product', 'N/A')}\n"
            f"  Zero Balance:       {product.get('has_zero_balance', 'N/A')}\n"
            "\n── Support History ──\n"
            f"  Open Complaint:     {support.get('has_complaint', 'N/A')}\n"
            f"  Satisfaction Score: {support.get('satisfaction_score', 'N/A')}/5 "
            f"({support.get('satisfaction_band', 'N/A')})\n"
            f"  High-Risk Support:  {support.get('is_high_risk_support', 'N/A')}\n"
            "\n── Behavioural Signals ──\n"
            f"  Active Member:      {behavior.get('is_active_member', 'N/A')}\n"
            f"  Loyalty Points:     {behavior.get('points_earned', 'N/A')}\n"
            f"  Card Engagement:    {behavior.get('card_engagement_score', 'N/A')}\n"
            f"  Activity Drop Flag: {behavior.get('activity_drop_flag', 'N/A')}\n"
            "\n── Top Churn Drivers (Personalised SHAP) ──\n"
            f"{driver_lines}"
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def advise(self, customer_id: str) -> str:
        """
        Main entry point. Pass a customer_id, get back the full advisory essay.
        """
        context = self.context_builder.build_context(customer_id)

        if context.get("context") == "No data available to build context":
            return f"No data found for customer {customer_id}. Cannot generate advice."

        summary = self._build_customer_summary(context)

        # ── Build a retrieval query from top SHAP drivers + risk tier ──
        top_features = [d["feature"] for d in context.get("top_churn_drivers", [])[:3]]
        segment       = context.get("account_info", {}).get("customer_segment", "general")
        risk_tier     = context.get("risk_tier", "unknown")

        rag_query = (
            f"customer retention strategies for {risk_tier.lower()} churn risk "
            f"in the {segment} segment, factors: "
            f"{', '.join(top_features) if top_features else 'general disengagement'}"
        )

        rag_context = {"risk_tier": risk_tier, "segment": segment}

        docs = self.store.retrieve(query=rag_query, top_k=5, customer_context=rag_context)

        context_block = (
            "\n\n".join(
                f"[{doc['doc_id']}] (relevance score: {doc['score']:.3f})\n{doc['content']}"
                for doc in docs
            )
            if docs
            else "No supporting documents retrieved. Base the analysis solely on "
                 "the customer data and SHAP drivers above."
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"## Relevant strategy documents:\n{context_block}\n\n"
                    f"## Current customer situation:\n{summary}\n\n"
                    "---\n"
                    "Using ALL of the information above, write the full 8-section "
                    "analytical essay as instructed. Write in flowing professional "
                    "prose. Do not use bullet points. Do not ask clarifying "
                    "questions. Output the essay only."
                ),
            },
        ]

        try:
            response = self.client.chat_completion(
                messages=messages,
                model=HF_MODEL,
                max_tokens=3000,
                temperature=0.3,
            )
            advice = response.choices[0].message.content.strip()
            logger.success(f"Advisory generated for customer {customer_id}")
            return advice

        except HfHubHTTPError as e:
            logger.error(f"LLM service unavailable: {e}")
            return "AI advisor temporarily unavailable. Please retry."

    def advise_batch(self, customer_ids: list[str]) -> dict[str, str]:
        """Generate advisories for multiple customers, one call each."""
        logger.info(f"Batch advise: {len(customer_ids)} customers")
        return {cid: self.advise(cid) for cid in customer_ids}


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    advisor = ChurnAdvisor()

    customer_id = "47b23f9e-906a-426f-959c-077bc762e18b"

    print("\n" + "=" * 65)
    print("  CHURN ADVISORY MEMO")
    print("=" * 65 + "\n")

    advice = advisor.advise(customer_id)
    print(advice)