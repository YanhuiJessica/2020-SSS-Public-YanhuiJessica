# 符号执行

## 实验要求

- [x] 安装 KLEE，完成官方 Tutorials

## 实验环境

### ACKali

- Kali Linux

## 安装 KLEE

```bash
# 启动 docker
systemctl start docker

# 安装 KLEE
docker pull klee/klee:2.0

# 启动，在容器中使用 KLEE
# 创建一个临时容器，退出后自动删除
docker run --rm -ti --ulimit='stack=-1:-1' klee/klee:2.0

# 创建一个长期容器并命名
docker run -ti --name=klee_container --ulimit='stack=-1:-1' klee/klee
# 退出后可通过名字再次进入
docker start -ai klee_container
# 删除长期容器
docker rm klee_container
```

## Tutorial 1 - Testing a Small Function

- 需要测试的函数为`get_sign`
    ```c
    int get_sign(int x) {
    if (x == 0) return 0;
    if (x < 0) return -1;
    else return 1;
    }
    ```
- 为了使用 KLEE 来测试`get_sign`函数，需要通过`klee_make_symbolic()`函数将变量标记为符号，主函数如下：
    ```c
    int main() {
    int a;
    // 需要头文件 klee/klee.h
    klee_make_symbolic(&a, sizeof(a), "a");
    return get_sign(a);
    }
    ```
- 启动 KLEE 容器，`get_sign.c`文件位于`/home/klee/klee_src/examples/get_sign`目录下（容器下没有`vim`，需要自己装，~~吃鲸~~）
- KLEE 操作基于 LLVM bitcode，将 C 语言文件编译转化为 LLVM bitcode：`clang -I ../../include -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone get_sign.c`
  - 使用`-I`参数让编译器能找到头文件`klee/klee.h`
  - 使用`-g`向 bitcode 文件添加调试信息
  - `-O0 -Xclang -disable-O0-optnone`只允许 KLEE 自己的优化
- 基于 bitcode 文件执行 KLEE：`klee get_sign.bc`
![输出结果](img/get_sign_out.jpg)<br>
  - `get_sign`函数有三条完整路径，a 等于 0、a 大于 0 和 a 小于 0
  - KLEE 为每条路径生成了一个测试
  - KLEE 执行后的输出结果在`klee-out-0`文件夹中，包括 KLEE 生成的测试（`klee-last`为指向`klee-out-0`的软链接文件夹，一般创建时指向最近创建的文件）
![文件夹内容](img/klee-out-sign.jpg)
- 测试文件为二进制文件，可通过`ktest-tool`查看
![查看、输出结果](img/ktest-tool.jpg)<br>
- 使用测试用例运行程序，查看输出结果
  ```bash
  # 设置除默认路径外查找动态链接库的路径
  export LD_LIBRARY_PATH=~/klee_build/lib/:$LD_LIBRARY_PATH

  # 将程序与 libkleeRuntest 库链接
  gcc -I ../../include -L /home/klee/klee_build/lib/ get_sign.c -lkleeRuntest

  # 设置 KTEST_FILE 的值指向期望的测试用例的文件名
  KTEST_FILE=klee-last/test000001.ktest ./a.out

  KTEST_FILE=klee-last/test000002.ktest ./a.out

  KTEST_FILE=klee-last/test000003.ktest ./a.out

  # 每次执行后查看返回值
  echo $?
  ```
  ![返回结果](img/tutorial-1-result.jpg)
  - `-1`已转换为 0-255 范围内有效的退出状态码

## Tutorial 2 - Testing a Simple Regular Expression Library

- 示例代码`Regexp.c`位于`/home/klee/klee_src/examples/regexp`目录下
- 将 C 语言文件编译转化为 LLVM bitcode：`clang -I ../../include -emit-llvm -c -g -O0 -Xclang -disable-O0-optnone Regexp.c`
  - `-c`：将代码编译为对象文件，而非原生可执行程序
- 使用 KLEE 运行代码：`klee --only-output-states-covering-new Regexp.bc`
![执行结果](img/klee-out-reg.jpg)
- 如果 KLEE 在程序执行时发现了错误，就会生成能触发错误的测试用例，并将关于错误的附加信息写入文件`testN.TYPE.err`（`N`是测试样例编号，`TYPE`指明错误类型）

  Type | Descriptiond
  -|-
  ptr|Stores or loads of invalid memory locations
  free|Double or invalid free()
  abort|The program called abort()
  assert|An assertion failed
  div|A division or modulus by zero was detected
  user|There is a problem with the input (invalid klee intrinsic calls) or the way KLEE is being used
  exec|There was a problem which prevented KLEE from executing the program; for example an unknown instruction, a call to an invalid function pointer, or inline assembly
  model|KLEE was unable to keep full precision and is only exploring parts of the program state. For example, symbolic sizes to malloc are not currently supported, in such cases KLEE will concretize the argument
- 从上面的结果可以看到，KLEE 检测出了两个内存错误，用`cat`查看其中一个的内容：<br>
![错误信息分析](img/ptr-err.jpg)
- KLEE 发现这个错误并不是因为正则表达式的函数有 BUG，而是指出测试驱动程序存在问题。我们使输入正则表达式缓冲区完全符号化，而匹配函数期望它是以`\0`结尾的字符串
- 使缓冲区符号化只是将内容初始化为引用符号变量，我们仍可以修改内存，最简单的解决方法是在符号化后在缓冲区末尾添加`\0`，修改后：
  ```c
  int main() {
    // The input regular expression.
    char re[SIZE];

    // Make the input symbolic.
    klee_make_symbolic(re, sizeof re, "re");
    re[SIZE - 1] = '\0';

    // Try to match against a constant string "hello".
    match(re, "hello");

    return 0;
  }
  ```
  ![没有再出现报错信息](img/no-ptr-err.jpg)
- 使用`klee_assume`内置函数可以达到同样的效果（但更灵活），`klee_assume`接受一个无符号整数的参数，通常是某种条件表达式，并且假设该表达式在当前路径上为真（如果这种情况永远不会发生，KLEE 将报错）。使用`klee_assume`使 KLEE 只探索以`\0`结尾的字符串：
  ```c
  int main() {
    // The input regular expression.
    char re[SIZE];

    // Make the input symbolic.
    klee_make_symbolic(re, sizeof re, "re");
    klee_assume(re[SIZE - 1] == '\0');

    // Try to match against a constant string "hello".
    match(re, "hello");

    return 0;
  }
  ```
- 注意：在对多个条件语句使用`klee_assume`时，类似`&&`和`||`布尔条件句可能会被编译成计算表达式结果之前的分支代码，这种情况下 KLEE 可能将在调用`klee_assume`之前岔开进程，探索不必要的状态。尽可能使用简单的表达式，并使用`&`和`|`运算符

## 参考资料

- [Tutorials · KLEE](https://klee.github.io/tutorials/)