# combine CPE 实验

本实验用 Python 的 `ctypes` 调用 `vec.c` 中的 `combine1`、`combine2`、`combine3`，对不同长度 `n` 的向量计时，并绘制每元素开销随 `n` 变化的曲线。

## 运行方式

```sh
python3 measure_combine_cpe.py
```

脚本会自动把 `vec.c` 编译成共享库，然后生成：

- `combine_cpe.csv`：原始测量数据
- `combine_cpe.png`：曲线图

默认以 `-O2 -DLONG` 编译。如果系统无法给出 CPU 频率，脚本会输出 `ns/element`；要换算 CPE，可以显式设置频率：

```sh
CPU_HZ=3200000000 python3 measure_combine_cpe.py
```

## 三个版本的差异

```c
void combine1(vec_ptr v, data_t *dest)
{
    long i;
    *dest = IDENT;
    for (i = 0; i < vec_length(v); i++) {
        data_t val;
        get_vec_element(v, i, &val);
        *dest = *dest OP val;
    }
}
```

`combine1` 每次循环都调用 `vec_length(v)`，循环边界重复求值。如果编译器不能证明 `vec_length` 没有副作用，或者不能安全内联，就不能随意把它移出循环。

```c
void combine2(vec_ptr v, data_t *dest)
{
    long i;
    long length = vec_length(v);
    *dest = IDENT;
    for (i = 0; i < length; i++) {
        data_t val;
        get_vec_element(v, i, &val);
        *dest = *dest OP val;
    }
}
```

`combine2` 把长度读取移到循环外，属于代码移动。它减少了循环内的过程调用，但仍然每个元素都通过 `get_vec_element` 做边界检查和间接写入。

```c
void combine3(vec_ptr v, data_t *dest)
{
    long i;
    long length = vec_length(v);
    data_t *data = get_vec_start(v);
    *dest = IDENT;
    for (i = 0; i < length; i++) {
        *dest = *dest OP data[i];
    }
}
```

`combine3` 直接取得底层数组指针，循环内不再调用 `get_vec_element`。它通常会得到最低 CPE，因为每轮迭代只保留必要的数组读取、加法和结果写回。

## 结论

随着 `n` 增大，固定测量开销被摊薄，曲线会更接近稳定值。一般趋势是：

```text
combine3 < combine2 < combine1
```

这个实验对应 CSAPP 第 5 章的三个局部优化点：

- 代码移动：把 `vec_length(v)` 移出循环。
- 减少过程调用：避免每轮迭代调用访问器函数。
- 消除不必要的工作：直接访问连续数组，让循环体更接近机器实际需要执行的操作。
