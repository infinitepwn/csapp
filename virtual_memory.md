### Information Is Bits + Context

信息就是比特+上下文

### Programs Are Translated by Other Programs into Different Forms

程序被其他程序翻译成不同的形式

虽然一个程序例如hello.c是由高级语言C编写的，但是为了运行这个文件，C语言必须被其他程序翻译成一系列低级的机器语言指令。

> These instructions are then packaged in a form called an executable object program and stored as a binary disk file. Object programs are also referred to as executable object files.

这些指令随后被打包成一种叫做**可执行目标程序**的形式，然后存储为一个二进制的磁盘文件，目标程序也被叫做**可执行目标文件**

![image-20260525171452710](/Users/infinite/Library/Application Support/typora-user-images/image-20260525171452710.png)

翻译的工作是由compiler driver(编译器驱动程序)完成的

```bash
gcc -o hello hello.c
```

##### Pre-processor阶段

cpp会根据开头为#的directives来修改原始的C程序，比如

#include<stdio.h>会告诉预处理器去读取系统头文件stdio.h并且直接插入到程序的文本当中，这样会生成一个.i文件

##### Complication阶段

cc1把hello.i翻译成hello.s,也就是汇编语言

汇编语言可以为不同的高级语言提供了通用的输出语言

##### Assembly阶段

as把hello.s翻译成机器语言指令，并且打包为一种叫做可重定位目标程序的形式，然后存储为目标文件hello.o。这个文件一个二进制文件.他包含了17个被编码为机器指令的字节，如果我们在text editor里面打开，则显示的是乱码

##### Linking阶段

hello.c调用了printf函数，他是C标准库里的函数，它存储在一个预先编译好的printf.o当中，然后由ld与hello.o合并，最后形成一个可执行目标文件hello

### 系统的硬件组成

![image-20260525175928030](/Users/infinite/Library/Application Support/typora-user-images/image-20260525175928030.png)

### Threads

虽然我们通常认为一个进程有一个单独的控制流，但实际上一个进程是由多个执行单元构成的，叫做线程



### Dynnamic Memory Allocation (动态内存分配)

While it is certainly possible to use the low-level mmap and munmap functions to create and delete areas of virtual memory, C programmers typically find it more convenient and more portable to use a dynamic memory allocator when they need to acquire additional virtual memory at run time.