// cpp_shim/feed_parser.cpp — High-performance tick parser
#include <cstdint>
#include <cstring>

struct ParsedTick {
    char symbol[8];
    double price;
    uint64_t timestamp_ns;
    uint32_t qty;
};

extern "C" {
    void parse_tick(const char* raw, ParsedTick* out) {
        // Stub: copy raw into out symbol for now
        std::strncpy(out->symbol, raw, 7);
        out->symbol[7] = '\0';
        out->price = 0.0;
        out->timestamp_ns = 0;
        out->qty = 0;
    }
}
