"""C语言每日一题 — 程序阅读题，LLM生成为主 + 题库兜底。
指令: /每日一题 /再来一题 /答 /答案 /题解
"""
from __future__ import annotations

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from maibot_sdk import Command, Field, MaiBotPlugin, PluginConfigBase, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


PROBLEM_BANK: list[dict[str, str]] = [
    # ── 运算符优先级 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 5, b = 3;\n    printf(\"%d\", a + b * 2);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "11",
        "hint": "乘法优先级高于加法喵~",
        "explanation": "b * 2 = 6，然后 a + 6 = 11。乘法优先级高于加法，不是 (5+3)*2。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 10, y = 3;\n    printf(\"%d\", x / y * y + x % y);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "10",
        "hint": "整数除法会截断小数部分喵~",
        "explanation": "x/y=3（整数除法），3*3=9，x%y=10%3=1，9+1=10。其实就是带余除法恒等式：x = (x/y)*y + x%y。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 1, b = 2, c = 3;\n    printf(\"%d\", a < b < c);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "1",
        "hint": "C语言里 < 是从左往右结合的，结果不是你想的那样…但答案碰巧是1喵",
        "explanation": "a<b<c 等价于 (a<b)<c。a<b 为真=1，1<c=1<3 也为真=1。虽然碰巧对了，但这不是在判断 b 是否在 a 和 c 之间！正确写法是 a<b && b<c。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 1, b = 2, c = 3;\n    printf(\"%d\", a + b & c);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "3",
        "hint": "& 的优先级低于 + 喵~",
        "explanation": "+ 优先级高于 &，所以是 (a+b) & c = 3 & 3 = 3。注意 & 是位与，不是逻辑与 &&。",
        "source": "bank",
    },
    # ── 自增/自减 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int i = 5;\n    printf(\"%d\", i++ * i++);\n    return 0;\n}",
        "question": "这段代码是未定义行为，但大多数编译器（GCC/Clang）的输出是什么？（如不确定可答'未定义行为'）",
        "answer": "未定义行为",
        "hint": "同一表达式里多次修改同一个变量……",
        "explanation": "C标准规定，在两个序列点之间多次修改同一变量是未定义行为(UB)。不同编译器结果不同，考试中答案是「未定义行为」。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 3;\n    printf(\"%d %d\", ++a, a++);\n    return 0;\n}",
        "question": "这段代码的行为是什么？",
        "answer": "未定义行为",
        "hint": "函数参数的求值顺序是不确定的喵~",
        "explanation": "函数参数的求值顺序在C标准中是未指定的。printf的参数从右往左还是从左往右求值由编译器决定，且涉及对同一变量的多次修改，属未定义行为。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int i = 3;\n    int j = ++i + i++;\n    printf(\"%d\", j);\n    return 0;\n}",
        "question": "这段代码的行为是什么？",
        "answer": "未定义行为",
        "hint": "++i 和 i++ 之间没有序列点喵~",
        "explanation": "++i + i++ 在序列点之间两次修改 i，这是未定义行为。即使一些编译器输出某个值，也不应该依赖它。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int i = 5;\n    printf(\"%d, \", i++);\n    printf(\"%d\", i);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5, 6",
        "hint": "i++ 先用后加喵~",
        "explanation": "第一个 printf 输出 i 的值 5，然后 i 变为 6。第二个 printf 输出 6。所以是「5, 6」。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int i = 5;\n    printf(\"%d, \", ++i);\n    printf(\"%d\", i);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "6, 6",
        "hint": "++i 先加后用喵~",
        "explanation": "第一个 printf 先将 i 加到 6 再输出，第二个 printf 也是 6。所以是「6, 6」。",
        "source": "bank",
    },
    # ── 指针与数组 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int a[] = {10, 20, 30, 40, 50};\n    printf(\"%d\", *(a + 2));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "30",
        "hint": "a 是指向数组首元素的指针，+2 偏移两个元素喵~",
        "explanation": "a 等价于 &a[0]，a+2 指向 a[2]，*(a+2) 就是 a[2]=30。注意不是加两个字节，而是加两个 int 的大小。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a[] = {1, 2, 3, 4, 5};\n    int *p = a;\n    printf(\"%d\", *(p + 1) + *(a + 3));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "6",
        "hint": "p+1 指向 a[1]，a+3 指向 a[3]喵~",
        "explanation": "*(p+1) = a[1] = 2，*(a+3) = a[3] = 4，2+4 = 6。p 和 a 指向同一个数组。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    char s[] = \"hello\";\n    printf(\"%d\", sizeof(s));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "6",
        "hint": "sizeof 数组会算上结尾的 '\\0' 喵~",
        "explanation": "s 是 char 数组（不是指针），\"hello\" 在内存中是 h,e,l,l,o,\\0 共6个字节。sizeof(s) = 6。如果 s 是指针 char*，sizeof 会是指针大小(4或8)。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int arr[5] = {0};\n    printf(\"%d\", arr[3]);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "0",
        "hint": "{0} 会把整个数组初始化为0喵~",
        "explanation": "C语言中，{0} 初始化数组会把所有元素置为0（未显式指定的元素会被零初始化）。所以 arr[3]=0。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a[3] = {1, 2, 3};\n    printf(\"%d\", 2[a]);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "3",
        "hint": "a[b] 等价于 *(a+b)，2[a] 合法且等价于 a[2] 喵~",
        "explanation": "C语言中 a[b] 展开为 *(a+b)。2[a] 展开为 *(2+a)，和 *(a+2) 完全一样，等于 a[2]=3。虽然能编译，但别这么写！",
        "source": "bank",
    },
    # ── 位运算 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", 5 & 3);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "1",
        "hint": "5=101b, 3=011b，按位与喵~",
        "explanation": "5 的二进制是 101，3 的二进制是 011。按位与：101 & 011 = 001 = 1。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", 5 | 3);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "7",
        "hint": "5=101b, 3=011b，按位或喵~",
        "explanation": "5(101) | 3(011) = 111 = 7。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", 5 ^ 3);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "6",
        "hint": "5=101b, 3=011b，按位异或喵~",
        "explanation": "5(101) ^ 3(011) = 110 = 6。异或：相同得0，不同得1。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", ~5);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "-6",
        "hint": "~ 是按位取反，包括符号位喵~（假设32位int）",
        "explanation": "5 的32位二进制: 000...0101。取反: 111...1010。这是补码表示的 -6。公式: ~x = -x - 1，所以 ~5 = -6。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 8;\n    printf(\"%d\", x >> 1);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "4",
        "hint": "右移一位相当于除以2喵~",
        "explanation": "8 的二进制是 1000，右移一位得 0100 = 4。正数右移等价于除以2。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 1;\n    printf(\"%d\", x << 3);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "8",
        "hint": "左移三位相当于乘以2^3喵~",
        "explanation": "1 << 3 = 1 * 2³ = 8。左移n位等于乘以2的n次方。",
        "source": "bank",
    },
    # ── 逻辑短路 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 0, b = 5;\n    if (a && b++) {}\n    printf(\"%d\", b);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5",
        "hint": "&& 短路求值：左边为假就不算右边了喵~",
        "explanation": "a=0 为假，&& 短路，b++ 不会执行。所以 b 还是 5。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 1, b = 5;\n    if (a || b++) {}\n    printf(\"%d\", b);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5",
        "hint": "|| 短路求值：左边为真就不算右边了喵~",
        "explanation": "a=1 为真，|| 短路，b++ 不会执行。b 保持 5。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 5;\n    printf(\"%d\", !x);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "0",
        "hint": "! 是逻辑非，非零值都是真，!真=假=0喵~",
        "explanation": "x=5 非零，在逻辑运算中为真。!5 = 0（假）。只有 !0 才等于 1。",
        "source": "bank",
    },
    # ── 逗号运算符 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int a;\n    a = (3, 5, 8);\n    printf(\"%d\", a);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "8",
        "hint": "逗号运算符：从左到右依次求值，返回最右边的值喵~",
        "explanation": "逗号运算符依次计算 3（丢弃）、5（丢弃）、8，最终返回 8。所以 a=8。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 1, y = 2;\n    printf(\"%d\", (x++, y++, x + y));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5",
        "hint": "逗号运算符依次执行，x变成2，y变成3喵~",
        "explanation": "逗号运算符依次执行 x++（x变为2）、y++（y变为3），然后求值 x+y=2+3=5。返回5。",
        "source": "bank",
    },
    # ── switch 穿透 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 2;\n    switch (x) {\n        case 1: printf(\"A\");\n        case 2: printf(\"B\");\n        case 3: printf(\"C\");\n        default: printf(\"D\");\n    }\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "BCD",
        "hint": "switch 没有 break 会穿透喵~",
        "explanation": "x=2，从 case 2 开始执行，输出 B，因为没有 break，继续输出 C，再输出 D。最终输出 BCD。经典的 fall-through。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int x = 5;\n    switch (x) {\n        case 1: printf(\"A\"); break;\n        case 3: printf(\"B\"); break;\n        default: printf(\"C\");\n    }\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "C",
        "hint": "x=5 没有匹配的 case，走 default 喵~",
        "explanation": "x=5 不匹配 case 1 和 case 3，执行 default 分支，输出 C。default 可以放在任意位置。",
        "source": "bank",
    },
    # ── 类型转换 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", (int)3.9);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "3",
        "hint": "强制类型转换是截断，不是四舍五入喵~",
        "explanation": "(int)3.9 把 3.9 的小数部分截断，得到 3。不是四舍五入！",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    char c = 65;\n    printf(\"%c\", c);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "A",
        "hint": "ASCII 码 65 对应字符 'A' 喵~",
        "explanation": "char c=65 将整数 65 赋值给字符变量，ASCII码中 65='A'。用 %c 输出字符，所以是 A。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", 'A' + 1);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "66",
        "hint": "字符在运算中会被提升为 int 喵~",
        "explanation": "'A' 的 ASCII 码是 65，'A'+1=66。用 %d 输出整数，所以是 66。如果用 %c 就是 'B'。",
        "source": "bank",
    },
    # ── 静态变量 ──
    {
        "code": "#include <stdio.h>\nvoid f() {\n    static int n = 0;\n    n++;\n    printf(\"%d\", n);\n}\nint main() {\n    f(); f(); f();\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "123",
        "hint": "static 变量只初始化一次，值在函数调用之间保留喵~",
        "explanation": "第一次调用 f()：n 从 0 变为 1，输出 1。第二次：n 从 1 变为 2，输出 2。第三次：n 从 2 变为 3，输出 3。连续输出 123。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint g() {\n    static int x = 10;\n    return x--;\n}\nint main() {\n    printf(\"%d\", g());\n    printf(\"%d\", g());\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "109",
        "hint": "static 变量在调用之间保留值，x-- 先用后减喵~",
        "explanation": "第一次 g()：返回 x 的值 10，然后 x 变为 9。输出 10。第二次 g()：返回 x 的值 9，然后 x 变为 8。输出 9。最终输出「109」。",
        "source": "bank",
    },
    # ── 宏 ──
    {
        "code": "#include <stdio.h>\n#define SQUARE(x) x * x\nint main() {\n    printf(\"%d\", SQUARE(1 + 2));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5",
        "hint": "宏只是文本替换，展开后是 1+2*1+2 喵~",
        "explanation": "SQUARE(1+2) 展开为 1+2*1+2 = 1+2+2 = 5，不是 9！宏是纯文本替换。正确写法：#define SQUARE(x) ((x)*(x))。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\n#define MAX(a,b) a > b ? a : b\nint main() {\n    printf(\"%d\", 2 * MAX(3, 4));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "3",
        "hint": "宏展开后是 2*3>4?3:4，乘法优先级最高喵~",
        "explanation": "2*MAX(3,4) 展开为 2*3>4?3:4。C语言优先级：乘(*)>大于(>)>条件(?:)。所以 (2*3)>4?3:4 → 6>4?3:4 → 真?3:4 → 3。正确写法：#define MAX(a,b) ((a)>(b)?(a):(b))。",
        "source": "bank",
    },
    # ── printf 返回值 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    printf(\"%d\", printf(\"hello\"));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "hello5",
        "hint": "printf 的返回值是输出的字符数喵~",
        "explanation": "内层 printf(\"hello\") 先执行，输出 \"hello\" 并返回 5。外层 printf(\"%d\",5) 输出 \"5\"。最终输出 \"hello5\"。",
        "source": "bank",
    },
    # ── 循环 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int s = 0;\n    for (int i = 0; i < 5; i++) {\n        if (i == 3) continue;\n        s += i;\n    }\n    printf(\"%d\", s);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "7",
        "hint": "continue 跳过 i=3 的那一次，其他都加了喵~",
        "explanation": "i=0,1,2,4 时执行 s+=i。s=0+1+2+4=7。i=3 时 continue 跳过了。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int s = 0;\n    for (int i = 0; i < 5; i++) {\n        if (i == 3) break;\n        s += i;\n    }\n    printf(\"%d\", s);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "3",
        "hint": "break 直接跳出循环，i=3 及之后都不执行了喵~",
        "explanation": "i=0,1,2 时执行 s+=i，s=0+1+2=3。i=3 时 break 跳出循环。输出 3。",
        "source": "bank",
    },
    # ── 递归 ──
    {
        "code": "#include <stdio.h>\nint f(int n) {\n    if (n <= 1) return 1;\n    return n * f(n - 1);\n}\nint main() {\n    printf(\"%d\", f(4));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "24",
        "hint": "这是阶乘函数喵~ f(4)=4*3*2*1",
        "explanation": "f(4) = 4 * f(3) = 4 * 3 * f(2) = 4 * 3 * 2 * f(1) = 4 * 3 * 2 * 1 = 24。递归实现的阶乘。",
        "source": "bank",
    },
    # ── 字符串 ──
    {
        "code": "#include <stdio.h>\n#include <string.h>\nint main() {\n    printf(\"%d\", strlen(\"hello\\0world\"));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "5",
        "hint": "strlen 遇到 '\\0' 就停了喵~",
        "explanation": "字符串中间的 \\0 是空字符，strlen 在此处停止计数。\"hello\" 长度是 5，后面的 \"world\" 不会被计数。",
        "source": "bank",
    },
    # ── 结构体对齐 ──
    {
        "code": "#include <stdio.h>\nstruct S {\n    char a;\n    int b;\n    char c;\n};\nint main() {\n    printf(\"%d\", (int)sizeof(struct S));\n    return 0;\n}",
        "question": "这段代码在 32 位系统上通常输出什么？（提示：考虑内存对齐）",
        "answer": "12",
        "hint": "int 需要 4 字节对齐，所以 char a 后面有 3 字节填充喵~",
        "explanation": "char(1B) + 填充(3B) + int(4B) + char(1B) + 填充(3B) = 12 字节。内存对齐导致实际大小比成员之和(1+4+1=6)大。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int *p;\n    printf(\"%d\", (int)sizeof(p));\n    return 0;\n}",
        "question": "这段代码在 64 位系统上输出什么？",
        "answer": "8",
        "hint": "指针的大小取决于系统位数喵~",
        "explanation": "64位系统上指针占 8 字节，32位系统上占 4 字节。sizeof(指针) 和它指向什么类型无关。",
        "source": "bank",
    },
    # ── 综合 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    unsigned int x = 3;\n    printf(\"%d\", x - 5);\n    return 0;\n}",
        "question": "这段代码的输出是什么？（用 %d 输出无符号数）",
        "answer": "-2",
        "hint": "虽然 x 是 unsigned，但 %d 把它当作 signed 解释喵~",
        "explanation": "x-5 = 3-5，在 unsigned 运算中产生回绕，但用 %d 输出时按有符号整数解释。在32位系统上，3-5 的位模式恰好对应 -2 的补码，所以输出 -2。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 0;\n    printf(\"%d %d %d\", a, a++, ++a);\n    return 0;\n}",
        "question": "这段代码的行为是什么？",
        "answer": "未定义行为",
        "hint": "函数参数求值顺序未指定，且对同一变量多次修改喵~",
        "explanation": "printf 中三个参数都涉及 a，其中 a++ 和 ++a 修改了 a。参数求值顺序是未指定的，同时多次修改同一变量属未定义行为。不要写这种代码！",
        "source": "bank",
    },
    # ── 补充: 内存管理 ──
    {
        "code": "#include <stdio.h>\n#include <stdlib.h>\nint main() {\n    int *p = (int*)malloc(sizeof(int) * 3);\n    p[0] = 10; p[1] = 20; p[2] = 30;\n    p++;\n    printf(\"%d\", *p);\n    free(p - 1);\n    return 0;\n}",
        "question": "这段代码中 printf 输出什么？",
        "answer": "20",
        "hint": "p++ 让指针指向第二个元素，free 时必须传回原始地址喵~",
        "explanation": "malloc 分配 3 个 int，p 指向首地址。p++ 后 p 指向 p[1]=20，输出 20。free(p-1) 正确释放了原始地址。",
        "source": "bank",
    },
    {
        "code": "#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\nint main() {\n    char *s = (char*)malloc(6);\n    strcpy(s, \"hello\");\n    printf(\"%d\", (int)strlen(s));\n    free(s);\n    printf(\"%d\", (int)strlen(s));\n    return 0;\n}",
        "question": "这段代码有什么问题？",
        "answer": "使用已释放内存",
        "hint": "free 之后指针变成悬空指针，再使用是未定义行为喵~",
        "explanation": "free(s) 之后，s 指向的内存已被回收。第二次 strlen(s) 访问已释放的内存，属于 use-after-free，是严重的未定义行为。实际运行时可能崩溃也可能输出随机值。",
        "source": "bank",
    },
    # ── 补充: 函数指针 ──
    {
        "code": "#include <stdio.h>\nint add(int a, int b) { return a + b; }\nint sub(int a, int b) { return a - b; }\nint main() {\n    int (*op)(int, int);\n    op = add;\n    printf(\"%d \", op(3, 4));\n    op = sub;\n    printf(\"%d\", op(3, 4));\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "7 -1",
        "hint": "函数指针指向不同函数时，行为也跟着变喵~",
        "explanation": "op 先指向 add，op(3,4)=7；再指向 sub，op(3,4)=-1。所以输出「7 -1」。函数指针可以动态切换被调用的函数。",
        "source": "bank",
    },
    # ── 补充: 浮点陷阱 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    float f = 0.1 + 0.2;\n    printf(\"%d\", f == 0.3);\n    return 0;\n}",
        "question": "这段代码在绝大多数平台上输出什么？",
        "answer": "0",
        "hint": "浮点数不能精确表示 0.1 和 0.2 喵~",
        "explanation": "0.1 和 0.2 在二进制浮点中都是无限循环小数，它们的和并不精确等于 0.3。所以 f == 0.3 通常为假，输出 0。比较浮点数应使用 fabs(a-b)<epsilon 的方式。",
        "source": "bank",
    },
    # ── 补充: 大小端 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    union { int i; char c[4]; } u;\n    u.i = 0x01020304;\n    printf(\"%02x\", (unsigned char)u.c[0]);\n    return 0;\n}",
        "question": "在小端序（x86）系统上，这段代码输出什么？",
        "answer": "04",
        "hint": "小端序：低位字节在低地址喵~",
        "explanation": "0x01020304 在内存中：小端序低位在前，c[0] 存储最低字节 0x04。大端序则输出 01。这是检测系统字节序的经典方法。",
        "source": "bank",
    },
    # ── 补充: 枚举 ──
    {
        "code": "#include <stdio.h>\nenum Color { RED = 1, GREEN, BLUE = 5, YELLOW };\nint main() {\n    printf(\"%d %d\", GREEN, YELLOW);\n    return 0;\n}",
        "question": "这段代码的输出是什么？",
        "answer": "2 6",
        "hint": "枚举值默认从0开始递增，显式赋值后从该值继续递增喵~",
        "explanation": "RED=1，GREEN 自动为 2。BLUE=5，YELLOW 自动为 6。枚举可以跳值，没有赋值的成员 = 前一个成员的值 + 1。",
        "source": "bank",
    },
    # ── 补充: 链式赋值 ──
    {
        "code": "#include <stdio.h>\nint main() {\n    int a = 5;\n    printf(\"%d\", a -= a -= a);\n    return 0;\n}",
        "question": "这段代码的行为是什么？",
        "answer": "未定义行为",
        "hint": "序列点之间多次修改同一变量喵~",
        "explanation": "a -= a -= a 在一个表达式中两次修改 a，中间没有序列点。这是未定义行为。不要这样写代码！任何链式修改同一变量的赋值都是 UB。",
        "source": "bank",
    },
]


LLM_GENERATE_PROMPT = """你是C语言助教。生成一道C语言程序阅读题（给代码段猜输出），参考 LeetCode/牛客网/PTA 风格。

要求:
- 代码 6~25 行，必须包含 #include 和 main
- 聚焦一个知识点：运算符优先级、指针、位运算、static、宏、sizeof、类型转换、内存管理、递归、结构体对齐、未定义行为等
- 答案必须包含陷阱/反直觉的点，不是简单的加减乘除
- 覆盖不同知识点，不要重复常见的那些（i++/++i、&&短路、逗号运算符、switch穿透这些太常见了，换别的）

返回严格的JSON格式（不要markdown代码块包裹）:
{"code": "完整C代码", "question": "一句话问题", "answer": "正确答案", "hint": "简短提示(≤20字)", "explanation": "详细解析(≤200字)"}"""


class PluginConfig(PluginConfigBase):
    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=True, description="是否启用插件")
    config_version: str = Field(default="2.0.0", description="配置版本")


class DailyProblemConfig(PluginConfigBase):
    __ui_label__ = "编程一题"
    __ui_icon__ = "code"
    __ui_order__ = 1

    enabled: bool = Field(default=True, description="是否启用")
    reveal_on_wrong: bool = Field(default=False, description="答错后是否立即揭示正确答案")
    llm_first: bool = Field(default=True, description="优先用LLM生成题目（关闭则纯题库）")


class DailyProblemPluginConfig(PluginConfigBase):
    plugin: PluginConfig = Field(default_factory=PluginConfig)
    daily_problem: DailyProblemConfig = Field(default_factory=DailyProblemConfig)


def _normalize_answer(a: str) -> str:
    a = a.strip().rstrip("。，.!！?？")
    if (a.startswith("'") and a.endswith("'")) or (a.startswith('"') and a.endswith('"')):
        a = a[1:-1]
    a = re.sub(r"\s*,\s*", ", ", a)
    a = re.sub(r"\s+", " ", a).strip()
    return a


class DailyProblemPlugin(MaiBotPlugin):
    config_model = DailyProblemPluginConfig

    def __init__(self) -> None:
        super().__init__()
        self._state: dict[str, dict] = {}
        self._data_file = Path(__file__).parent / "daily_state.json"

    async def on_load(self) -> None:
        await self._load_state()

    async def on_unload(self) -> None:
        await self._save_state()

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    async def _load_state(self) -> None:
        try:
            if self._data_file.exists():
                self._state = await asyncio.to_thread(
                    lambda: json.loads(self._data_file.read_text("utf-8"))
                )
        except Exception:
            self._state = {}

    async def _save_state(self) -> None:
        try:
            data = json.dumps(self._state, ensure_ascii=False, indent=2)
            await asyncio.to_thread(self._data_file.write_text, data, "utf-8")
        except Exception:
            pass

    @staticmethod
    def _extract_user_id(kwargs: dict) -> str:
        for key in ("user_id", "sender_id", "qq"):
            if key in kwargs and kwargs[key]:
                return str(kwargs[key])
        return ""

    def _today_key(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    # ── 题目选取 ──

    def _get_or_init_group_state(self, stream_id: str) -> dict:
        if stream_id not in self._state:
            self._state[stream_id] = {"shown_indices": [], "current_problem": None, "answered_by": []}
        gs = self._state[stream_id]
        gs.setdefault("shown_indices", [])
        gs.setdefault("current_problem", None)
        gs.setdefault("answered_by", [])
        return gs

    def _pick_bank_problem(self, stream_id: str) -> dict[str, str]:
        gs = self._get_or_init_group_state(stream_id)
        shown = set(gs["shown_indices"])
        available = [i for i in range(len(PROBLEM_BANK)) if i not in shown]
        if not available:
            shown.clear()
            gs["shown_indices"] = []
            available = list(range(len(PROBLEM_BANK)))

        idx = random.choice(available)
        gs["shown_indices"].append(idx)
        problem = dict(PROBLEM_BANK[idx])
        problem["_source"] = "bank"
        return problem

    async def _llm_generate_problem(self) -> dict[str, str] | None:
        try:
            result = await self.ctx.llm.generate(
                prompt=LLM_GENERATE_PROMPT,
                request_type="plugin.daily_problem.generate",
                max_tokens=1024,
                temperature=0.9,
            )
        except Exception:
            self.ctx.logger.debug("LLM 生成题目失败", exc_info=True)
            return None

        if not isinstance(result, dict) or not result.get("success"):
            return None

        raw = str(result.get("response") or result.get("content") or "").strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

        try:
            problem = json.loads(raw)
        except json.JSONDecodeError:
            self.ctx.logger.debug("LLM 返回非JSON，尝试修复: %s", raw[:100])
            return None

        required = ("code", "question", "answer", "explanation")
        if not all(k in problem for k in required):
            return None

        problem.setdefault("hint", "")
        problem["source"] = "llm"
        problem["_source"] = "llm"
        return dict(problem)

    async def _get_problem(self, stream_id: str) -> dict[str, str]:
        if self.config.daily_problem.llm_first:
            generated = await self._llm_generate_problem()
            if generated:
                gs = self._get_or_init_group_state(stream_id)
                gs["current_problem"] = generated
                await self._save_state()
                return generated

        problem = self._pick_bank_problem(stream_id)
        gs = self._get_or_init_group_state(stream_id)
        gs["current_problem"] = problem
        await self._save_state()
        return problem

    async def _get_current_problem(self, stream_id: str) -> dict[str, str]:
        gs = self._get_or_init_group_state(stream_id)
        cached = gs.get("current_problem")
        if cached and isinstance(cached, dict):
            cached["_source"] = cached.get("source", "cache")
            return cached
        return await self._get_problem(stream_id)

    # ── QQ安全处理 ──

    @staticmethod
    def _sanitize_qq_text(text: str) -> str:
        return text.replace("<", "＜").replace(">", "＞")

    def _format_problem_msg(self, problem: dict, show_answer: bool = False) -> str:
        source_tag = {"bank": " 📚题库", "llm": " 🤖AI生成", "cache": ""}.get(problem.get("source", ""), "")
        parts = [
            f"📝 编程一题 | 📅 {self._today_key()}{source_tag}",
            f"❓ {problem['question']}",
            "",
            problem["code"].strip(),
        ]
        if show_answer:
            parts.append(f"✅ 答案：{problem['answer']}")
            parts.append(f"📖 解析：{problem['explanation']}")
        else:
            parts.append("💡 /答 <答案> 提交 | /答案 揭晓 | /题解 解析 | /再来一题")
        return self._sanitize_qq_text("\n".join(parts))

    # ── 命令 ──

    @Command("daily_problem", description="编程一题 — C语言程序阅读题，LLM生成+题库", pattern=r"(?:^|\s)[/!]每日一题\s*$")
    async def handle_daily_problem(self, stream_id: str = "", **kwargs: Any):
        problem = await self._get_problem(stream_id)
        msg = self._format_problem_msg(problem)
        await self.ctx.send.text(msg, stream_id)
        return True, "题目已发送", True

    @Command("next_problem", description="再来一道编程题", pattern=r"(?:^|\s)[/!]再来一题\s*$")
    async def handle_next_problem(self, stream_id: str = "", **kwargs: Any):
        problem = await self._get_problem(stream_id)
        msg = self._format_problem_msg(problem)
        await self.ctx.send.text(msg, stream_id)
        return True, "新题目已发送", True

    @Command("submit_answer", description="提交答案: /答 <你的答案>", pattern=r"(?:^|\s)[/!]答\s+(?P<answer>.+?)\s*$")
    async def handle_submit_answer(self, stream_id: str = "", **kwargs: Any):
        matched = kwargs.get("matched_groups", {})
        raw_answer = str(matched.get("answer") or "").strip()
        if not raw_answer:
            await self.ctx.send.text(self._sanitize_qq_text("用法：/答 <你的答案>   比如 /答 42"), stream_id)
            return True, "答案为空", True

        user_id = self._extract_user_id(kwargs)
        problem = await self._get_current_problem(stream_id)

        expected = _normalize_answer(problem["answer"])
        given = _normalize_answer(raw_answer)
        name_tag = f"@{user_id} " if user_id else ""

        if given == expected.lower() or given == expected:
            msg = f"{name_tag}✅ 完全正确！\n\n📖 解析：{problem['explanation']}"
            gs = self._get_or_init_group_state(stream_id)
            answered = gs.get("answered_by", [])
            if user_id and user_id not in answered:
                answered.append(user_id)
                gs["answered_by"] = answered
                await self._save_state()
        else:
            msg = f"{name_tag}❌ 不对喵~"
            if problem.get("hint"):
                msg += f"\n💡 提示：{problem['hint']}"
            if self.config.daily_problem.reveal_on_wrong:
                msg += f"\n\n✅ 正确答案：{problem['answer']}\n📖 解析：{problem['explanation']}"

        await self.ctx.send.text(self._sanitize_qq_text(msg), stream_id)
        return True, f"答案提交: {raw_answer}", True

    @Command("reveal_answer", description="查看正确答案和解析", pattern=r"(?:^|\s)[/!]答案\s*$")
    async def handle_reveal_answer(self, stream_id: str = "", **kwargs: Any):
        problem = await self._get_current_problem(stream_id)
        msg = self._format_problem_msg(problem, show_answer=True)
        await self.ctx.send.text(msg, stream_id)
        return True, "答案已揭示", True

    @Command("explanation", description="查看详细解析", pattern=r"(?:^|\s)[/!]题解\s*$")
    async def handle_explanation(self, stream_id: str = "", **kwargs: Any):
        problem = await self._get_current_problem(stream_id)
        msg = (
            f"📖 编程一题题解 ({self._today_key()})\n{'─' * 20}\n\n"
            f"❓ {problem['question']}\n\n{problem['code']}\n\n{'─' * 20}\n"
            f"✅ 答案：{problem['answer']}\n\n📖 解析：{problem['explanation']}"
        )
        await self.ctx.send.text(self._sanitize_qq_text(msg), stream_id)
        return True, "题解已发送", True

    # ── LLM Tool ──

    @Tool(
        "get_daily_c_problem",
        description="获取C语言程序阅读题（给代码猜输出）。用户说'每日一题''做题''来道C语言题'时调用。LLM生成或题库抽取。",
        parameters=[],
    )
    async def handle_tool(self, **kwargs: Any):
        del kwargs
        if self.config.daily_problem.llm_first:
            problem = await self._llm_generate_problem()
            if problem is None:
                idx = random.randint(0, len(PROBLEM_BANK) - 1)
                problem = dict(PROBLEM_BANK[idx])
                problem["_source"] = "bank"
        else:
            idx = random.randint(0, len(PROBLEM_BANK) - 1)
            problem = dict(PROBLEM_BANK[idx])
            problem["_source"] = "bank"

        source_label = "🤖AI生成" if problem.get("_source") == "llm" else "📚题库"
        return {
            "name": "get_daily_c_problem",
            "content": self._sanitize_qq_text(
                f"📝 C语言阅读题 ({self._today_key()} {source_label})\n"
                f"❓ {problem['question']}\n\n{problem['code']}\n\n"
                f"（用户用 /答 <答案> 提交，用 /答案 查看正确答案。"
                f"答案：{problem['answer']}。解析：{problem['explanation']}）"
            ),
        }


def create_plugin() -> DailyProblemPlugin:
    return DailyProblemPlugin()
