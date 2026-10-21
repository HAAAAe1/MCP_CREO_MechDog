// Read model length units without assigning a unit to failed queries (BUG-072).
#pragma once
#include <ProMdlUnits.h>
#include <cmath>
#include <cwchar>
#include <optional>

struct InspectionLengthUnits {
    ProUnititem length = {};
    ProError code = PRO_TK_NO_ERROR;

    bool millimeters() const {
        return code == PRO_TK_NO_ERROR && !std::wcscmp(length.name, L"mm");
    }

    std::optional<double> volume_mm3(double native_volume) const {
        if (millimeters() && std::isfinite(native_volume))
            return native_volume;
        return std::nullopt;
    }
};

inline InspectionLengthUnits inspect_length_units(ProMdl model) {
    InspectionLengthUnits result;
    ProUnitsystem system = {};
    result.code = ProMdlPrincipalunitsystemGet(model, &system);
    if (result.code == PRO_TK_NO_ERROR)
        result.code = ProUnitsystemUnitGet(&system, PRO_UNITTYPE_LENGTH, &result.length);
    return result;
}
