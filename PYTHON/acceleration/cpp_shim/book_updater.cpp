// cpp_shim/book_updater.cpp — L1/L2 order book updater
#include <cstdint>
#include <cstring>

struct BookLevel {
    double price;
    uint32_t qty;
};

struct OrderBook {
    BookLevel bids[5];
    BookLevel asks[5];
    uint64_t timestamp_ns;
};

extern "C" {
    void update_book(OrderBook* book, const char side, double price, uint32_t qty) {
        if (side == 'B') {
            book->bids[0].price = price;
            book->bids[0].qty = qty;
        } else {
            book->asks[0].price = price;
            book->asks[0].qty = qty;
        }
    }
}
