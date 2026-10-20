from typing import Any
from uuid import UUID, uuid4

from core.broker.rpc import RpcError
from core.enum.rpc import OrgRPC
from core.schema.message.core import MQError
from core.schema.message.org import OrganizationRef


class FakeOrg:
    def __init__(self) -> None:
        self.refs: dict[UUID, OrganizationRef] = {}
        self.parents: dict[UUID, UUID] = {}
        self.calls: list[OrgRPC] = []
        self.down = False

    def add(
        self, type: str, name: str, university_id: UUID | None = None
    ) -> OrganizationRef:
        ref = OrganizationRef(id=uuid4(), name=name, type=type)
        self.refs[ref.id] = ref
        if university_id is not None:
            self.parents[ref.id] = university_id
        return ref

    def _find(self, types: tuple[str, ...], name: str, parent: UUID | None) -> Any:
        return next(
            (
                ref
                for ref in self.refs.values()
                if ref.type in types
                and ref.name.lower() == name.lower()
                and self.parents.get(ref.id) == parent
            ),
            None,
        )

    async def __call__(self, topic: OrgRPC, request: Any, model: Any, **_: Any) -> Any:
        self.calls.append(topic)
        if self.down:
            raise TimeoutError
        if topic == OrgRPC.GET_ORGANIZATION:
            if request.id in self.refs:
                return self.refs[request.id]
            raise RpcError(MQError(code=404, detail="ORGANIZATION_NOT_FOUND", extra={}))
        if topic == OrgRPC.RESOLVE_FACULTY:
            university = self.refs.get(request.university_id)
            if university is None or university.type != "university":
                raise RpcError(
                    MQError(code=404, detail="UNIVERSITY_NOT_FOUND", extra={})
                )
            found = self._find(("faculty",), request.name, request.university_id)
            return found or self.add("faculty", request.name, request.university_id)
        types = {
            OrgRPC.RESOLVE_UNIVERSITY: ("university",),
            OrgRPC.RESOLVE_ORGANIZATION: ("organization", "university"),
        }[topic]
        found = self._find(types, request.name, None)
        kind = "university" if topic == OrgRPC.RESOLVE_UNIVERSITY else "organization"
        return found or self.add(kind, request.name)
