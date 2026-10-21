// Compile the production deadline without linking PTC or touching a Creo session.
#include "recovery_deadline.h"

int wmain(int argc, wchar_t **argv) {
    if (argc != 3)
        return 2;
    bool timeout = std::wstring(argv[1]) == L"timeout";
    RecoveryDeadline deadline(argv[2], timeout ? 100 : 1000);
    Sleep(timeout ? 5000 : 10);
    deadline.complete();
    return publish_native_json(std::wstring(argv[2]) + L"\\native_result.json",
                               {{"success", true}, {"deadline_completed", true}})
               ? 0
               : 32;
}
