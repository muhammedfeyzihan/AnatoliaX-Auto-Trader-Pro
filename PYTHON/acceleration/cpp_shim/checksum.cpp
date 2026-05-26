// cpp_shim/checksum.cpp — Fast checksum/CRC32
#include <cstdint>
#include <cstddef>

extern "C" {
    uint32_t crc32_simple(const uint8_t* data, size_t len) {
        uint32_t crc = 0xFFFFFFFF;
        for (size_t i = 0; i < len; ++i) {
            crc ^= data[i];
            for (int j = 0; j < 8; ++j) {
                crc = (crc >> 1) ^ (0xEDB88320 & -(crc & 1));
            }
        }
        return ~crc;
    }
}
