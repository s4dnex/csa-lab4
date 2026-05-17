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

    push_m a_lo
    push_m b_lo
    add
    pop_m res_lo

    push_m a_hi
    push_m b_hi
    adc
    pop_m res_hi

    call print_result

    push message_sub
    call print_str

    push_m c_lo
    push_m d_lo
    sub
    pop_m res_lo

    push_m c_hi
    push_m d_hi
    sbc
    pop_m res_hi

    call print_result

    push message_mul
    call print_str

    push_m e
    push_m f
    mul
    pop_m res_lo

    push_m e
    push_m f
    mulh
    pop_m res_hi

    call print_result

    halt

print_result:
    push 2047
    push_m res_hi
    pop_ind

    push sep
    call print_str

    push 2047
    push_m res_lo
    pop_ind

    push sep
    call print_str
    ret

print_str:
    pop_m print_ptr

print_str_loop:
    push_m print_ptr
    push_ind
    jz print_str_end

    push 2046
    push_m print_ptr
    push_ind
    pop_ind

    push_m print_ptr
    push 1
    add
    pop_m print_ptr

    jmp print_str_loop

print_str_end:
    ret