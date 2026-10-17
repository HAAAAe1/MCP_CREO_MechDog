// Read-only runtime verification shared by status and both direct-loft entry points.
#pragma once
#include <ProToolkitDll.h>
#include <ProArray.h>
#include "callback_identity.h"

static J read_callback_json(const std::filesystem::path &file) {
    std::ifstream input(file, std::ios::binary);
    J value;
    input >> value;
    if (!value.is_object())
        throw std::runtime_error("Invalid callback metadata object");
    return value;
}

static J callback_live_identity(ProToolkitDllHandle handle) {
    unsigned char random[16];
    if (BCryptGenRandom(nullptr, random, sizeof(random), BCRYPT_USE_SYSTEM_PREFERRED_RNG) < 0)
        throw std::runtime_error("Cannot create callback probe nonce");
    constexpr char hex[] = "0123456789abcdef";
    std::string nonce;
    for (auto byte : random) {
        nonce += hex[byte >> 4];
        nonce += hex[byte & 15];
    }
    ProArgument *inputs = nullptr, *outputs = nullptr;
    J identity;
    try {
        ProError code = ProArrayAlloc(1, sizeof(ProArgument), 1, (ProArray *)&inputs);
        if (code)
            throw std::runtime_error("Cannot allocate callback probe");
        inputs[0] = {};
        wcscpy_s(inputs[0].label, L"nonce");
        inputs[0].value.type = PRO_VALUE_TYPE_WSTRING;
        auto value = wide(nonce);
        code = ProValuedataWstringSet(&inputs[0].value, value.data());
        if (code)
            throw std::runtime_error("Cannot encode callback probe");
        ProCharPath function = "MechDogBlendIdentity";
        ProError returned = PRO_TK_GENERAL_ERROR;
        code = ProToolkitTaskExecute(handle, function, inputs, &outputs, &returned);
        int count = 0;
        if (code || returned || !outputs || ProArraySizeGet((ProArray)outputs, &count) ||
            count != 1 || outputs[0].value.type != PRO_VALUE_TYPE_WSTRING || !outputs[0].value.v.w)
            throw std::runtime_error("Callback live identity unavailable (Toolkit " +
                                     std::to_string(code) + ", callback " +
                                     std::to_string(returned) + ")");
        identity = J::parse(utf8(outputs[0].value.v.w));
        if (identity.value("nonce", "") != nonce)
            throw std::runtime_error("Callback live identity nonce mismatch");
    } catch (...) {
        if (outputs)
            ProArgumentProarrayFree(&outputs);
        if (inputs)
            ProArgumentProarrayFree(&inputs);
        throw;
    }
    ProError freed_output = ProArgumentProarrayFree(&outputs);
    ProError freed_input = ProArgumentProarrayFree(&inputs);
    if (freed_output || freed_input)
        throw std::runtime_error("Cannot free callback probe arguments");
    identity.erase("nonce");
    return identity;
}

static J callback_runtime_status(const std::filesystem::path &build,
                                 ProToolkitDllHandle &verified_module, std::string &command) {
    verified_module = nullptr;
    J status = {{"readiness", "unknown"}, {"registration_status", "unknown"}};
    try {
        J setup = read_callback_json(build / L"blend_callback_setup.json");
        status["deployed"] = {
            {"dll_sha256", setup.at("dll_sha256")},   {"loader_sha256", setup.at("loader_sha256")},
            {"loader_file", setup.at("loader_file")}, {"module_file", setup.at("module_file")},
            {"protocol", setup.at("protocol")},       {"contract", setup.at("contract")}};
        status["registry_file"] = setup.at("registry_file");
        if (setup.value("protocol", 0) != mechdog_callback::protocol ||
            setup.value("contract", "") != mechdog_callback::contract ||
            setup.value("loader_abi", 0) != mechdog_callback::loader_abi ||
            mechdog_callback::sha256(wide(setup.at("module_file"))) != setup.at("dll_sha256") ||
            mechdog_callback::sha256(wide(setup.at("loader_file"))) != setup.at("loader_sha256")) {
            status["readiness"] = "version_mismatch";
            status["reason"] = "worker_or_artifact_incompatible";
            status["instruction"] =
                "Rebuild this worker and prepare a matching deployment; do not model";
            return status;
        }
        std::vector<std::filesystem::path> records = {wide(setup.at("ready_file"))};
        // Old loader generations are candidates only. Their files never establish readiness.
        auto loaders = build / L"blend_loader";
        if (std::filesystem::is_directory(loaders))
            for (const auto &entry : std::filesystem::directory_iterator(loaders))
                if (entry.is_directory())
                    records.push_back(entry.path() / L"callback_result.json");
        bool recorded = false, identity_failed = false;
        J mismatch;
        for (const auto &record : records) {
            if (!std::filesystem::is_regular_file(record))
                continue;
            J state;
            try {
                state = read_callback_json(record);
            } catch (const std::exception &) {
                identity_failed = true;
                continue;
            }
            if (!state.contains("application_id"))
                continue;
            recorded = true;
            std::wstring id_value = wide(state.at("application_id"));
            if (id_value.size() >= PRO_NAME_SIZE)
                continue;
            ProName id;
            wcscpy_s(id, id_value.c_str());
            ProToolkitDllHandle handle = nullptr;
            ProError lookup = ProToolkitDllHandleGet(id, &handle);
            if (lookup == PRO_TK_E_NOT_FOUND || lookup == PRO_TK_BAD_CONTEXT)
                continue;
            if (lookup || !handle) {
                identity_failed = true;
                continue;
            }
            J loaded;
            try {
                loaded = callback_live_identity(handle);
            } catch (const std::exception &error) {
                status["probe_error"] = error.what();
                identity_failed = true;
                continue;
            }
            bool matches = loaded.value("protocol", 0) == mechdog_callback::protocol &&
                           loaded.value("contract", "") == mechdog_callback::contract &&
                           loaded.value("loader_abi", 0) == mechdog_callback::loader_abi &&
                           loaded.value("initialize_code", -1) == 0 &&
                           // A stopped loader/identity handler cannot answer the nonce.
                           // Early v3 payloads omit the optional false termination flag.
                           !loaded.value("terminated", false);
            for (const char *field : {"dll_sha256", "loader_sha256", "command", "module_file",
                                      "loader_file", "resource_root"})
                matches = matches && loaded.value(field, "") == setup.value(field, "");
            if (!matches) {
                mismatch = loaded;
                continue;
            }
            status["loaded"] = loaded;
            status["readiness"] = loaded.value("active_request", true) ? "unknown" : "ready";
            status["reason"] =
                loaded.value("active_request", true) ? "callback_busy" : "live_identity_verified";
            status["instruction"] =
                loaded.value("active_request", true)
                    ? "Inspect the previous Blend job; never reset or replay an unknown request"
                    : "Callback verified in the selected session; this is a point-in-time "
                      "observation";
            if (!loaded.value("active_request", true)) {
                verified_module = handle;
                command = setup.at("command");
            }
            return status;
        }
        if (!mismatch.is_null()) {
            status["loaded"] = mismatch;
            status["readiness"] = "version_mismatch";
            status["reason"] = "loaded_deployment_differs";
            status["next_action"] = "restart_creo_then_start_registered_application";
            if (mismatch.value("loader_file", "") != setup.value("loader_file", ""))
                status["next_action"] =
                    "restart_creo_read_persistent_registration_or_refresh_session_entry";
            status["instruction"] =
                "Preserve loaded files. Finish known jobs, normally restart Creo, then start the "
                "registered application. If loader/SDK generation changed, let persistent config "
                "read the same registry_file on restart; a session-only registration may need "
                "refreshing from that fixed file. Query again before modeling.";
        } else {
            status["readiness"] = recorded && !identity_failed ? "not_loaded" : "unknown";
            status["reason"] = identity_failed ? "live_identity_unavailable"
                               : recorded      ? "recorded_application_not_active"
                                               : "no_runtime_identity_record";
            status["next_action"] = "start_or_register_application_manually";
            status["instruction"] =
                "GUI registration cannot be queried. If this generation is already registered, "
                "start it in Auxiliary Applications; otherwise register registry_file once and "
                "review its DLL prompt. If this loader was previously stopped or startup failed, "
                "normally restart Creo before starting it again. Legacy protocol-2 registrations "
                "require migration. If the entry disappears after restart, fix its persistent "
                "config.pro registry reference once; the generated config snippet is not loaded "
                "automatically. A listed entry that is not running needs manual Start. Query "
                "again before modeling.";
        }
    } catch (const std::exception &error) {
        status["readiness"] = "unknown";
        status["reason"] = "invalid_or_missing_artifacts";
        status["probe_error"] = error.what();
        status["instruction"] =
            "Build and verify this installation's callback artifacts before manual setup";
    }
    return status;
}
