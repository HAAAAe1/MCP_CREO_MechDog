// Shared, explicit callback wire contract. Change the contract for incompatible semantics.
#pragma once
#include <windows.h>
#include <bcrypt.h>
#include <filesystem>
#include <fstream>
#include <stdexcept>
#include <string>
#include <vector>
#pragma comment(lib, "bcrypt.lib")

namespace mechdog_callback {
constexpr int protocol = 3;
constexpr int loader_abi = 1;
constexpr const char *contract = "blend-selection-v3-ordered-curves-mm";

inline bool digest_valid(const std::string &value) {
    return value.size() == 64 && value.find_first_not_of("0123456789abcdef") == std::string::npos;
}

inline std::string sha256(const std::filesystem::path &file) {
    BCRYPT_ALG_HANDLE algorithm = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    std::vector<unsigned char> object;
    auto check = [](NTSTATUS status) {
        if (status < 0)
            throw std::runtime_error("Callback SHA256 verification failed");
    };
    try {
        check(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0));
        DWORD size = 0, returned = 0;
        check(BCryptGetProperty(algorithm, BCRYPT_OBJECT_LENGTH, (PUCHAR)&size, sizeof(size),
                                &returned, 0));
        object.resize(size);
        check(BCryptCreateHash(algorithm, &hash, object.data(), size, nullptr, 0, 0));
        std::ifstream input(file, std::ios::binary);
        if (!input)
            throw std::runtime_error("Cannot read callback binary");
        char block[65536];
        while (input.read(block, sizeof(block)) || input.gcount())
            check(BCryptHashData(hash, (PUCHAR)block, (ULONG)input.gcount(), 0));
        if (!input.eof())
            throw std::runtime_error("Cannot finish reading callback binary");
        unsigned char digest[32];
        check(BCryptFinishHash(hash, digest, sizeof(digest), 0));
        BCryptDestroyHash(hash);
        hash = nullptr;
        BCryptCloseAlgorithmProvider(algorithm, 0);
        algorithm = nullptr;
        constexpr char hex[] = "0123456789abcdef";
        std::string result;
        for (auto byte : digest) {
            result += hex[byte >> 4];
            result += hex[byte & 15];
        }
        return result;
    } catch (...) {
        if (hash)
            BCryptDestroyHash(hash);
        if (algorithm)
            BCryptCloseAlgorithmProvider(algorithm, 0);
        throw;
    }
}
} // namespace mechdog_callback
