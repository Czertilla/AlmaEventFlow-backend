from typing import Annotated
from fastapi import Depends
from ._uow import UOWDep
from org.uow.address import AddressUOW

AddressUOWDep = Annotated[AddressUOW, Depends(UOWDep(AddressUOW))]
