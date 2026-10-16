// Result evidence survives a blocked Toolkit disconnect. Never terminate Creo.
#pragma once
#include "third_party/json.hpp"
#include <Windows.h>
#include <fstream>
#include <string>
#include <thread>

static bool publish_native_json(const std::wstring &file, const nlohmann::json &value) {
    const std::wstring temporary = file + L".tmp";
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    output << value.dump(2);
    output.flush();
    bool written = output.good();
    output.close();
    return written && MoveFileExW(temporary.c_str(), file.c_str(),
                                  MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH);
}

template <typename Disconnect>
static int deliver_native_result(const std::wstring &job, nlohmann::json report, bool connected,
                                 Disconnect disconnect, DWORD disconnect_budget_ms = 20000) {
    report["native_pid"] = GetCurrentProcessId();
    report["delivery_complete"] = false;
    report["completion_stage"] = "before_disconnect";
    report["disconnect_code"] = nullptr;
    report["disconnect_budget_seconds"] = disconnect_budget_ms / 1000.0;
    const std::wstring checkpoint = job + L"\\native_checkpoint.json";
    if (!publish_native_json(checkpoint, report))
        return 32;
    if (connected) {
        HANDLE done = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        if (!done)
            return 32;
        // Toolkit stays on the calling thread. The watchdog only writes evidence
        // and exits this helper if the SDK's nominal 15 s limit fails to return.
        std::thread watchdog([=]() mutable {
            if (WaitForSingleObject(done, disconnect_budget_ms) == WAIT_TIMEOUT) {
                report["completion_stage"] = "disconnect_timeout";
                publish_native_json(checkpoint, report);
                ExitProcess(31);
            }
        });
        int code = disconnect();
        SetEvent(done);
        watchdog.join();
        CloseHandle(done);
        report["disconnect_code"] = code;
    }
    report["completion_stage"] = "result_delivery";
    report["delivery_complete"] = true;
    if (!publish_native_json(job + L"\\native_result.json", report))
        return 32;
    return report.value("success", false) ? 0 : 30;
}
