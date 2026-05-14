from typing import Optional

from vcm_os.schemas import ContextPack, MemoryRequest, SessionIdentity, SessionState
from vcm_os.session.checkpoint import CheckpointManager
from vcm_os.session.store import SessionStore
from vcm_os.memory.router import MemoryRouter
from vcm_os.memory.reader import MemoryReader
from vcm_os.context.pack_builder import ContextPackBuilder
from vcm_os.storage.sqlite_store import SQLiteStore
from vcm_os.storage.vector_index import VectorIndex
from vcm_os.storage.sparse_index import SparseIndex


class SessionRestorer:
    def __init__(
        self,
        store: SQLiteStore,
        vector_index: VectorIndex,
        sparse_index: SparseIndex,
    ):
        self.session_store = SessionStore(store)
        self.checkpoint_manager = CheckpointManager(store)
        self.router = MemoryRouter()
        self.reader = MemoryReader(store, vector_index, sparse_index)
        self.pack_builder = ContextPackBuilder()

    def restore(self, session_id: str, query: str = "resume work") -> ContextPack:
        checkpoint = self.checkpoint_manager.load_latest_checkpoint(session_id)
        active_state = self.session_store.get_session_state(session_id)
        session = self.session_store.get_session(session_id)
        project_id = session.project_id if session else "default"

        request = MemoryRequest(
            project_id=project_id,
            session_id=session_id,
            query=query,
            task_type=self.router.classify_task(query).value,
        )

        plan = self.router.make_plan(request)
        candidates = self.reader.retrieve(request, plan)

        pack = self.pack_builder.build(
            request=request,
            candidates=candidates,
            checkpoint=checkpoint,
            active_state=active_state,
            session=session,
        )
        return pack
