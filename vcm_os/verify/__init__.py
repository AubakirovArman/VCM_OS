"""VCM-OS system verification orchestrator."""
import asyncio
import sys
from datetime import datetime, timezone

from vcm_os.verify.unit import run_unit_tests
from vcm_os.verify.api import api_smoke_tests


async def main() -> int:
    print("=" * 60)
    print("VCM-OS v0.3 System Verification")
    print("=" * 60)
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")

    all_ok = True

    # Unit tests
    if not run_unit_tests():
        all_ok = False
        print("\n❌ UNIT TESTS FAILED")
    else:
        print("\n✅ ALL UNIT TESTS PASSED")

    # API tests
    try:
        if not await api_smoke_tests():
            all_ok = False
            print("\n❌ API SMOKE TESTS FAILED")
        else:
            print("\n✅ ALL API SMOKE TESTS PASSED")
    except Exception as e:
        all_ok = False
        print(f"\n❌ API SMOKE TESTS EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    if all_ok:
        print("✅ ALL CHECKS PASSED - System is healthy")
    else:
        print("❌ SOME CHECKS FAILED - See output above")
    print("=" * 60)
    return 0 if all_ok else 1


def run():
    sys.exit(asyncio.run(main()))
