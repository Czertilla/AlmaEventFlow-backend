from typing import Annotated

from fastapi import Depends

from org.uow.address import AddressUOW

from ._uow import UOWDep

AddressUOWDep = Annotated[AddressUOW, Depends(UOWDep(AddressUOW))]
