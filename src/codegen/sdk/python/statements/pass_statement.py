from __future__ import annotations

from typing import override

from codegen.sdk.core.dataclasses.usage import UsageKind
from codegen.sdk.core.interfaces.has_name import HasName
from codegen.sdk.core.statements.statement import Statement, StatementType
from codegen.sdk.extensions.autocommit import commiter
from codegen.shared.decorators.docs import noapidoc, py_apidoc


@py_apidoc
class PyPassStatement(Statement["PyCodeBlock"]):
    """An abstract representation of a python pass statement."""

    statement_type = StatementType.PASS_STATEMENT

    @noapidoc
    @commiter
    @override
    def _compute_dependencies(self, usage_type: UsageKind, dest: HasName | None = None) -> None:
        pass
