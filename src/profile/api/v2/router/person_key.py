from profile.api.v2.docs import DESTROY_KEY_ERRORS
from profile.api.v2.schema.person_key import DestroyedKeyRead, DestroyKeyData
from profile.dependency.personal_data import PersonalDataUOWDep
from profile.dependency.viewer import VerifiedViewerDep
from profile.service.key_maintenance import KeyMaintenanceService
from uuid import UUID

from fastapi import APIRouter

from core.dependencies.auth import SuperUserJWTDep

router = APIRouter(prefix="/persons/{person_id}", tags=["person", "personal-data"])


@router.post("/destroy-key", responses={**DESTROY_KEY_ERRORS})
async def destroy_person_key(
    person_id: UUID,
    data: DestroyKeyData,
    user: SuperUserJWTDep,
    viewer: VerifiedViewerDep,
    uow: PersonalDataUOWDep,
) -> DestroyedKeyRead:
    """Destroys the person's data key and the encrypted data with it, for good: a
    passport is deleted, an optional encrypted value is emptied. The person is
    told; new data is sealed with a new key."""
    return DestroyedKeyRead.from_dto(
        await KeyMaintenanceService(uow).destroy(person_id, data.to_dto(), viewer)
    )
