"""Research a topic with Tavily and save results to .tmp/<slug>/research.json.

Usage: python tools/research_topic.py --topic "Agentes de IA em pequenas empresas"
Cost: advanced search = 2 Tavily credits (free plan: 1,000/month).
"""
import argparse
import json

from tavily import TavilyClient

from _env import require_env, run_dir, slugify


def research(topic: str, max_results: int = 8) -> dict:
    client = TavilyClient(api_key=require_env("TAVILY_API_KEY"))
    resp = client.search(
        query=topic,
        search_depth="advanced",
        max_results=max_results,
        include_answer=True,
    )
    return {
        "topic": topic,
        "answer": resp.get("answer"),
        "results": [
            {"title": r.get("title"), "url": r.get("url"), "content": r.get("content")}
            for r in resp.get("results", [])
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--topic", required=True)
    p.add_argument("--slug")
    p.add_argument("--max-results", type=int, default=8)
    a = p.parse_args()
    slug = a.slug or slugify(a.topic)
    data = research(a.topic, a.max_results)
    if not data["results"]:
        raise SystemExit("Tavily returned no results — try a broader topic.")
    out = run_dir(slug) / "research.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(data['results'])} results -> {out}")
    print(f"SLUG={slug}")


if __name__ == "__main__":
    main()
