For example:

编写一个 MBR 引导程序：
```scheme
; 其它代码
(to^ 510)
(set^ magic-number
  [asm
    [db 0x55 0xaa]])
```

定义一个转换器：
```scheme
(define-syntax! (with)              ; 辅助关键字表
                (call f with e ...) ; 抓取
                (f e ...))          ; 转换
(call set^ with (_ ($+ 1 1)))       ; -> (set^ _ 2)
```

Laxer 和 Parser 在一个 Pass 内，宏展开器独立一个 Pass ，编译器一个 Pass 。
