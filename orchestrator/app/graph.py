from typing import Any, Dict, List, TypedDict

from langgraph.graph import END, StateGraph

from app import config
from app.clients import embed_texts, generate_answer, rerank
from app.db import fetch_similar_docs


class GraphState(TypedDict, total=False):
    query: str
    k: int
    query_vec_128: List[float]
    query_vec_768: List[float]
    docs_128: List[Dict[str, Any]]
    docs_768: List[Dict[str, Any]]
    reranked: List[Dict[str, Any]]
    rerank_top_score: float
    path_used: str
    answer: str


async def node_embed_128(state: GraphState) -> GraphState:
    vectors = await embed_texts([state["query"]], 128)
    return {"query_vec_128": vectors[0]}


def node_retrieve_128(state: GraphState) -> GraphState:
    docs = fetch_similar_docs(state["query_vec_128"], 128, state["k"])
    return {"docs_128": docs}


async def node_rerank_128(state: GraphState) -> GraphState:
    docs = state.get("docs_128", [])
    if not docs:
        return {"reranked": [], "rerank_top_score": 0.0}

    try:
        ranked = await rerank(state["query"], [d["text"] for d in docs])
        ranked_map = {item["text"]: item["score"] for item in ranked}
        merged = sorted(
            [
                {
                    **doc,
                    "rerank_score": float(
                        ranked_map.get(doc["text"], doc["similarity"])
                    ),
                }
                for doc in docs
            ],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )
        top = merged[0]["rerank_score"] if merged else 0.0
        return {"reranked": merged, "rerank_top_score": top}
    except Exception:
        merged = sorted(docs, key=lambda x: x["similarity"], reverse=True)
        top = merged[0]["similarity"] if merged else 0.0
        return {"reranked": merged, "rerank_top_score": top}


def decide_quality(state: GraphState) -> str:
    return (
        "strong"
        if state.get("rerank_top_score", 0.0) >= config.RERANK_QUALITY_THRESHOLD
        else "weak"
    )


async def node_embed_768(state: GraphState) -> GraphState:
    vectors = await embed_texts([state["query"]], 768)
    return {"query_vec_768": vectors[0]}


def node_retrieve_768(state: GraphState) -> GraphState:
    docs = fetch_similar_docs(state["query_vec_768"], 768, state["k"])
    return {"docs_768": docs}


async def node_rerank_768(state: GraphState) -> GraphState:
    docs = state.get("docs_768", [])
    if not docs:
        return {"reranked": [], "rerank_top_score": 0.0}

    try:
        ranked = await rerank(state["query"], [d["text"] for d in docs])
        ranked_map = {item["text"]: item["score"] for item in ranked}
        merged = sorted(
            [
                {
                    **doc,
                    "rerank_score": float(
                        ranked_map.get(doc["text"], doc["similarity"])
                    ),
                }
                for doc in docs
            ],
            key=lambda x: x["rerank_score"],
            reverse=True,
        )
        return {"reranked": merged}
    except Exception:
        merged = sorted(docs, key=lambda x: x["similarity"], reverse=True)
        return {"reranked": merged}


def node_mark_fast_path(_: GraphState) -> GraphState:
    return {"path_used": "fast_128"}


def node_mark_fallback_path(_: GraphState) -> GraphState:
    return {"path_used": "fallback_768"}


def node_generate(state: GraphState) -> GraphState:
    contexts = [d["text"] for d in state.get("reranked", [])[:3]]
    answer = generate_answer(state["query"], contexts)
    return {"answer": answer}


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("embed_128", node_embed_128)
    graph.add_node("retrieve_128", node_retrieve_128)
    graph.add_node("rerank_128", node_rerank_128)
    graph.add_node("mark_fast", node_mark_fast_path)
    graph.add_node("embed_768", node_embed_768)
    graph.add_node("retrieve_768", node_retrieve_768)
    graph.add_node("rerank_768", node_rerank_768)
    graph.add_node("mark_fallback", node_mark_fallback_path)
    graph.add_node("generate", node_generate)

    graph.set_entry_point("embed_128")
    graph.add_edge("embed_128", "retrieve_128")
    graph.add_edge("retrieve_128", "rerank_128")

    graph.add_conditional_edges(
        "rerank_128",
        decide_quality,
        {
            "strong": "mark_fast",
            "weak": "embed_768",
        },
    )

    graph.add_edge("mark_fast", "generate")
    graph.add_edge("embed_768", "retrieve_768")
    graph.add_edge("retrieve_768", "rerank_768")
    graph.add_edge("rerank_768", "mark_fallback")
    graph.add_edge("mark_fallback", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
