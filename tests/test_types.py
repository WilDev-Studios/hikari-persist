import enum
import pytest

from persist.internal.schemas import DataType, SCHEMA

DATA_TYPE_MAX_BOUNDS = {
    DataType.TINYINT: (1 << 7) - 1,
    DataType.SMALLINT: (1 << 15) - 1,
    DataType.INTEGER: (1 << 31) - 1,
    DataType.BIGINT: (1 << 63) - 1,
}

def get_max_value_from_serializer(serializer):
    if not serializer:
        return None

    target_cls = getattr(serializer, "enum", None) or getattr(serializer, "flag", None)

    if target_cls and issubclass(target_cls, enum.Enum):
        max_val = 0
        for member in target_cls:
            val = member.value
            if isinstance(val, int):
                max_val = max(max_val, val)
            elif isinstance(val, enum.Enum) and isinstance(val.value, int):
                max_val = max(max_val, val.value)

        if issubclass(target_cls, enum.IntFlag):
            all_bits = 0
            for member in target_cls:
                if isinstance(member.value, int) and member.value > 0:
                    all_bits |= member.value
            return all_bits

        return max_val

    return None

@pytest.mark.parametrize("table", SCHEMA, ids=lambda t: t.name)
def test_datatype_capacity_for_enums_and_flags(table):
    for field in table.fields:
        max_required_val = get_max_value_from_serializer(field.serializer)

        if max_required_val is not None:
            max_allowed = DATA_TYPE_MAX_BOUNDS.get(field.type)
            assert max_allowed is not None, f"Unsupported integer DataType {field.type} for field {table.name}.{field.name}" # noqa: E501

            assert max_required_val <= max_allowed, (
                f"Overflow risk in `{table.name}.{field.name}`: "
                f"Max value required by Hikari ({max_required_val}) "
                f"exceeds maximum capacity of {field.type} ({max_allowed})."
            )
