"""
TF-IDF/BM25 Vector Store — FraudGraph AI Phase 5B
===================================================
ChromaDB is not installed in this environment.  This module implements the lightweight
fallback using scikit-learn TF-IDF cosine similarity with the same public interface
so Phase 6 (LangGraph agent) can swap in ChromaDB with zero API changes.

What is indexed
---------------
  1. 5,565 closed cases  (dataset/HHGOA_IEEE/closed_cases_history.csv)
  2. 5 known fraud patterns          (from README.md "The five known fraud patterns")
  3. 10 regulatory references        (from README.md "Regulatory references" — title + URL)
  4. 10 policy rules R1–R10          (from README.md "Fraud Policy" section 3)

Source truth: ONLY text that exists in the project docs / dataset is indexed.
Nothing is invented.

Interface contract (shared with future ChromaDB implementation)
---------------------------------------------------------------
  FraudVectorStore.query(query_text, n=5, source_types=None) -> List[SearchResult]
  FraudVectorStore.get_by_id(doc_id) -> Optional[Document]
  FraudVectorStore.stats() -> Dict[str, int]
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Document model
# ---------------------------------------------------------------------------

@dataclass
class Document:
    doc_id: str
    text: str                       # searchable concatenated text
    source_type: str                # "closed_case" | "fraud_pattern" | "regulatory" | "policy_rule"
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Convenience accessors (present in metadata)
    @property
    def case_id(self) -> Optional[str]:
        return self.metadata.get("case_id")

    @property
    def rule_id(self) -> Optional[str]:
        return self.metadata.get("rule_id")

    @property
    def ref_name(self) -> Optional[str]:
        return self.metadata.get("ref_name")


@dataclass
class SearchResult:
    doc: Document
    score: float                    # cosine similarity, 0–1


# ---------------------------------------------------------------------------
# Regulatory references — titles and URLs as documented in README.md
# ---------------------------------------------------------------------------

REGULATORY_REFERENCES: List[Dict[str, str]] = [
    {
        "ref_id": "fincen-sar-faqs",
        "agency": "FinCEN",
        "title": "SAR Filing FAQs, October 2025",
        "url": "https://www.fincen.gov/system/files/2025-10/SAR-FAQs-October-2025.pdf",
        "summary": (
            "FinCEN SAR Filing FAQs: frequently asked questions about when and how to file "
            "Suspicious Activity Reports (SARs), required fields, timelines, and filing obligations "
            "for financial institutions under the Bank Secrecy Act."
        )
    },
    {
        "ref_id": "fincen-sar-narrative-guidance",
        "agency": "FinCEN",
        "title": "SAR Narrative Guidance",
        "url": "https://www.fincen.gov/system/files/shared/sar_guidance_narrative.pdf",
        "summary": (
            "FinCEN standard guidance for writing SAR narratives: who, what, when, where, how, "
            "and why suspicious activity occurred. This is the standard for sar.narrative in answer files."
        )
    },
    {
        "ref_id": "fincen-sar-complete-narrative",
        "agency": "FinCEN",
        "title": "Preparing a Complete and Sufficient SAR Narrative",
        "url": "https://www.fincen.gov/system/files/shared/sarnarrcompletguidfinal_112003.pdf",
        "summary": (
            "FinCEN guidance on preparing complete SAR narratives: the five W's (who, what, when, where, "
            "why), completeness requirements, and examples of sufficient versus insufficient narratives."
        )
    },
    {
        "ref_id": "fincen-sar-supporting-docs",
        "agency": "FinCEN",
        "title": "SAR Supporting Documentation (FIN-2007-G003)",
        "url": "https://www.fincen.gov/system/files/shared/fin-2007-g003.pdf",
        "summary": (
            "FinCEN FIN-2007-G003: guidance on retaining and producing SAR supporting documentation, "
            "record retention obligations, and disclosure rules."
        )
    },
    {
        "ref_id": "fincen-sar-activity-review",
        "agency": "FinCEN",
        "title": "SAR Activity Review: Trends, Tips and Issues",
        "url": "https://www.fincen.gov/sites/default/files/sar_report/sar_tti_19.pdf",
        "summary": (
            "FinCEN SAR Activity Review: statistical trends in SAR filing, fraud typologies seen by "
            "financial institutions, tips for effective SAR preparation, and common issues."
        )
    },
    {
        "ref_id": "fincen-account-takeover-advisory",
        "agency": "FinCEN",
        "title": "Advisory on Account Takeover Activity (FIN-2011-A016)",
        "url": "https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2011-a016",
        "summary": (
            "FinCEN advisory on account takeover fraud: red flags including unauthorized access via "
            "phishing or malware, mule networks, wire transfers, and SAR filing guidance for account "
            "takeover activity."
        )
    },
    {
        "ref_id": "fincen-imposter-mule-advisory",
        "agency": "FinCEN",
        "title": "Advisory on Imposter Scams and Money Mule Schemes",
        "url": "https://www.fincen.gov/system/files/advisory/2020-07-07/Advisory_%20Imposter_and_Money_Mule_COVID_19_508_FINAL.pdf",
        "summary": (
            "FinCEN 2020 advisory on imposter scams and money mule schemes: fraud patterns leveraging "
            "COVID-19 as cover, red flags for mule accounts, and SAR filing guidance."
        )
    },
    {
        "ref_id": "fincen-identity-suspicious-activity",
        "agency": "FinCEN",
        "title": "Identity-Related Suspicious Activity, 2021",
        "url": "https://www.fincen.gov/system/files/shared/FTA_Identity_Final508.pdf",
        "summary": (
            "FinCEN 2021 report on identity-related suspicious activity: synthetic identity fraud, "
            "account takeover, new account fraud, and red flags for identity misuse at financial institutions."
        )
    },
    {
        "ref_id": "ffiec-ml-red-flags",
        "agency": "FFIEC",
        "title": "Money Laundering and Terrorist Financing Red Flags",
        "url": "https://bsaaml.ffiec.gov/manual/Appendices/07",
        "summary": (
            "FFIEC BSA/AML manual appendix on money laundering and terrorist financing red flags: "
            "unusual transaction patterns, structuring, layering, integration, and behavioral red flags "
            "for financial institutions."
        )
    },
    {
        "ref_id": "ffiec-suspicious-activity-reporting",
        "agency": "FFIEC",
        "title": "Suspicious Activity Reporting",
        "url": "https://bsaaml.ffiec.gov/manual/AssessingComplianceWithBSARegulatoryRequirements/04",
        "summary": (
            "FFIEC BSA/AML manual section on suspicious activity reporting: mandatory reporting "
            "thresholds, SAR requirements, documentation standards, and examiner expectations."
        )
    },
]

# ---------------------------------------------------------------------------
# Fraud patterns — text verbatim from README.md "The five known fraud patterns"
# ---------------------------------------------------------------------------

FRAUD_PATTERNS: List[Dict[str, str]] = [
    {
        "pattern_id": "card_testing",
        "name": "Card Testing",
        "policy_rule": "R5",
        "text": (
            "Card testing. A stolen card number is checked before use: three or more tiny online "
            "authorizations, often under $5, then a larger purchase. Confirmed by the sequence itself. "
            "Three or more small online authorizations on one card within an hour followed by a larger "
            "purchase. Recommend DECLINE_TRANSACTION and STEP_UP_AUTH. If a purchase over $100 has "
            "already cleared, recommend BLOCK_CARD."
        )
    },
    {
        "pattern_id": "card_not_present_fraud",
        "name": "Card-Not-Present Fraud",
        "policy_rule": "R1-R4",
        "text": (
            "Card-not-present fraud. The number is used online without the card. Amounts and products "
            "that don't fit the cardholder's history, often in a burst of two to four within 48 hours. "
            "On its own, one unusual online purchase is ambiguous: verify. Verify before blocking on a "
            "weak signal. If the case rests on a single signal and fraud probability is below 0.70, "
            "recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block."
        )
    },
    {
        "pattern_id": "card_not_present_new_device",
        "name": "Card-Not-Present Fraud from a New Device",
        "policy_rule": "R1-R4",
        "text": (
            "Card-not-present fraud from a new device. Same as card-not-present fraud, with the identity "
            "record marking the device as New for this account, sometimes behind a proxy. Stronger than "
            "pattern 2, still not proof: people buy new phones. id_15 is New for the device. id_23 may "
            "indicate proxy use (transparent, anonymous, hidden). Higher signal strength than plain "
            "card-not-present fraud but still not definitive proof."
        )
    },
    {
        "pattern_id": "out_of_region_use",
        "name": "Out-of-Region Use",
        "policy_rule": "R2-R3",
        "text": (
            "Out-of-region use. Card-present purchases in a billing region the cardholder has no history "
            "in, while their normal activity continues at home. Several days of purchases in one new "
            "region is a trip, not a clone. In-person transactions in addr1 region where cardholder has "
            "no history. Normal home activity continues in parallel. Policy R2 on denial, R3 on confirmation."
        )
    },
    {
        "pattern_id": "account_takeover",
        "name": "Account Takeover",
        "policy_rule": "R6-R9",
        "text": (
            "Account takeover. Mixed-channel activity inconsistent with the cardholder, often with device "
            "and match-flag anomalies, pointing to stolen credentials rather than a stolen number. "
            "Mixed in-person and online transactions inconsistent with cardholder history. Device and "
            "match-flag anomalies (M1-M9, id_15, id_23). Stolen credentials rather than stolen card number. "
            "May involve shared device profiles across multiple accounts."
        )
    },
]

# ---------------------------------------------------------------------------
# Policy rules — text verbatim from README.md "Fraud Policy" section 3
# ---------------------------------------------------------------------------

POLICY_RULES: List[Dict[str, str]] = [
    {
        "rule_id": "R1",
        "text": (
            "R1. Verify before you block on a weak signal. If the case rests on a single signal "
            "(including a risk score alone) and your assessed fraud probability is below 0.70, "
            "recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block. Blocking a legitimate "
            "customer on one signal is a policy breach."
        )
    },
    {
        "rule_id": "R2",
        "text": (
            "R2. Customer denies the transaction. Recommend BLOCK_CARD and CREATE_CASE. Add FILE_REPORT "
            "if exposure exceeds $1,000 or the case connects to a shared device profile or another "
            "card's fraud."
        )
    },
    {
        "rule_id": "R3",
        "text": (
            "R3. Customer confirms the transaction. Recommend CLOSE_NO_FRAUD. Note the confirmation "
            "in the case file."
        )
    },
    {
        "rule_id": "R4",
        "text": (
            "R4. No reply within 24 hours. Recommend MONITOR_CARD and DECLINE_TRANSACTION for pending "
            "authorizations. Escalate if exposure exceeds $500."
        )
    },
    {
        "rule_id": "R5",
        "text": (
            "R5. Card testing. Three or more small online authorizations on one card within an hour, "
            "followed by a larger purchase: recommend DECLINE_TRANSACTION and STEP_UP_AUTH. If a "
            "purchase over $100 has already cleared, recommend BLOCK_CARD."
        )
    },
    {
        "rule_id": "R6",
        "text": (
            "R6. Shared origin. When several cards show fraud from the same device profile, the same "
            "billing region, or the same recipient email in one window, name the shared element, "
            "recommend CREATE_CASE and FILE_REPORT, and MONITOR_CONNECTED_CARDS for every card "
            "that shares it."
        )
    },
    {
        "rule_id": "R7",
        "text": (
            "R7. Disputed but legitimate. When the customer disputes a charge that matches their own "
            "recurring pattern (same merchant, same amount, monthly), recommend CREATE_CASE, "
            "VERIFY_WITH_CUSTOMER, and WARN_CUSTOMER. Do not block."
        )
    },
    {
        "rule_id": "R8",
        "text": (
            "R8. Escalate when uncertain and exposed. If the verdict is 'uncertain' and exposure "
            "exceeds $500, or the evidence conflicts, recommend ESCALATE_TO_ANALYST."
        )
    },
    {
        "rule_id": "R9",
        "text": (
            "R9. Undocumented patterns. When activity fits none of the known patterns but the evidence "
            "shows coordinated or repeated abuse across customers, recommend CREATE_CASE, FILE_REPORT, "
            "and ESCALATE_TO_ANALYST, and describe the pattern in your own words. Do not force it "
            "into a known category."
        )
    },
    {
        "rule_id": "R10",
        "text": (
            "R10. Never BLOCK_ALL_CARDS unless at least two of the customer's cards show confirmed "
            "fraud or the customer's credentials are confirmed compromised."
        )
    },
]


# ---------------------------------------------------------------------------
# TF-IDF Vector Store
# ---------------------------------------------------------------------------

class FraudVectorStore:
    """
    TF-IDF cosine-similarity vector store.

    Public interface matches the contract so that a ChromaDB implementation
    can be substituted without changing callers.

    Usage
    -----
        store = FraudVectorStore(data_dir=Path("dataset/HHGOA_IEEE"))
        results = store.query("card testing small online authorizations", n=5)
        for r in results:
            print(r.score, r.doc.source_type, r.doc.metadata)
    """

    SOURCE_TYPES = ("closed_case", "fraud_pattern", "regulatory", "policy_rule")

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path("dataset/HHGOA_IEEE")
        self._docs: List[Document] = []
        self._doc_index: Dict[str, Document] = {}
        self._vectorizer: Optional[TfidfVectorizer] = None
        self._matrix = None
        self._is_built = False
        self._backend = "tfidf"

        self.build()

    # ------------------------------------------------------------------
    # Building the index
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Loads all source material and fits the TF-IDF model."""
        logger.info("Building FraudVectorStore (TF-IDF backend)...")

        self._docs.clear()
        self._doc_index.clear()

        self._index_fraud_patterns()
        self._index_policy_rules()
        self._index_regulatory_references()
        self._index_closed_cases()

        if not self._docs:
            logger.warning("No documents indexed — vector store is empty.")
            return

        texts = [d.text for d in self._docs]
        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
            analyzer="word"
        )
        self._matrix = self._vectorizer.fit_transform(texts)
        self._is_built = True
        logger.info(
            f"FraudVectorStore built: {len(self._docs)} documents "
            f"({self._count_by_type()}) using TF-IDF."
        )

    def _make_doc(self, doc_id: str, text: str, source_type: str, metadata: Dict[str, Any]) -> Document:
        d = Document(doc_id=doc_id, text=text, source_type=source_type, metadata=metadata)
        self._docs.append(d)
        self._doc_index[doc_id] = d
        return d

    def _index_fraud_patterns(self) -> None:
        for p in FRAUD_PATTERNS:
            self._make_doc(
                doc_id=f"pattern::{p['pattern_id']}",
                text=p["text"],
                source_type="fraud_pattern",
                metadata={
                    "pattern_id": p["pattern_id"],
                    "name": p["name"],
                    "policy_rule": p["policy_rule"],
                    "source_type": "fraud_pattern"
                }
            )

    def _index_policy_rules(self) -> None:
        for r in POLICY_RULES:
            self._make_doc(
                doc_id=f"rule::{r['rule_id']}",
                text=r["text"],
                source_type="policy_rule",
                metadata={
                    "rule_id": r["rule_id"],
                    "source_type": "policy_rule"
                }
            )

    def _index_regulatory_references(self) -> None:
        for ref in REGULATORY_REFERENCES:
            text = f"{ref['agency']} {ref['title']}: {ref['summary']}"
            self._make_doc(
                doc_id=f"reg::{ref['ref_id']}",
                text=text,
                source_type="regulatory",
                metadata={
                    "ref_id": ref["ref_id"],
                    "ref_name": ref["title"],
                    "agency": ref["agency"],
                    "url": ref["url"],
                    "source_type": "regulatory"
                }
            )

    def _index_closed_cases(self) -> None:
        csv_path = self.data_dir / "closed_cases_history.csv"
        if not csv_path.exists():
            logger.warning(f"closed_cases_history.csv not found at {csv_path}")
            return

        count = 0
        with open(csv_path, encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                case_id = row.get("case_id", "")
                if not case_id:
                    continue

                # Build searchable text from meaningful fields only
                parts = [
                    f"case_id {case_id}",
                    f"customer {row.get('customer_id', '')}",
                    f"card {row.get('card_id', '')}",
                    f"outcome {row.get('outcome', '')}",
                    f"pattern {row.get('pattern', '')}",
                    f"exposure {row.get('exposure_usd', '')}",
                    f"actions {row.get('actions_taken', '')}",
                ]
                notes = row.get("analyst_notes", "") or ""
                if notes:
                    parts.append(notes)

                text = " ".join(p for p in parts if p.strip())
                metadata = {
                    "case_id": case_id,
                    "customer_id": row.get("customer_id"),
                    "card_id": row.get("card_id"),
                    "outcome": row.get("outcome"),
                    "pattern": row.get("pattern"),
                    "exposure_usd": row.get("exposure_usd"),
                    "opened_at": row.get("opened_at"),
                    "closed_at": row.get("closed_at"),
                    "actions_taken": row.get("actions_taken"),
                    "report_filed": row.get("report_filed"),
                    "source_type": "closed_case"
                }
                self._make_doc(
                    doc_id=f"case::{case_id}",
                    text=text,
                    source_type="closed_case",
                    metadata=metadata
                )
                count += 1

        logger.info(f"Indexed {count} closed cases.")

    # ------------------------------------------------------------------
    # Query interface
    # ------------------------------------------------------------------

    def query(
        self,
        query_text: str,
        n: int = 5,
        source_types: Optional[List[str]] = None
    ) -> List[SearchResult]:
        """
        Retrieves top-n documents most similar to query_text.

        Parameters
        ----------
        query_text   : free-text search string
        n            : number of results to return
        source_types : optional filter — list of "closed_case" | "fraud_pattern" |
                       "regulatory" | "policy_rule"

        Returns
        -------
        List[SearchResult] ordered by descending cosine similarity.
        """
        if not query_text or not query_text.strip():
            return []
        if not self._is_built or self._vectorizer is None or self._matrix is None:
            return []

        q_vec = self._vectorizer.transform([query_text.strip()])
        scores = cosine_similarity(q_vec, self._matrix).flatten()

        # Apply source_type filter
        candidates = []
        for i, doc in enumerate(self._docs):
            if source_types and doc.source_type not in source_types:
                continue
            candidates.append((float(scores[i]), doc))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return [SearchResult(doc=doc, score=score) for score, doc in candidates[:n]]

    def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Retrieves a document by its exact doc_id."""
        return self._doc_index.get(doc_id)

    def stats(self) -> Dict[str, int]:
        """Returns counts of indexed documents by source type."""
        result = {t: 0 for t in self.SOURCE_TYPES}
        result["total"] = len(self._docs)
        for d in self._docs:
            if d.source_type in result:
                result[d.source_type] += 1
        return result

    def _count_by_type(self) -> str:
        s = self.stats()
        return (
            f"closed_cases={s['closed_case']}, patterns={s['fraud_pattern']}, "
            f"regulatory={s['regulatory']}, policy_rules={s['policy_rule']}"
        )
