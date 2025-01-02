from dataclasses import dataclass
from typing import Self
from enum import Enum


class ParamType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


class ParameterSchema:
    """Defines a parameter for a lambda function"""
    def __init__(self):
        self._parameters = []

    def add_param(self, name: str, parameter_type: ParamType, description: str, required: bool = False):
        param = self._Param.create(name, parameter_type, description, required)
        self._parameters.append(param)

    def to_dict(self):
        return {
            param.name:
            {
                "description": param.description,
                "type": param.type.value,
                "required": param.required
            } for param in self._parameters
        }

    @dataclass
    class _Param:
        name: str
        type: ParamType
        description: str
        required: bool = False

        @classmethod
        def create(cls, name: str, parameter_type: ParamType, description: str, required: bool = False) -> Self:
            return cls(name, parameter_type, description, required)
