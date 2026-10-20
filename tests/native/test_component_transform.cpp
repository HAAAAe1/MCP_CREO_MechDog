// BUG-036 SDK contract test. Substituted API results; no Toolkit connection.
#include "component_transform.h"
#include "third_party/json.hpp"
#include <cassert>
#include <cmath>

static ProError path_result = PRO_TK_NO_ERROR;
static ProError transform_result = PRO_TK_NO_ERROR;
static int transform_calls = 0;
static ProMdl expected_owner = nullptr;

ProError ProAsmcomppathInit(ProSolid owner, ProIdTable ids, int count, ProAsmcomppath *path) {
    assert(owner == expected_owner && ids[0] == 48 && count == 1);
    path->table_num = 1;
    return path_result;
}

ProError ProAsmcomppathTrfGet(ProAsmcomppath *path, ProBoolean bottom_up, ProMatrix matrix) {
    ++transform_calls;
    assert(path->table_num == 1 && bottom_up == PRO_B_TRUE);
    // Solved pose is identity, unlike the initial (-30,20,0)+Z30 placement.
    for (int i = 0; i < 4; ++i)
        for (int j = 0; j < 4; ++j)
            matrix[i][j] = i == j ? 1.0 : 0.0;
    return transform_result;
}

int main() {
    int owner_storage = 0;
    expected_owner = reinterpret_cast<ProMdl>(&owner_storage);
    ProAsmcomp component = {};
    component.id = 48;
    component.owner = expected_owner;
    ProMatrix actual = {};
    assert(component_to_assembly_transform(&component, actual) == PRO_TK_NO_ERROR);
    assert(std::abs(actual[3][0]) < 1e-12 && std::abs(actual[3][1]) < 1e-12);
    assert(std::abs(actual[0][0] - 1.0) < 1e-12);
    path_result = PRO_TK_BAD_INPUTS;
    assert(component_to_assembly_transform(&component, actual) == PRO_TK_BAD_INPUTS);
    assert(transform_calls == 1);
    path_result = PRO_TK_NO_ERROR;
    transform_result = PRO_TK_GENERAL_ERROR;
    assert(component_to_assembly_transform(&component, actual) == PRO_TK_GENERAL_ERROR);
    assert(component_to_assembly_transform(nullptr, actual) == PRO_TK_BAD_INPUTS);
    using Json = nlohmann::json;
    Json legacy = {{"transform", {-30, 20, 0}}};
    Json current = {{"transform", {0, 0, 0}},
                    {"initial_transform", {-30, 20, 0}},
                    {"transform_source", "component_to_assembly"}};
    assert(component_transform_for_verification(legacy, current) == legacy["transform"]);
    assert(component_transform_for_verification(current, current) == current["transform"]);
    Json unknown = {{"transform_source", "unknown"}};
    bool refused = false;
    try {
        component_transform_for_verification(unknown, current);
    } catch (const std::runtime_error &) {
        refused = true;
    }
    assert(refused);
    return 0;
}
