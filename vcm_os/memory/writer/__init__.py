from vcm_os.memory.writer.core import MemoryWriterCore
from vcm_os.memory.writer.extractor import ExtractorMixin
from vcm_os.memory.writer.ledger import LedgerMixin
from vcm_os.memory.writer.linker import LinkerMixin
from vcm_os.memory.writer.rule_extractors import RuleExtractorMixin
from vcm_os.memory.writer.scorer import ScorerMixin


class MemoryWriter(
    MemoryWriterCore,
    ExtractorMixin,
    RuleExtractorMixin,
    ScorerMixin,
    LinkerMixin,
    LedgerMixin,
):
    pass
