"""Family-specific command catalogs."""

from .idos import get_specs as get_idos_specs
from .ifill import get_specs as get_ifill_specs
from .isafe import get_specs as get_isafe_specs
from .isoft import get_specs as get_isoft_specs
from .softwell import get_specs as get_softwell_specs

__all__ = [
    "get_idos_specs",
    "get_ifill_specs",
    "get_isafe_specs",
    "get_isoft_specs",
    "get_softwell_specs",
]
