from enum import Enum


class ChoiceEnum(Enum):
    @classmethod
    def choices(cls):
        return [(choice.value, choice.name.lower().replace("_", " ").capitalize()) for choice in cls]


class ActionTypeE(ChoiceEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
