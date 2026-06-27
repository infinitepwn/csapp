# 第26讲：线程级并行（Thread-Level Parallelism）

> 来源：CS:APP 15-213 Introduction to Computer Systems，第26讲，2015年12月1日
> 讲师：Randal E. Bryant & David R. O'Hallaron

---

## 一、本讲概览

- **并行计算硬件**
  - 多核（Multicore）：单芯片上多个独立处理器
  - 超线程（Hyperthreading）：单核高效执行多线程
- **线程级并行**
  - 将程序划分为独立任务
  - 示例1：并行求和
  - 示例2：并行快速排序（分治并行）
- **一致性模型**：多线程读写共享状态时会发生什么

---

## 二、并行执行的动机

- 之前用线程处理 **I/O 延迟**（如每个客户端一个线程，防止互相阻塞）
- 多核/超线程 CPU 提供了新机会：
  - 将工作分散到并行执行的线程上
  - 多个独立任务时自动并行（如运行多个程序、服务多个客户端）
  - 也可以将**一个大任务**组织成多个并行子任务，从而加速

---

## 三、硬件基础

### 3.1 典型多核处理器结构

```
Core 0                  Core n-1
┌─────────────────┐     ┌─────────────────┐
│ Regs             │     │ Regs             │
│ L1 d-cache       │     │ L1 d-cache       │
│ L1 i-cache       │     │ L1 i-cache       │
│ L2 unified cache │     │ L2 unified cache │
└─────────────────┘     └─────────────────┘
         ┌─────────────────────────┐
         │ L3 unified cache        │
         │ （所有核共享）           │
         └─────────────────────────┘
                  Main Memory
```

- 多个处理器对内存有**一致的视图**（Coherent view of memory）

### 3.2 乱序执行（Out-of-Order）处理器结构

- 指令控制单元动态地将程序转换为操作流
- 操作被映射到多个功能单元（FU）上**并行执行**：
  - 整数算术单元（×2）
  - 浮点运算单元
  - Load/Store 单元

### 3.3 超线程实现（Hyperthreading）

- 复制足够的指令控制来处理 **K 个指令流**
- **K 份寄存器拷贝**（每个线程独立的 PC、寄存器堆、操作队列）
- **共享功能单元**
- 原理：当一个线程等待（如 cache miss）时，另一个线程可利用空闲的功能单元

### 3.4 基准测试机器

- Intel Xeon E5520 @ 2.27 GHz（Nehalem 架构，约2010年）
- **8个核**，每核支持 **2× 超线程**
- 信息来源：`/proc/cpuinfo`

---

## 四、示例1：并行求和

**任务**：求 0 到 n-1 的总和（结果应为 `(n-1)*n/2`）

**策略**：
- 将值域 `[1, n-1]` 分成 `t` 个范围，每个范围有 `n/t` 个值
- 每个线程处理一个范围（假设 n 是 t 的倍数）

### 4.1 方法一：全局变量求和（有问题）

```c
/* 错误示范：全局变量 */
void *sum_global(void *vargp) {
    // ... 直接累加到全局变量
    // 问题：存在竞态条件（race condition）
}
```

**问题**：多线程同时写全局变量，结果不可预期。

### 4.2 方法二：局部变量 + 全局数组

```c
/* 每个线程先算局部和，再写入全局数组对应槽 */
void *sum_local(void *vargp) {
    long myid = ((arg_t *)vargp)->id;
    long start = myid * (n / nthreads);
    long end   = start + n / nthreads;
    long sum   = 0;
    for (long i = start; i < end; i++)
        sum += i;
    gsum[myid] = sum;  // 每个线程写各自的槽
    return NULL;
}
```

- 主线程汇总各线程的局部和

### 4.3 性能分析：Amdahl's Law 的影响

| 线程数 | 加速比（理想） | 实际加速比 |
|--------|--------------|-----------|
| 1      | 1×           | ~1×       |
| 2      | 2×           | ~1.99×    |
| 4      | 4×           | ~3.91×    |
| 8      | 8×           | ~7.08×    |
| 16     | 16×          | ~13.2×    |

> **注意**：超过物理核数后（>8），加速比增长放缓，因为受超线程效率和串行部分限制。

### 4.4 伪共享问题（False Sharing）

- 即使每个线程写**不同的数组元素**，如果这些元素在**同一个 cache line** 中，会导致性能下降
- 原因：写一个槽会使其他线程的同一 cache line 失效（invalidate），触发不必要的缓存同步
- **解决方法**：使每个槽之间有足够间隔（stride），避免落入同一 cache line

```c
// 加 padding，使每个线程的数据在不同 cache line 上
typedef struct {
    long val;
    long pad[7];  // 凑够 64 字节（一个 cache line）
} padded_t;
padded_t gsum[MAXTHREADS];
```

---

## 五、示例2：并行快速排序

### 5.1 顺序快速排序

```c
void qsort_serial(data_t *base, size_t nele) {
    if (nele <= 1) return;
    if (nele == 2) {
        if (base[0] > base[1]) swap(base, base+1);
        return;
    }
    size_t m = partition(base, nele);  // 返回枢轴(pivot)的索引
    if (m > 1)        qsort_serial(base, m);
    if (nele-1 > m+1) qsort_serial(base+m+1, nele-m-1);
}
```

**过程**：
1. 选择"枢轴" p
2. 将 X 重排为：L（≤p）、p、R（≥p）
3. 递归排序 L 和 R
4. 返回 L : p : R

### 5.2 并行快速排序思路

- 若子数组大小 N ≤ Nthresh，使用**顺序快速排序**
- 否则：
  1. 选择枢轴 p，划分为 L 和 R
  2. **递归地 spawn 独立线程**分别排序 L 和 R
  3. 合并结果

### 5.3 顶层函数（简化）

```c
void tqsort(data_t *base, size_t nele) {
    init_task(nele);
    global_base = base;
    global_end  = global_base + nele - 1;
    task_queue_ptr tq = new_task_queue();
    tqsort_helper(base, nele, tq);
    join_tasks(tq);       // 等待所有线程完成
    free_task_queue(tq);
}
```

### 5.4 递归排序函数（简化）

```c
static void tqsort_helper(data_t *base, size_t nele, task_queue_ptr tq) {
    if (nele <= nele_max_sort_serial) {
        qsort_serial(base, nele);  // 小数组用顺序排序
        return;
    }
    size_t m = partition(base, nele);
    // spawn 两个子任务
    spawn_task(tq, tqsort_helper, base, m, tq);
    spawn_task(tq, tqsort_helper, base+m+1, nele-m-1, tq);
}
```

### 5.5 并行快速排序性能

- 使用任务队列（task queue）管理线程
- 相对于顺序版本，可获得接近线性的加速比（在合适的阈值 Nthresh 下）

### 5.6 并行划分（Parallel Partitioning）的尝试

- 尝试过并行化 partition 步骤（在划分时也并行）
- **实验结论**：无法获得加速比
- **推测原因**：数据拷贝开销过大（需要临时空间重新组装划分结果，无法在原地完成）

---

## 六、经验总结与教训

1. **必须有并行化策略**
   - 将问题分成 K 个独立部分（分区法）
   - 使用分治（divide-and-conquer）
2. **内层循环必须无同步**
   - 同步操作（锁、原子操作等）代价极高
3. **注意 Amdahl's Law**
   - 串行代码会成为瓶颈
   - 即使极小比例的串行部分，也会严重限制最大加速比
4. **你可以做到！**
   - 实现适度的并行加速并不难
   - 搭建实验框架，测试多种策略

---

## 七、内存一致性（Memory Consistency）

### 7.1 问题引入

```c
int a = 1, b = 100;

// Thread 1:          // Thread 2:
a = 2;      (Wa)     b = 200;    (Wb)
print(b);   (Rb)     print(a);   (Ra)
```

**可能的输出值是什么？** —— 这取决于**内存一致性模型**

### 7.2 顺序一致性（Sequential Consistency）

- **定义**：整体执行效果与某种所有线程操作的顺序交织（interleaving）一致，且每个线程内的操作顺序保持不变
- 每个线程内：Wa → Rb（Thread1），Wb → Ra（Thread2）

**可能的合法输出**：

| 执行顺序 | Thread1 输出 | Thread2 输出 |
|---------|-------------|-------------|
| Wa→Rb→Wb→Ra | 100 | 2 |
| Wa→Wb→Rb→Ra | 200 | 2 |
| Wb→Ra→Wa→Rb | 1 | 200 |
| Wb→Wa→Ra→Rb | 2 | 200 |
| Wa→Wb→Ra→Rb | 200 | 2 |
| Wb→Wa→Rb→Ra | 200 | 2 |

**不可能的输出**：`100, 1` 或 `1, 100`
- 这需要在 Wa 和 Wb 都执行前就读到 Ra 和 Rb，违反线程内顺序

### 7.3 非一致缓存场景（Non-Coherent Cache）

- 写回缓存（write-back cache）但**缓存之间没有协调**
- 结果：Thread1 的 `a=2` 存在 Thread1 的缓存中，但 Thread2 读 `a` 时仍从主存读到 `a=1`
- 这会导致 `print(a)=1, print(b)=100` 这种**在顺序一致性下不可能出现的结果**

### 7.4 Snoopy 缓存（缓存一致性协议）

每个缓存块打上状态标签：

| 状态 | 含义 |
|------|------|
| **Invalid** | 不可使用该值（已失效） |
| **Shared** | 可读的拷贝（可能多个缓存共有） |
| **Exclusive** | 可写的拷贝（只有一个缓存持有） |

**工作机制**：
- 当某个缓存看到其他缓存对自己 **Exclusive** 标记的块发出请求时：
  1. 从缓存（而非主存）提供最新值
  2. 将状态降级为 **Shared**

**效果**：保证所有核看到的是内存的一致视图，防止出现读到旧值的情况。

---

## 八、关键术语速查

| 术语 | 含义 |
|------|------|
| **Multicore** | 单芯片多核处理器 |
| **Hyperthreading** | 单核多线程（共享功能单元，复制寄存器） |
| **False Sharing** | 不同线程访问同一 cache line 的不同元素导致的性能问题 |
| **Amdahl's Law** | 加速比上限受串行部分比例限制：$S = 1/(s + (1-s)/p)$ |
| **Sequential Consistency** | 所有线程操作可等效为某种全局顺序交织的一致性模型 |
| **Snoopy Cache** | 通过监听总线请求维护缓存一致性的协议（MSI/MESI等） |
| **Task Queue** | 并行任务管理结构，用于动态分配和等待线程任务 |
| **Partition** | 快速排序中将数组按枢轴划分为两部分的操作 |

---

*笔记整理自 CMU 15-213 CS:APP 第26讲 PPT*
