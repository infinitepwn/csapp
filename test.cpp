#include <iostream>
#include <mach/mach_time.h>
#include <sys/sysctl.h>
#include "opt/combine.h"

static double get_cpu_ghz() {
    uint64_t freq;
    size_t size = sizeof(freq);
    const char *keys[] = {"hw.cpufrequency", "hw.cpufrequency_max", "hw.cpufrequency_min"};
    for (int i = 0; i < 3; i++) {
        if (sysctlbyname(keys[i], &freq, &size, NULL, 0) == 0 && freq > 0) {
            std::cout << "Detected " << keys[i] << " = " << freq << " Hz\n";
            return (double)freq / 1e9;
        }
    }

    // 备选方案：可能 Apple Silicon 没有这些节点，使用 CPU 计数器（经验）。
    std::cout << "hw.cpufrequency* nodes not available. Could not detect GHz.\n";
    return 0.0;
}

int main() {
    const long LEN = 1000000;
    const int ITER = 100; // 迭代次数

    vec_ptr v = new_vec(LEN);
    if (!v) {
        std::cout << "Failed to create vector" << std::endl;
        return 1;
    }

    for (long i = 0; i < vec_length(v); i++) {
        set_vec_element(v, i, 1);
    }

    data_t result;

    // 获取时间基准
    mach_timebase_info_data_t timebase;
    mach_timebase_info(&timebase);

    double cpu_ghz = get_cpu_ghz();
    bool has_cpu_ghz = cpu_ghz > 0.0;

    auto do_measure = [&](void (*f)(vec_ptr, data_t *), const char *name) {
        uint64_t s = mach_absolute_time();
        for (int i = 0; i < ITER; i++) {
            f(v, &result);
        }
        uint64_t e = mach_absolute_time();
        uint64_t ticks = e - s;
        uint64_t ns = ticks * timebase.numer / timebase.denom;
        double sec = ns / 1e9;
        double time_iter = sec / ITER;
        double ticks_per_element = (double)ticks / (ITER * LEN);

        std::cout << name << " result=" << result << " total=" << sec << " s";
        std::cout << " per_iter=" << time_iter << " s";
        std::cout << " ticks_per_element=" << ticks_per_element;

        if (has_cpu_ghz) {
            double cycles_iter = time_iter * cpu_ghz * 1e9;
            double cpe_local = cycles_iter / LEN;
            std::cout << " cpe=" << cpe_local << " cycles/element";
        } else {
            std::cout << " (cpe unavailable, cpu freq unknown)";
        }

        std::cout << std::endl;
    };

    do_measure(combine1, "combine1");
    do_measure(combine2, "combine2");

    free_vec(v);
    return 0;
}