from core.repository.location import LocationBaseRepo
from core.utils.abstract.unit_of_work import ABCUnitOfWork


class LocationAUOW(ABCUnitOfWork):
    locations: LocationBaseRepo
