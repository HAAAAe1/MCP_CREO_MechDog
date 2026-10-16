// BUG-008 controlled helper test. No Creo/Toolkit calls and no real model success.
#define NOMINMAX
#include "result_delivery.h"
#include <filesystem>

int wmain(int argc, wchar_t **argv) {
    if (argc != 3)
        return 2;
    std::wstring job = argv[2];
    std::ifstream mode_file(job + L"\\scenario.txt");
    std::string mode;
    mode_file >> mode;
    nlohmann::json report = {
        {"success", true}, {"saved_file_reloaded_and_verified", true}, {"fixture_only", true}};
    if (mode == "write_failure")
        std::filesystem::create_directory(job + L"\\native_result.json");
    auto disconnect = [&]() {
        if (mode == "hang" || mode == "hang_default")
            Sleep(60000);
        return mode == "disconnect_failure" ? -38 : 0;
    };
    if (mode == "hang_default")
        return deliver_native_result(job, report, true, disconnect);
    return deliver_native_result(job, report, true, disconnect, 200);
}
