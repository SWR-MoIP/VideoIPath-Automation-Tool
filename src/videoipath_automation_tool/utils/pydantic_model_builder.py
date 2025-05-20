from __future__ import annotations

from pydantic import BaseModel


class PydanticModelBuilder:
    def __init__(self, name: str, parent_classes: list[str] | None = None):
        self.name = name
        self.fields: list[PydanticModelField] = []
        self.parent_classes: list[str] | None = parent_classes

    def add_field(self, field: PydanticModelField):
        self.fields.append(field)

    def build(self) -> str:
        return f"{self._class_definition}\n{self._fields()}"

    def _fields(self) -> str:
        if len(self.fields) == 0:
            return "\t..."
        return "\n".join([str(field) for field in self.fields])

    @property
    def _class_definition(self) -> str:
        return f"class {self.name}({', '.join(self.parent_classes) if self.parent_classes else 'BaseModel'}):"


class PydanticModelField(BaseModel):
    name: str
    type: str
    default: str | int | float | bool | None = None
    alias: str | None = None
    label: str | None = None
    description: str | None = None
    is_optional: bool = False
    min_value: int | float | None = None
    max_value: int | float | None = None
    literal_options: list[tuple[str | int | float, str, bool]] | None = None

    def __str__(self) -> str:
        return f"{self._render_attribute()}{self._render_docstring()}"

    def _render_attribute(self) -> str:
        name_and_type = f"{self.name}: {self._parse_type()}"
        params = []

        if self.default is not None:
            params.append(f"default={self._render_default_value()}")

        if self.min_value is not None:
            params.append(f"ge={self.min_value}")

        if self.max_value is not None:
            params.append(f"le={self.max_value}")

        if self.alias:
            params.append(f'alias="{self.alias}"')

        if len(params) == 1 and self.default is not None:
            return f"\t{name_and_type} = {self._render_default_value()}\n"

        return f"\t{name_and_type} = Field({', '.join(params)})\n"

    def _render_docstring(self) -> str:
        docstring = ""

        if self.label:
            docstring += f"{self.label}\\n\n"

        if self.description and self.description != self.label:
            parsed_description = self.description.replace("\n", "\\n\n")
            docstring += f"{parsed_description}\\n\n"

        if self.literal_options:
            docstring += "Possible values:"
            for value, label, is_default in self.literal_options:
                docstring += f"\\n\n\t`{value}`: {label}{' (default)' if is_default else ''}"
            docstring += "\n"

        return f'\t"""\n{docstring}\t"""\n' if docstring else ""

    def _render_default_value(self) -> str:
        if self.default is None:
            return ""

        if type(self.default) is str:
            return f'"{self.default}"'

        return str(self.default)

    def _parse_type(self) -> str:
        if self.is_optional:
            return f"Optional[{self._parse_raw_type()}]"
        return self._parse_raw_type()

    def _parse_raw_type(self) -> str:
        if self.type == "string":
            return "str"
        if self.type == "number":
            return "int"
        if self.type == "float":
            return "float"
        if self.type == "bool":
            return "bool"
        if self.type == "map":
            return "any"
        return self.type
