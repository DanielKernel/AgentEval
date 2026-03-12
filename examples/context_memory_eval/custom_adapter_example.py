"""
Custom adapter example: Connecting any service to agent-eval.

This example shows three patterns for implementing custom adapters:
1. HTTP REST service (using RESTServiceAdapter)
2. Python SDK / local function (using LocalFunctionAdapter)
3. Custom Protocol implementation

Run with:
    python custom_adapter_example.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_eval.context_memory import (
    ContextMemoryEvalHarness,
    ContextQualityResult,
    Document,
    LocalFunctionAdapter,
    MemoryAnswer,
    MemoryTask,
    MemoryTaskType,
    MemoryTurn,
    MockAdapter,
    RankedDocument,
    RetrievalTask,
    get_all_self_built_tasks,
)


# ── Pattern 1: REST Service Adapter ─────────────────────────────────────────
def demo_rest_adapter():
    """Connect to any HTTP REST API."""
    from agent_eval.context_memory import RESTServiceAdapter

    adapter = RESTServiceAdapter(
        base_url="http://your-service.example.com",
        endpoints={
            # Map adapter methods to your API endpoints
            "retrieve": "/api/v1/retrieve",
            "store_memory": "/api/v1/memory/store",
            "query_memory": "/api/v1/memory/query",
            "compress": "/api/v1/compress",
            "answer": "/api/v1/answer",
        },
        headers={
            "Authorization": "Bearer YOUR_TOKEN",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    print("✓ RESTServiceAdapter created (not called, would need a real server)")
    return adapter


# ── Pattern 2: Python SDK / Local Function Adapter ───────────────────────────
def demo_local_adapter():
    """Wrap any Python callable as an adapter."""

    # Simulate a "service" (could be your Python SDK, a class instance, etc.)
    class MyMemoryService:
        def __init__(self):
            self._store = {}

        def add(self, session_id: str, messages: list):
            self._store[session_id] = messages

        def ask(self, session_id: str, question: str) -> str:
            turns = self._store.get(session_id, [])
            for turn in reversed(turns):
                if question.lower() in turn.get("content", "").lower():
                    return turn.get("content", "I don't know")
            return "I don't know"

    svc = MyMemoryService()

    adapter = LocalFunctionAdapter(
        store_fn=lambda session_id, history: svc.add(
            session_id, [{"role": t.role, "content": t.content} for t in history]
        ),
        query_fn=lambda session_id, question: MemoryAnswer(
            task_id="", answer=svc.ask(session_id, question)
        ),
    )
    print("✓ LocalFunctionAdapter wrapping MyMemoryService")
    return adapter


# ── Pattern 3: Custom Protocol Implementation ────────────────────────────────
class MyCustomAdapter:
    """
    Full custom implementation of all three adapter protocols.

    Implement whichever methods your service supports.
    The harness auto-detects which capabilities are available.
    """

    def retrieve(self, query: str, corpus, top_k: int):
        """Implement retrieval logic here."""
        # Example: simple keyword overlap ranking
        query_tokens = set(query.lower().split())
        scored = []
        for doc in corpus:
            tokens = set(doc.text.lower().split())
            score = len(query_tokens & tokens) / max(len(query_tokens), 1)
            scored.append((score, doc.doc_id))
        scored.sort(reverse=True)
        return [
            RankedDocument(doc_id=did, score=s, rank=i + 1)
            for i, (s, did) in enumerate(scored[:top_k])
        ]

    def store_memory(self, session_id: str, history) -> None:
        """Store conversation history."""
        print(f"  [store] session={session_id}, {len(history)} turns")

    def query_memory(self, session_id: str, question: str) -> MemoryAnswer:
        """Query stored memory."""
        return MemoryAnswer(task_id="", answer=f"Answer to: {question}")

    def compress_context(self, documents, budget_tokens: int) -> str:
        """Compress documents to fit within token budget."""
        combined = " ".join(str(d) for d in documents)
        return combined[:budget_tokens * 4]  # rough 4-char/token estimate

    def answer_with_context(self, context: str, question: str) -> ContextQualityResult:
        """Answer a question given compressed context."""
        return ContextQualityResult(
            task_id="",
            answer=f"Based on context: {context[:50]}...",
            context_used=context,
            tokens_used=len(context.split()),
        )


def demo_custom_adapter():
    """Run self-built scenario tasks with our custom adapter."""
    adapter = MyCustomAdapter()
    print("✓ MyCustomAdapter created")

    # Load all self-built UC scenario tasks
    tasks = get_all_self_built_tasks()
    print(f"  Loaded {len(tasks)} self-built UC scenario tasks")

    harness = ContextMemoryEvalHarness(adapter=adapter)
    report = harness.run(tasks[:5])  # Run first 5 for demo

    summary = report.summary()
    print(f"  Pass rate: {report.pass_rate:.1%} ({report.passed_tasks}/{report.total_tasks})")
    return report


# ── Main demo ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=== Custom Adapter Patterns Demo ===\n")

    print("Pattern 1: REST Service Adapter")
    demo_rest_adapter()
    print()

    print("Pattern 2: LocalFunctionAdapter")
    demo_local_adapter()
    print()

    print("Pattern 3: Custom Protocol Implementation")
    report = demo_custom_adapter()
    print()

    print("=== Done ===")
    print("\nTo connect to ContextAgent, configure RESTServiceAdapter with your endpoints:")
    print("""
    from agent_eval.context_memory import RESTServiceAdapter, BEIRLoader, ContextMemoryEvalHarness

    adapter = RESTServiceAdapter(
        base_url="http://your-context-agent-host:8080",
        endpoints={
            "retrieve": "/api/v1/context/retrieve",
            "store_memory": "/api/v1/memory/store",
            "query_memory": "/api/v1/memory/query",
        },
        headers={"Authorization": "Bearer <your-token>"},
    )

    tasks = BEIRLoader().load(local_path="./data/nfcorpus", max_samples=100)
    report = ContextMemoryEvalHarness(adapter=adapter).run_retrieval(tasks)
    print(report.summary())
    """)
