.data
.org 0x20
message_add:    .str "4294967295 + 2 = "
message_sub:    .str "4294967297 - 2 = "
message_mul:    .str "100000 * 100000 = "
sep:            .str " "

a_hi:           .word 0
a_lo:           .word -1
b_hi:           .word 0
b_lo:           .word 2

c_hi:           .word 1
c_lo:           .word 1
d_hi:           .word 0
d_lo:           .word 2

e:              .word 100000
f:              .word 100000

res_hi:         .word 0
res_lo:         .word 0
print_ptr:      .word 0

.text
.org 150
_start:
    push message_add
    call print_str

    pushm a_lo
    pushm b_lo
    add
    popm res_lo

    pushm a_hi
    pushm b_hi
    addc
    popm res_hi

    call print_result

    push message_sub
    call print_str

    pushm c_lo
    pushm d_lo
    sub
    popm res_lo

    pushm c_hi
    pushm d_hi
    subc
    popm res_hi

    call print_result

    push message_mul
    call print_str

    pushm e
    pushm f
    mul
    popm res_lo

    pushm e
    pushm f
    mulh
    popm res_hi

    call print_result

    halt

print_result:
    push 2047
    pushm res_hi
    popi

    push sep
    call print_str

    push 2047
    pushm res_lo
    popi

    push sep
    call print_str
    ret

print_str:
    popm print_ptr

print_str_loop:
    pushm print_ptr
    pushi
    beqz print_str_end

    push 2046
    pushm print_ptr
    pushi
    popi

    pushm print_ptr
    push 1
    add
    popm print_ptr

    jump print_str_loop

print_str_end:
    ret