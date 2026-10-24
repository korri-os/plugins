;; Original Korri native runner fixture. SPDX-License-Identifier: CC0-1.0
(module
 (import "env" "memory" (memory 1 1))
 (import "env" "diskr" (func $diskr (param i32 i32) (result i32)))
 (import "env" "diskw" (func $diskw (param i32 i32) (result i32)))
 (import "env" "rect" (func $rect (param i32 i32 i32 i32)))
 (func (export "start")
  (drop (call $diskr (i32.const 1024) (i32.const 8)))
  (i32.store (i32.const 1024) (i32.add (i32.load (i32.const 1024)) (i32.const 1)))
  (drop (call $diskw (i32.const 1024) (i32.const 8))))
 (func (export "update")
  (if (i32.and (i32.load8_u (i32.const 22)) (i32.const 64))
   (then
    (i32.store (i32.const 1028) (i32.const 42))
    (drop (call $diskw (i32.const 1024) (i32.const 8)))))
  (i32.store16 (i32.const 20) (i32.const 3))
  (call $rect (i32.const 20) (i32.const 20) (i32.const 100) (i32.const 100))))
