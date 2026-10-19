// BUG-072: real SDK declarations, substituted read-only calls; no Creo connection.
#include "inspection_units.h"
#include <cassert>
#include <cstdio>
#include <limits>

static ProError principal_code = PRO_TK_NO_ERROR, length_code = PRO_TK_NO_ERROR;
static const wchar_t *length_name = L"mm";
static int length_queries = 0;

ProError ProMdlPrincipalunitsystemGet(ProMdl, ProUnitsystem *) {
    return principal_code;
}

ProError ProUnitsystemUnitGet(ProUnitsystem *, ProUnitType type, ProUnititem *unit) {
    assert(type == PRO_UNITTYPE_LENGTH);
    ++length_queries;
    if (!length_code)
        wcscpy_s(unit->name, length_name);
    return length_code;
}

int main() {
    ProMdl model = nullptr; // Never dereferenced by the substituted SDK calls.
    auto units = inspect_length_units(model);
    assert(units.millimeters() && units.volume_mm3(123.0) == 123.0);
    assert(!units.volume_mm3(std::numeric_limits<double>::quiet_NaN()));
    assert(!units.volume_mm3(std::numeric_limits<double>::infinity()));
    length_name = L"in";
    units = inspect_length_units(model);
    assert(!units.millimeters() && !units.volume_mm3(1.0));
    assert(!wcscmp(units.length.name, L"in"));
    length_name = L"cm";
    units = inspect_length_units(model);
    assert(!units.millimeters() && !units.volume_mm3(1.0));
    length_name = L"";
    units = inspect_length_units(model);
    assert(!units.millimeters() && !units.volume_mm3(1.0));
    principal_code = PRO_TK_BAD_INPUTS;
    length_name = L"mm";
    length_queries = 0;
    units = inspect_length_units(model);
    assert(units.code == principal_code && length_queries == 0);
    assert(!units.millimeters() && !units.volume_mm3(1.0));
    principal_code = PRO_TK_NO_ERROR;
    length_code = PRO_TK_E_NOT_FOUND;
    units = inspect_length_units(model);
    assert(units.code == length_code && length_queries == 1);
    assert(!units.millimeters() && !units.volume_mm3(1.0));
    std::puts("INSPECTION_UNITS_OK cases=8; SDK calls substituted, no Toolkit connection");
}
