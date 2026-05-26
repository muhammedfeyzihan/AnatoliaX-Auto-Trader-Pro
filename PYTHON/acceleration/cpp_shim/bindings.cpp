// cpp_shim/bindings.cpp — pybind11 C++ modul baglantisi
//
// Exported Python modulu: anatoliax_cpp
// Siniflar:
// - NanosecondClock: now_ns(), elapsed_ns(), tsc_calibrate()
// - ParsedTick: symbol, price, volume, timestamp_ns
// - OrderBook: add_order(), modify_order(), cancel_order(), execute_trade()

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <string>
#include <cstdint>

namespace py = pybind11;

// Ileride clock.cpp'ten tanimlar gelecek; simdilik yer tutucu
uint64_t now_ns_stub();

class NanosecondClock {
public:
    uint64_t now_ns() const { return now_ns_stub(); }
    uint64_t elapsed_ns(uint64_t start) const { return now_ns_stub() - start; }
    void tsc_calibrate() {}
};

struct ParsedTick {
    std::string symbol;
    double price;
    double volume;
    uint64_t timestamp_ns;
};

class OrderBook {
public:
    void add_order(const std::string& id, double price, double volume, const std::string& side) {}
    void modify_order(const std::string& id, double new_price, double new_volume) {}
    void cancel_order(const std::string& id) {}
    void execute_trade(const std::string& id, double qty) {}
    double mid_price() const { return 0.0; }
    double spread() const { return 0.0; }
};

uint64_t now_ns_stub() {
    // Yer tutucu: gercek TSC/rdtsc implementasyonu ileride eklenecek
    return 0;
}

PYBIND11_MODULE(anatoliax_cpp, m) {
    m.doc() = "AnatoliaX C++ performans shimi (pybind11)";

    py::class_<NanosecondClock>(m, "NanosecondClock")
        .def(py::init<>())
        .def("now_ns", &NanosecondClock::now_ns)
        .def("elapsed_ns", &NanosecondClock::elapsed_ns)
        .def("tsc_calibrate", &NanosecondClock::tsc_calibrate);

    py::class_<ParsedTick>(m, "ParsedTick")
        .def(py::init<>())
        .def_readwrite("symbol", &ParsedTick::symbol)
        .def_readwrite("price", &ParsedTick::price)
        .def_readwrite("volume", &ParsedTick::volume)
        .def_readwrite("timestamp_ns", &ParsedTick::timestamp_ns);

    py::class_<OrderBook>(m, "OrderBook")
        .def(py::init<>())
        .def("add_order", &OrderBook::add_order)
        .def("modify_order", &OrderBook::modify_order)
        .def("cancel_order", &OrderBook::cancel_order)
        .def("execute_trade", &OrderBook::execute_trade)
        .def("mid_price", &OrderBook::mid_price)
        .def("spread", &OrderBook::spread);
}
