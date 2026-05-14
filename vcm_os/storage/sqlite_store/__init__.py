from vcm_os.storage.sqlite_store.core import SQLiteStoreCore
from vcm_os.storage.sqlite_store.events import EventStoreMixin
from vcm_os.storage.sqlite_store.memories import MemoryStoreMixin
from vcm_os.storage.sqlite_store.sessions import SessionStoreMixin
from vcm_os.storage.sqlite_store.session_state import SessionStateMixin
from vcm_os.storage.sqlite_store.checkpoints import CheckpointStoreMixin
from vcm_os.storage.sqlite_store.decisions import DecisionStoreMixin
from vcm_os.storage.sqlite_store.errors import ErrorStoreMixin
from vcm_os.storage.sqlite_store.stale import StaleMarkerMixin
from vcm_os.storage.sqlite_store.canonical import CanonicalHashMixin
from vcm_os.storage.sqlite_store.links import LinkStoreMixin
from vcm_os.storage.sqlite_store.monitoring import MonitoringMixin


class SQLiteStore(SQLiteStoreCore, EventStoreMixin, MemoryStoreMixin, SessionStoreMixin, SessionStateMixin, CheckpointStoreMixin, DecisionStoreMixin, ErrorStoreMixin, StaleMarkerMixin, CanonicalHashMixin, LinkStoreMixin, MonitoringMixin):
    pass
