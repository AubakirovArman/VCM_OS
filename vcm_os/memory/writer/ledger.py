from vcm_os.schemas import MemoryObject


class LedgerMixin:
    def _update_decision_ledger(self, obj: MemoryObject) -> None:
        pass

    def _update_error_ledger(self, obj: MemoryObject) -> None:
        pass
