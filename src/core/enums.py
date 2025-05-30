from enum import Enum


class ApiTags(str, Enum):
    PUBLIC = "public"
    BALANCE = "balance"
    ORDER = "order"
    ADMIN = "admin"
    USER = "user"