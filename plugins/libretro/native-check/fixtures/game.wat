;; Original Korri native runner fixture. SPDX-License-Identifier: CC0-1.0
(module
 (import "env" "memory" (memory 1 1))
 (import "env" "diskr" (func $diskr (param i32 i32) (result i32)))
 (import "env" "diskw" (func $diskw (param i32 i32) (result i32)))
 (import "env" "rect" (func $rect (param i32 i32 i32 i32)))
 (func (export "start")
  (drop (call $diskr (i32.const 1024) (i32.const 4)))
  (i32.store (i32.const 1024) (i32.add (i32.load (i32.const 1024)) (i32.const 1)))
  (drop (call $diskw (i32.const 1024) (i32.const 4))))
 (func (export "update")
  (i32.store16 (i32.const 20) (i32.const 3))
  (call $rect (i32.const 20) (i32.const 20) (i32.const 100) (i32.const 100))))
