// The operator registers this immutable loader once per loader/SDK generation.
// Only explicit GUI startup reads deployment.json and loads the selected payload.
#define NOMINMAX
#include <windows.h>
#include <ProToolkitDll.h>
#include <ProArray.h>
#include <filesystem>
#include <fstream>
#include "third_party/json.hpp"
#include "callback_identity.h"
#include "callback_api.h"

static HMODULE payload = nullptr;
static bool initialized = false;
static bool attempted = false;
using Initialize = int (*)(int, char **, char *, char *, wchar_t *, const wchar_t *,
                           const wchar_t *, const MechDogCallbackApi *);
static const MechDogCallbackApi host_api = {
    mechdog_callback::loader_abi,
    sizeof(MechDogCallbackApi),
    &ProArraySizeGet,
    &ProArrayAlloc,
    &ProArgumentProarrayFree,
    &ProValuedataWstringSet,
    &ProMdlCurrentGet,
    &ProMdlMdlnameGet,
    &ProModelitemInit,
    &ProSelectionAlloc,
    &ProSelectExternalselectionRecord,
    &ProSelectionFree,
    &ProCmdActionAdd,
};
using Terminate = void (*)();
static Terminate terminate_payload = nullptr;
static ProTkdllFunction prepare_payload = nullptr, release_payload = nullptr,
                        identity_payload = nullptr;

extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendPrepare(ProArgument *in, ProArgument **out) {
    return initialized ? prepare_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendRelease(ProArgument *in, ProArgument **out) {
    return initialized ? release_payload(in, out) : PRO_TK_BAD_CONTEXT;
}
extern "C" PRO_TK_DLL_EXPORT ProError MechDogBlendIdentity(ProArgument *in, ProArgument **out) {
    return initialized ? identity_payload(in, out) : PRO_TK_BAD_CONTEXT;
}

extern "C" __declspec(dllexport) int user_initialize(int argc, char **argv, char *version,
                                                     char *build, wchar_t errmsg[80]) {
    if (attempted) {
        wcscpy_s(errmsg, 80, L"Restart Creo before starting this loader again");
        return PRO_TK_BAD_CONTEXT;
    }
    attempted = true;
    try {
        wchar_t filename[MAX_PATH];
        HMODULE self = nullptr;
        if (!GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS |
                                    GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                                (LPCWSTR)&user_initialize, &self) ||
            !GetModuleFileNameW(self, filename, MAX_PATH))
            throw std::runtime_error("Cannot identify loader");
        auto directory = std::filesystem::path(filename).parent_path();
        std::ifstream input(directory / L"deployment.json", std::ios::binary);
        nlohmann::json deployment;
        input >> deployment;
        std::string digest = deployment.at("dll_sha256");
        if (deployment.value("loader_abi", 0) != mechdog_callback::loader_abi ||
            !mechdog_callback::digest_valid(digest))
            throw std::runtime_error("Unsupported loader deployment");
        // Derive the absolute payload path from our own installation. The pointer
        // cannot redirect a registered loader into another installation directory.
        auto module =
            directory.parent_path().parent_path() / L"blend_callback" / digest / L"callback.dll";
        if (mechdog_callback::sha256(module) != digest)
            throw std::runtime_error("Callback payload hash mismatch");
        ProName application_id;
        ProError identified = ProToolkitDllIdGet(nullptr, application_id);
        if (identified)
            return identified;
        payload = LoadLibraryExW(module.c_str(), nullptr, LOAD_WITH_ALTERED_SEARCH_PATH);
        if (!payload)
            throw std::runtime_error("Cannot load callback payload");
        auto initialize = (Initialize)GetProcAddress(payload, "MechDogBlendInitialize");
        terminate_payload = (Terminate)GetProcAddress(payload, "user_terminate");
        prepare_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendPrepare");
        release_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendRelease");
        identity_payload = (ProTkdllFunction)GetProcAddress(payload, "MechDogBlendIdentity");
        if (!initialize || !terminate_payload || !prepare_payload || !release_payload ||
            !identity_payload)
            throw std::runtime_error("Callback loader ABI exports missing");
        int code =
            initialize(argc, argv, version, build, errmsg, application_id, filename, &host_api);
        initialized = code == PRO_TK_NO_ERROR;
        // Never unload partially initialized code: a Toolkit command may already
        // reference it. Preserve it until process exit and report failure.
        return code;
    } catch (...) {
        wcscpy_s(errmsg, 80,
                 L"Callback setup invalid; rebuild and inspect deployment before startup");
        return PRO_TK_BAD_INPUTS;
    }
}

extern "C" __declspec(dllexport) void user_terminate() {
    if (initialized)
        terminate_payload();
    initialized = false;
    // No FreeLibrary: Creo command callbacks can outlive an application stop.
    // The process owns the payload image until a normal Creo restart.
}
