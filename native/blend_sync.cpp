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
using Json = nlohmann::json;
static std::wstring directory, expected_model;
static std::vector<int> curve_ids;
static Json outcome = {{"selected", 0}, {"codes", Json::array()}};
static size_t section_index = 0;
static bool resident = false, active = false;
static std::wstring module_directory, resource_root, current_request;
static std::string resident_command;
static Json resident_identity;
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
        ProError code = ProArraySizeGet((ProArray)inputs, &count);
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
        if (request.value("protocol", 0) != 2)
            return PRO_TK_BAD_INPUTS;
        configure_request(request);
        ProMdl model = nullptr;
        ProMdlName name = L"";
        code = ProMdlCurrentGet(&model);
        if (!code)
            code = ProMdlMdlnameGet(model, name);
        if (code || _wcsicmp(name, expected_model.c_str()))
            return code ? code : PRO_TK_BAD_CONTEXT;
        directory = file.parent_path().wstring();
        current_request = file.wstring();
        outcome = {{"protocol", 2},
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
        ProError code = ProArraySizeGet((ProArray)inputs, &count);
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
    ProSelection selected = nullptr;
    try {
        ProMdl model = nullptr;
        ProMdlName name = L"";
        ProError code = ProMdlCurrentGet(&model);
        if (!code)
            code = ProMdlMdlnameGet(model, name);
        if (!code && (_wcsicmp(name, expected_model.c_str()) || section_index >= curve_ids.size()))
            code = PRO_TK_BAD_CONTEXT;
        ProModelitem item;
        if (!code)
            code = ProModelitemInit(model, curve_ids[section_index], PRO_CURVE, &item);
        if (!code)
            code = ProSelectionAlloc(nullptr, &item, &selected);
        if (!code)
            code = ProSelectExternalselectionRecord(selected, PRO_SELECT_OVERRIDE);
        if (selected) {
            ProSelectionFree(&selected);
            selected = nullptr;
        }
        outcome["codes"].push_back(code);
        if (!code)
            section_index++;
        outcome["selected"] = section_index;
        persist();
    } catch (...) {
        if (selected)
            ProSelectionFree(&selected);
        try {
            outcome["exception"] = true;
            persist();
        } catch (...) {
        }
    }
    return 0;
}
extern "C" __declspec(dllexport) int user_initialize(int, char **, char *, char *,
                                                     wchar_t errmsg[80]) {
    try {
        wchar_t filename[MAX_PATH];
        HMODULE module = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&user_initialize, &module) ||
            !GetModuleFileNameW(module, filename, MAX_PATH))
            return PRO_TK_GENERAL_ERROR;
        directory = filename;
        directory = directory.substr(0, directory.find_last_of(L"\\"));
        module_directory = directory;
        resident = std::filesystem::is_regular_file(directory + L"\\callback_bootstrap.json");
        std::ifstream input(directory +
                            (resident ? L"\\callback_bootstrap.json" : L"\\callback_request.json"));
        Json request;
        input >> request;
        std::string command = request.at("command");
        if (!safe_token(command))
            return PRO_TK_BAD_INPUTS;
        if (resident) {
            if (request.value("protocol", 0) != 2)
                return PRO_TK_BAD_INPUTS;
            resource_root = from_utf8(request.at("resource_root"));
            resident_command = command;
            outcome["protocol"] = 2;
            outcome["command"] = command;
        } else {
            configure_request(request);
        }
        // Persist Creo's real identifier before exposing the command. A later worker
        // can locate this module after a loader prompt outlives the original process.
        outcome["initialize_stage"] = "before_application_id";
        outcome["initialize_tick_ms"] = GetTickCount64();
        persist();
        ProName application_id;
        ProError identified = ProToolkitDllIdGet(nullptr, application_id);
        outcome["application_id_code"] = identified;
        outcome["initialize_stage"] = "after_application_id";
        if (!identified) {
            std::wstring id = application_id;
            outcome["application_id"] = std::string(id.begin(), id.end());
        }
        persist();
        if (identified)
            return identified;
        outcome["initialize_stage"] = "before_command_register";
        persist();
        uiCmdCmdId action;
        ProError code = ProCmdActionAdd(command.data(), select_section, uiProeAsynch, access,
                                        PRO_B_FALSE, PRO_B_FALSE, &action);
        outcome["initialize_code"] = code;
        outcome["initialize_stage"] = "after_command_register";
        persist();
        if (resident)
            resident_identity = outcome;
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
            std::ofstream file(module_directory + L"\\callback_result.json", std::ios::binary);
            file << resident_identity.dump(2);
        }
    } catch (...) {
    }
}
