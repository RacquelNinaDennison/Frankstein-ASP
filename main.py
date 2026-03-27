import asyncio
from pathlib import Path
from src.modules.frankstein import Frankenstein
from src.modules.data_loader import load_applications

BASE = Path(__file__).parent
SAMPLE_DATA = BASE / "src" / "data" / "sample_applications.json"


def main():
    applications = load_applications(SAMPLE_DATA)
    frank = Frankenstein()
    results = asyncio.run(frank.pass_applications(applications))

    print("\n=== FINAL RESULTS ===")
    for app_id, decision in results.items():
        print(f"  {app_id}: {decision}")


if __name__ == "__main__":
    main()
