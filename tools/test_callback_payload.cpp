// Standalone ABI/state regression. Model calls are controlled fixtures, not Creo geometry.
#define NOMINMAX
#include <windows.h>
#include "../native/callback_api.h"
#include "../native/third_party/json.hpp"
#include <filesystem>
#include <fstream>
#include <stdexcept>
using J = nlohmann::json;
static uiCmdCmdActFn selection_action = nullptr;
static int recorded_selections = 0;
static ProError add(char *, uiCmdCmdActFn action, uiCmdPriority, uiCmdAccessFn, ProBoolean,
                    ProBoolean, uiCmdCmdId *id) {
    selection_action = action;
    *id = {};
    return PRO_TK_NO_ERROR;
}
static ProError current(ProMdl *model) {
    *model = reinterpret_cast<ProMdl>(1);
    return PRO_TK_NO_ERROR;
}
static ProError name(ProMdl, ProMdlName model_name) {
    wcscpy_s(model_name, PRO_NAME_SIZE, L"fixture_model");
    return PRO_TK_NO_ERROR;
}
static ProError item(ProMdl model, int id, ProType type, ProModelitem *value) {
    *value = {};
    value->owner = model;
    value->id = id;
    value->type = type;
    return PRO_TK_NO_ERROR;
}
static ProError allocate_selection(ProAsmcomppath *, ProModelitem *, ProSelection *selection) {
    *selection = reinterpret_cast<ProSelection>(1);
    return PRO_TK_NO_ERROR;
}
static ProError record_selection(ProSelection, ProSelectRecordAction) {
    ++recorded_selections;
    return PRO_TK_NO_ERROR;
}
static ProError free_selection(ProSelection *selection) {
    *selection = nullptr;
    return PRO_TK_NO_ERROR;
}
static void require(bool condition, const char *message) {
    if (!condition)
        throw std::runtime_error(message);
}
static J read(const std::filesystem::path &file) {
    std::ifstream input(file);
    J value;
    input >> value;
    return value;
}
static ProError call(ProTkdllFunction function, const std::wstring &value, J *output = nullptr) {
    ProArgument *inputs = nullptr, *outputs = nullptr;
    require(ProArrayAlloc(1, sizeof(ProArgument), 1, (ProArray *)&inputs) == 0, "allocate inputs");
    inputs[0] = {};
    wcscpy_s(inputs[0].label, L"request");
    inputs[0].value.type = PRO_VALUE_TYPE_WSTRING;
    require(ProValuedataWstringSet(&inputs[0].value, const_cast<wchar_t *>(value.c_str())) == 0,
            "set input");
    ProError code = function(inputs, &outputs);
    if (!code && output) {
        int count = 0;
        require(outputs && ProArraySizeGet((ProArray)outputs, &count) == 0 && count == 1,
                "one output");
        require(outputs[0].label[0] && outputs[0].value.type == PRO_VALUE_TYPE_WSTRING,
                "named wide-string output");
        std::wstring text = outputs[0].value.v.w;
        int bytes = WideCharToMultiByte(CP_UTF8, 0, text.data(), (int)text.size(), nullptr, 0,
                                        nullptr, nullptr);
        std::string encoded(bytes, '\0');
        WideCharToMultiByte(CP_UTF8, 0, text.data(), (int)text.size(), encoded.data(), bytes,
                            nullptr, nullptr);
        *output = J::parse(encoded);
    }
    if (outputs)
        require(ProArgumentProarrayFree(&outputs) == 0, "free output");
    require(ProArgumentProarrayFree(&inputs) == 0, "free input");
    return code;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 5)
        return 2;
    J report = {{"success", false},
                {"scope", "standalone SDK allocation and fixture-model ABI; no Creo modeling"}};
    try {
        HMODULE module = LoadLibraryW(argv[1]);
        require(module != nullptr, "load compiled payload");
        using Init = int (*)(int, char **, char *, char *, wchar_t *, const wchar_t *,
                             const wchar_t *, const MechDogCallbackApi *);
        auto initialize = (Init)GetProcAddress(module, "MechDogBlendInitialize");
        auto identity = (ProTkdllFunction)GetProcAddress(module, "MechDogBlendIdentity");
        auto prepare = (ProTkdllFunction)GetProcAddress(module, "MechDogBlendPrepare");
        auto release = (ProTkdllFunction)GetProcAddress(module, "MechDogBlendRelease");
        auto terminate = (void (*)())GetProcAddress(module, "user_terminate");
        require(initialize && identity && prepare && release && terminate, "ABI exports");
        require(call(identity, L"0123456789abcdef0123456789abcdef") == PRO_TK_BAD_CONTEXT,
                "uninitialized identity does not call a missing host API");
        MechDogCallbackApi api = {
            1,
            sizeof(MechDogCallbackApi),
            &ProArraySizeGet,
            &ProArrayAlloc,
            &ProArgumentProarrayFree,
            &ProValuedataWstringSet,
            &current,
            &name,
            &item,
            &allocate_selection,
            &record_selection,
            &free_selection,
            &add,
        };
        wchar_t error[80] = L"";
        char empty[] = "";
        require(initialize(0, nullptr, empty, empty, error, L"standalone_fixture", argv[2], &api) ==
                    0,
                "initialize fixture");
        const std::wstring nonce = L"0123456789abcdef0123456789abcdef";
        J initial;
        require(call(identity, nonce, &initial) == 0 &&
                    initial["nonce"] == "0123456789abcdef0123456789abcdef" &&
                    initial["terminated"] == false && initial["active_request"] == false,
                "live idle identity");
        // A stale file cannot alter the live identity response.
        std::ofstream(std::filesystem::path(argv[2]).parent_path() / L"callback_result.json")
            << "{}";
        J fresh;
        require(call(identity, nonce, &fresh) == 0 && fresh == initial,
                "ignore stale identity file");
        require(!std::filesystem::exists(std::filesystem::path(argv[2]).parent_path() /
                                         L"callback_probe.json"),
                "identity query does not create a diagnostic file");
        require(call(prepare, L"outside_jobs/callback_request.json") == PRO_TK_BAD_INPUTS,
                "reject request outside installation jobs");
        require(call(prepare, argv[3]) == 0, "prepare fixture request");
        J active;
        require(call(identity, nonce, &active) == 0 && active["active_request"] == true,
                "active request remains visible");
        require(call(prepare, argv[3]) == PRO_TK_BAD_CONTEXT, "reject second active request");
        require(selection_action != nullptr, "registered selection action");
        selection_action({}, nullptr, nullptr);
        selection_action({}, nullptr, nullptr);
        auto result_file = std::filesystem::path(argv[3]).parent_path() / L"callback_result.json";
        J selected = read(result_file);
        require(recorded_selections == 2 && selected["selected"] == 2,
                "initialized callback selects both fixture sections");
        require(call(release, argv[3]) == 0 && read(result_file)["released"] == true,
                "release exact request");
        terminate();
        require(call(identity, nonce) == PRO_TK_BAD_CONTEXT, "stopped callback cannot prove ready");
        report["success"] = true;
        report["selected_fixture_sections"] = recorded_selections;
        report["checks"] = 12;
    } catch (const std::exception &error) {
        report["failure"] = error.what();
    }
    std::ofstream output(argv[4], std::ios::binary);
    output << report.dump(2);
    return report["success"].get<bool>() ? 0 : 1;
}
