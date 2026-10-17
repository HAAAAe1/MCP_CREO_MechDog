// Synchronous selection callback. Only the immutable, private request next to
// this per-operation DLL copy can supply the model, command and native curves.
#define NOMINMAX
#include <windows.h>
#include <ProToolkitDll.h>
#include <ProUICmd.h>
#include <ProMdl.h>
#include <ProModelitem.h>
#include <ProSelection.h>
#include <ProArray.h>
#include <fstream>
#include <filesystem>
#include <string>
#include <vector>
#include "third_party/json.hpp"
#include "callback_identity.h"
#include "callback_api.h"
static const MechDogCallbackApi *host = nullptr;
using Json = nlohmann::json;
static std::wstring directory, expected_model;
static std::vector<int> curve_ids;
static Json outcome = {{"selected", 0}, {"codes", Json::array()}};
static size_t section_index = 0;
static bool resident = false, active = false;
static std::wstring module_directory, resource_root, current_request;
static std::string resident_command;
static Json resident_identity;
static std::filesystem::path identity_file;
static void persist_identity() {
    std::ofstream file(identity_file, std::ios::binary);
    file << resident_identity.dump(2);
    if (!file)
        throw std::runtime_error("Cannot publish callback identity");
}
static bool safe_token(const std::string &value) {
    if (value.empty() || value.size() > 70)
        return false;
    for (char c : value)
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == '_'))
            return false;
    return true;
}
static void persist() {
    std::ofstream f(directory + L"\\callback_result.json", std::ios::binary);
    f << outcome.dump(2);
}

static std::wstring from_utf8(const std::string &value) {
    int size = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                                   nullptr, 0);
    if (!size)
        throw std::runtime_error("Invalid callback path");
    std::wstring result(size, L'\0');
    MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(), (int)value.size(),
                        result.data(), size);
    return result;
}

static std::string to_utf8(const std::wstring &value) {
    int size = WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), nullptr, 0, nullptr,
                                   nullptr);
    std::string result(size, '\0');
    if (size)
        WideCharToMultiByte(CP_UTF8, 0, value.data(), (int)value.size(), result.data(), size,
                            nullptr, nullptr);
    return result;
}

// Required by the Toolkit DLL link support, but payloads are never registered directly.
extern "C" __declspec(dllexport) int user_initialize(int, char **, char *, char *,
                                                     wchar_t errmsg[80]) {
    wcscpy_s(errmsg, 80, L"Register the MechDog loader protk.dat, not the callback payload");
    return PRO_TK_BAD_CONTEXT;
}

static void configure_request(const Json &request) {
    std::string name = request.at("model_name");
    if (!safe_token(name) || name.size() > 31)
        throw std::runtime_error("Invalid callback model");
    auto ids = request.at("curve_ids").get<std::vector<int>>();
    if (ids.size() < 2 || ids.size() > 20)
        throw std::runtime_error("Invalid callback section count");
    for (int id : ids)
        if (id < 0)
            throw std::runtime_error("Invalid callback curve");
    expected_model.assign(name.begin(), name.end());
    curve_ids = std::move(ids);
    section_index = 0;
}

// A resident callback is loaded by the operator before modeling, so PROMPT
// policy never blocks an asynchronous modeling worker on DLL authorization.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendPrepare(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || active || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        int count = 0;
        ProError code = host->array_size((ProArray)inputs, &count);
        if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
            !inputs[0].value.v.w)
            return PRO_TK_BAD_INPUTS;
        auto file = std::filesystem::weakly_canonical(inputs[0].value.v.w);
        auto jobs =
            std::filesystem::weakly_canonical(std::filesystem::path(resource_root) / L"jobs");
        auto a = jobs.begin(), b = file.begin();
        for (; a != jobs.end(); ++a, ++b)
            if (b == file.end() || _wcsicmp(a->c_str(), b->c_str()))
                return PRO_TK_BAD_INPUTS;
        if (file.filename() != L"callback_request.json")
            return PRO_TK_BAD_INPUTS;
        std::ifstream input(file, std::ios::binary);
        Json request;
        input >> request;
        if (request.value("protocol", 0) != mechdog_callback::protocol)
            return PRO_TK_BAD_INPUTS;
        configure_request(request);
        ProMdl model = nullptr;
        ProMdlName name = L"";
        code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (code || _wcsicmp(name, expected_model.c_str()))
            return code ? code : PRO_TK_BAD_CONTEXT;
        directory = file.parent_path().wstring();
        current_request = file.wstring();
        outcome = {{"protocol", mechdog_callback::protocol},
                   {"selected", 0},
                   {"codes", Json::array()},
                   {"command", resident_command},
                   {"prepared", true}};
        persist();
        active = true;
        return PRO_TK_NO_ERROR;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendRelease(ProArgument *inputs,
                                                          ProArgument **outputs) {
    if (outputs)
        *outputs = nullptr;
    if (!resident || !active || !inputs)
        return PRO_TK_BAD_CONTEXT;
    try {
        int count = 0;
        ProError code = host->array_size((ProArray)inputs, &count);
        if (code || count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING ||
            !inputs[0].value.v.w ||
            std::filesystem::weakly_canonical(inputs[0].value.v.w).wstring() != current_request)
            return PRO_TK_BAD_INPUTS;
        outcome["released"] = true;
        persist();
        active = false;
        curve_ids.clear();
        return PRO_TK_NO_ERROR;
    } catch (...) {
        return PRO_TK_BAD_INPUTS;
    }
}
static uiCmdAccessState access(uiCmdAccessMode) {
    return ACCESS_AVAILABLE;
}
static int select_section(uiCmdCmdId, uiCmdValue *, void *) {
    if (!resident || !active || resident_identity.value("terminated", true))
        return 0;
    ProSelection selected = nullptr;
    try {
        ProMdl model = nullptr;
        ProMdlName name = L"";
        ProError code = host->current_model(&model);
        if (!code)
            code = host->model_name(model, name);
        if (!code && (_wcsicmp(name, expected_model.c_str()) || section_index >= curve_ids.size()))
            code = PRO_TK_BAD_CONTEXT;
        ProModelitem item;
        if (!code)
            code = host->model_item(model, curve_ids[section_index], PRO_CURVE, &item);
        if (!code)
            code = host->selection_alloc(nullptr, &item, &selected);
        if (!code)
            code = host->selection_record(selected, PRO_SELECT_OVERRIDE);
        if (selected) {
            host->selection_free(&selected);
            selected = nullptr;
        }
        outcome["codes"].push_back(code);
        if (!code)
            section_index++;
        outcome["selected"] = section_index;
        persist();
    } catch (...) {
        if (selected)
            host->selection_free(&selected);
        try {
            outcome["exception"] = true;
            persist();
        } catch (...) {
        }
    }
    return 0;
}
extern "C" __declspec(dllexport) int MechDogBlendInitialize(int, char **, char *, char *,
                                                            wchar_t errmsg[80],
                                                            const wchar_t *application_id,
                                                            const wchar_t *loader_file,
                                                            const MechDogCallbackApi *api) {
    try {
        if (!api || api->abi != mechdog_callback::loader_abi ||
            api->size != sizeof(MechDogCallbackApi))
            return PRO_TK_BAD_INPUTS;
        host = api;
        wchar_t filename[MAX_PATH];
        HMODULE module = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&MechDogBlendInitialize, &module) ||
            !GetModuleFileNameW(module, filename, MAX_PATH))
            return PRO_TK_GENERAL_ERROR;
        directory = filename;
        directory = directory.substr(0, directory.find_last_of(L"\\"));
        module_directory = directory;
        resident = true;
        std::ifstream input(directory + L"\\callback_bootstrap.json");
        Json request;
        input >> request;
        std::string command = request.at("command");
        if (!safe_token(command))
            return PRO_TK_BAD_INPUTS;
        if (resident) {
            auto actual_root = std::filesystem::path(filename)
                                   .parent_path()
                                   .parent_path()
                                   .parent_path()
                                   .parent_path();
            if (request.value("protocol", 0) != mechdog_callback::protocol ||
                request.value("contract", "") != mechdog_callback::contract ||
                _wcsicmp(actual_root.c_str(), from_utf8(request.at("resource_root")).c_str()) ||
                request.value("dll_sha256", "") != mechdog_callback::sha256(filename) ||
                !application_id || !*application_id || !loader_file || !*loader_file)
                return PRO_TK_BAD_INPUTS;
            resource_root = from_utf8(request.at("resource_root"));
            resident_command = command;
            outcome["protocol"] = mechdog_callback::protocol;
            outcome["terminated"] = false;
            outcome["command"] = command;
            outcome["contract"] = mechdog_callback::contract;
            outcome["resource_root"] = request.at("resource_root");
            outcome["module_file"] = std::filesystem::path(filename).u8string();
            outcome["dll_sha256"] = request.at("dll_sha256");
            outcome["loader_file"] = std::filesystem::path(loader_file).u8string();
            outcome["loader_sha256"] = mechdog_callback::sha256(loader_file);
            outcome["loader_abi"] = mechdog_callback::loader_abi;
            outcome["process_id"] = GetCurrentProcessId();
            identity_file =
                std::filesystem::path(loader_file).parent_path() / L"callback_result.json";
        } else {
            configure_request(request);
        }
        // Persist Creo's real identifier before exposing the command. A later worker
        // can locate this module after a loader prompt outlives the original process.
        outcome["initialize_stage"] = "before_application_id";
        outcome["initialize_tick_ms"] = GetTickCount64();
        persist();
        // The registered loader supplies its identifier. The payload itself is
        // never independently registered as a Toolkit application.
        ProError identified =
            application_id && *application_id ? PRO_TK_NO_ERROR : PRO_TK_BAD_INPUTS;
        outcome["application_id_code"] = identified;
        outcome["initialize_stage"] = "after_application_id";
        if (!identified) {
            std::wstring id = application_id;
            outcome["application_id"] = to_utf8(id);
        }
        persist();
        if (identified)
            return identified;
        outcome["initialize_stage"] = "before_command_register";
        persist();
        uiCmdCmdId action;
        ProError code = host->command_add(command.data(), select_section, uiProeAsynch, access,
                                          PRO_B_FALSE, PRO_B_FALSE, &action);
        outcome["initialize_code"] = code;
        outcome["initialize_stage"] = "after_command_register";
        persist();
        if (resident) {
            resident_identity = outcome;
            persist_identity();
        }
        return code;
    } catch (...) {
        wcscpy_s(errmsg, 80, L"Invalid MechDog Blend callback request");
        return PRO_TK_BAD_INPUTS;
    }
}
extern "C" __declspec(dllexport) void user_terminate() {
    try {
        outcome["terminated"] = true;
        persist();
        if (resident) {
            resident_identity["terminated"] = true;
            persist_identity();
        }
    } catch (...) {
    }
}

// A live response, not an initialization file, proves that this exact module is
// running in the selected Creo session. It does not reset an active request.
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendIdentity(ProArgument *inputs,
                                                           ProArgument **outputs) {
    if (!outputs)
        return PRO_TK_BAD_INPUTS;
    *outputs = nullptr;
    try {
        if (!resident || !host || resident_identity.value("initialize_code", -1) != 0 ||
            resident_identity.value("terminated", false))
            return PRO_TK_BAD_CONTEXT;
        int count = 0;
        ProError array_code =
            inputs ? host->array_size((ProArray)inputs, &count) : PRO_TK_BAD_INPUTS;
        if (array_code)
            return array_code;
        if (count != 1 || inputs[0].value.type != PRO_VALUE_TYPE_WSTRING || !inputs[0].value.v.w)
            return PRO_TK_BAD_INPUTS;
        std::wstring nonce = inputs[0].value.v.w;
        if (nonce.size() != 32 ||
            nonce.find_first_not_of(L"0123456789abcdef") != std::wstring::npos)
            return PRO_TK_BAD_INPUTS;
        Json identity = resident_identity;
        identity.erase("application_id");
        identity["nonce"] = to_utf8(nonce);
        identity["active_request"] = active;
        ProError code = host->array_alloc(1, sizeof(ProArgument), 1, (ProArray *)outputs);
        if (code)
            return code;
        (*outputs)[0] = {};
        wcscpy_s((*outputs)[0].label, L"identity");
        (*outputs)[0].value.type = PRO_VALUE_TYPE_WSTRING;
        auto value = from_utf8(identity.dump());
        code = host->wstring_set(&(*outputs)[0].value, value.data());
        if (code)
            host->arguments_free(outputs);
        return code;
    } catch (...) {
        if (*outputs)
            host->arguments_free(outputs);
        return PRO_TK_GENERAL_ERROR;
    }
}
