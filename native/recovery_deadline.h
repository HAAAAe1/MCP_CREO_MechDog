// Recovery phase deadline. It only terminates this worker, never Creo.
#pragma once
#include "result_delivery.h"
#include <stdexcept>

class RecoveryDeadline {
    HANDLE done = nullptr;
    std::thread watchdog;

  public:
    explicit RecoveryDeadline(const std::wstring &job, DWORD budget_ms = 90000) {
        done = CreateEventW(nullptr, TRUE, FALSE, nullptr);
        if (!done)
            throw std::runtime_error("Cannot create recovery budget event");
        try {
            HANDLE event = done;
            watchdog = std::thread([=]() {
                if (WaitForSingleObject(event, budget_ms) == WAIT_TIMEOUT) {
                    publish_native_json(job + L"\\native_checkpoint.json",
                                        {{"success", false},
                                         {"delivery_complete", false},
                                         {"completion_stage", "recovery_phase_timeout"},
                                         {"phase_budget_seconds", budget_ms / 1000.0}});
                    ExitProcess(31);
                }
            });
        } catch (...) {
            CloseHandle(done);
            throw;
        }
    }
    RecoveryDeadline(const RecoveryDeadline &) = delete;
    RecoveryDeadline &operator=(const RecoveryDeadline &) = delete;
    void complete() {
        if (done) {
            SetEvent(done);
            watchdog.join();
            CloseHandle(done);
            done = nullptr;
        }
    }
    ~RecoveryDeadline() {
        complete();
    }
};
