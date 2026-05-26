// cpp_shim/ring_buffer.cpp — SPSC lock-free ring buffer
#include <cstdint>
#include <atomic>

struct RingBuffer {
    uint8_t* buffer;
    size_t capacity;
    std::atomic<size_t> head{0};
    std::atomic<size_t> tail{0};
};

extern "C" {
    bool rb_push(RingBuffer* rb, const uint8_t* data, size_t len) {
        size_t h = rb->head.load(std::memory_order_relaxed);
        size_t t = rb->tail.load(std::memory_order_acquire);
        size_t used = (h - t) % rb->capacity;
        if (used + len >= rb->capacity) return false;
        for (size_t i = 0; i < len; ++i) {
            rb->buffer[(h + i) % rb->capacity] = data[i];
        }
        rb->head.store((h + len) % rb->capacity, std::memory_order_release);
        return true;
    }

    size_t rb_pop(RingBuffer* rb, uint8_t* out, size_t max_len) {
        size_t t = rb->tail.load(std::memory_order_relaxed);
        size_t h = rb->head.load(std::memory_order_acquire);
        size_t avail = (h - t) % rb->capacity;
        size_t to_read = avail < max_len ? avail : max_len;
        for (size_t i = 0; i < to_read; ++i) {
            out[i] = rb->buffer[(t + i) % rb->capacity];
        }
        rb->tail.store((t + to_read) % rb->capacity, std::memory_order_release);
        return to_read;
    }
}
