from enum import Enum


class UserRole(str, Enum):
    user = "USER"
    admin = "ADMIN"