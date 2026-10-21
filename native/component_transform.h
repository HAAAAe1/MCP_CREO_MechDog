#pragma once

#include <ProAsmcomp.h>
#include <ProAsmcomppath.h>
#include <stdexcept>

// PositionGet describes the initial placement before constraints/movements.
// Public inspection must report the current member-to-owner transformation.
inline ProError component_to_assembly_transform(ProAsmcomp *component, ProMatrix matrix) {
    if (!component)
        return PRO_TK_BAD_INPUTS;
    ProIdTable ids = {};
    ids[0] = component->id;
    ProAsmcomppath path;
    ProError code = ProAsmcomppathInit((ProSolid)component->owner, ids, 1, &path);
    if (code)
        return code;
    return ProAsmcomppathTrfGet(&path, PRO_B_TRUE, matrix);
}

// Preserve the old checkpoint guard for registries which recorded initial poses.
// Newly saved inspections compare the solved transform; no legacy baseline is rewritten.
template <typename Json>
inline const Json &component_transform_for_verification(const Json &before, const Json &after) {
    if (before.contains("transform_source")) {
        if (before["transform_source"] != "component_to_assembly")
            throw std::runtime_error("Unknown saved component transform source");
        return after.at("transform");
    }
    return after.contains("initial_transform") ? after.at("initial_transform")
                                               : after.at("transform");
}
