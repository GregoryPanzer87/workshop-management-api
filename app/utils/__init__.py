from .generates import (
    generate_device_type_prefix, generate_custom_serial,
    generate_employee_code, generate_user_credentials,
)

from .validators import (
    validate_unique_fields_by_create,
    validate_unique_fields_by_update,
    validate_exists_by_create,
    validate_exists_by_update,
    build_audit_change_details,
)