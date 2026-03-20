from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.intelligence.general import GeneralAnalyst
from config import settings
from utils.model_factory import ModelFactory


DEFAULT_TEXT = (
    "TechCrunch reports that Startup A raised $18M Series A led by Fund X. "
    "Startup A builds AI agents for supply-chain automation. "
    "The company claims 220% YoY growth and expanded into 3 regions. "
    "Risks include high GPU costs and customer concentration."
)


async def run_test(
    *,
    provider: str,
    model_name: str,
    task_description: str,
    text: str,
) -> None:
    llm = ModelFactory.get_model(
        provider=provider,
        model_name=model_name,
        scene=ModelFactory.SCENE_ANALYSIS,
    )
    agent = GeneralAnalyst(model=llm)
    result = await agent.run(text, task_description=task_description)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GeneralAnalyst output test.")
    parser.add_argument("--provider", default=settings.ANALYST_PROVIDER)
    parser.add_argument("--model", default=settings.ANALYST_MODEL_NAME)
    parser.add_argument(
        "--task",
        default="Extract key intelligence for investment monitoring",
    )
    parser.add_argument("--text", default=DEFAULT_TEXT)
    args = parser.parse_args()

    print(f"[TEST] provider={args.provider} model={args.model}")
    try:
        asyncio.run(
            run_test(
                provider=args.provider,
                model_name=args.model,
                task_description=args.task,
                text=args.text,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        print("[FAILED]", exc)
        print("Hint: check .env API key / provider / network connectivity.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
