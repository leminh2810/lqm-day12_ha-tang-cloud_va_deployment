"""Lightweight legal multi-agent engine adapted from the Day 9 A2A lab.

The original Day 9 project runs Customer, Law, Tax, and Compliance agents as
separate A2A services backed by LangGraph. For the Day 12 final deployment we
keep the same specialist flow, but run it in-process so the app stays small,
Docker-friendly, and runnable without external LLM credentials.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, asdict


MAX_DELEGATION_DEPTH = 3


TAX_KEYWORDS = {
    "tax",
    "taxes",
    "irs",
    "evasion",
    "avoidance",
    "penalty",
    "penalties",
    "fbar",
    "fatca",
    "transfer pricing",
}

COMPLIANCE_KEYWORDS = {
    "compliance",
    "sec",
    "sox",
    "aml",
    "fcpa",
    "gdpr",
    "privacy",
    "regulation",
    "regulatory",
    "whistleblower",
    "governance",
}


@dataclass
class LegalAgentResult:
    trace_id: str
    context_id: str
    customer_summary: str
    law_analysis: str
    needs_tax: bool
    needs_compliance: bool
    tax_analysis: str | None
    compliance_analysis: str | None
    final_answer: str

    def model_dump(self) -> dict:
        return asdict(self)


def _contains_any(text: str, keywords: set[str]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def customer_agent(question: str) -> str:
    return (
        "Customer Agent accepted the question and delegated it to the legal "
        "orchestrator for specialist review."
    )


def law_agent(question: str) -> str:
    return (
        "Law Agent: The question should be analyzed for contract duties, "
        "business-law exposure, possible civil liability, and individual "
        "responsibility of decision makers. Preserve documents, identify the "
        "governing jurisdiction, and separate company liability from officer "
        "or director liability."
    )


def tax_agent(question: str) -> str:
    return (
        "- Tax exposure may include back taxes, interest, civil penalties, and audit risk.\n"
        "- Intentional evasion can trigger IRS investigation and DOJ Tax Division referral.\n"
        "- Executives who directed misconduct may face personal liability.\n"
        "Educational only; consult a licensed tax attorney."
    )


def compliance_agent(question: str) -> str:
    return (
        "Compliance Agent: Review SEC, SOX, AML, FCPA, privacy, and governance "
        "obligations based on the facts. Regulators may seek administrative, "
        "civil, or criminal remedies. Voluntary disclosure, cooperation, "
        "remediation, and a documented compliance program can reduce exposure."
    )


def route_specialists(question: str, depth: int) -> tuple[bool, bool]:
    if depth >= MAX_DELEGATION_DEPTH:
        return False, False

    needs_tax = _contains_any(question, TAX_KEYWORDS)
    needs_compliance = _contains_any(question, COMPLIANCE_KEYWORDS)

    # Day 9's Law Agent defaults toward specialist review when routing is
    # uncertain. Keep that conservative behavior for substantive legal prompts.
    if not needs_tax and not needs_compliance:
        legal_terms = {"contract", "company", "corporate", "law", "legal", "liability"}
        if _contains_any(question, legal_terms):
            needs_compliance = True

    return needs_tax, needs_compliance


def aggregate_answer(
    question: str,
    law_analysis: str,
    tax_analysis: str | None,
    compliance_analysis: str | None,
) -> str:
    sections = [
        "## Legal Analysis",
        law_analysis,
    ]

    if tax_analysis:
        sections.extend(["", "## Tax Analysis", tax_analysis])

    if compliance_analysis:
        sections.extend(["", "## Regulatory Compliance Analysis", compliance_analysis])

    sections.extend(
        [
            "",
            "## Practical Next Steps",
            "- Collect contracts, communications, accounting records, and board materials.",
            "- Identify jurisdictions, regulators, deadlines, and reporting obligations.",
            "- Escalate to licensed counsel before making admissions or disclosures.",
            "",
            "This analysis is educational and is not legal advice.",
        ]
    )
    return "\n".join(sections)


def run_legal_multi_agent(
    question: str,
    *,
    context_id: str | None = None,
    trace_id: str | None = None,
    depth: int = 0,
) -> LegalAgentResult:
    trace_id = trace_id or str(uuid.uuid4())
    context_id = context_id or str(uuid.uuid4())

    customer_summary = customer_agent(question)
    law_analysis = law_agent(question)
    needs_tax, needs_compliance = route_specialists(question, depth)

    tax_analysis = tax_agent(question) if needs_tax else None
    compliance_analysis = compliance_agent(question) if needs_compliance else None
    final_answer = aggregate_answer(
        question=question,
        law_analysis=law_analysis,
        tax_analysis=tax_analysis,
        compliance_analysis=compliance_analysis,
    )

    return LegalAgentResult(
        trace_id=trace_id,
        context_id=context_id,
        customer_summary=customer_summary,
        law_analysis=law_analysis,
        needs_tax=needs_tax,
        needs_compliance=needs_compliance,
        tax_analysis=tax_analysis,
        compliance_analysis=compliance_analysis,
        final_answer=final_answer,
    )
