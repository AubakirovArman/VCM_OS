from vcm_os.context.pack_builder.assembler import PackAssemblerMixin
from vcm_os.context.pack_builder.core import ContextPackBuilderCore
from vcm_os.context.pack_builder.rescue import RescueMixin


class ContextPackBuilder(ContextPackBuilderCore, RescueMixin, PackAssemblerMixin):
    pass
