.text
.org 0x0
trap_vector:
    jmp process_trap

_start:
useless:
    jmp useless

process_trap:
    push_m 2045
    dup
    push 0
    cmp
    jz print_char

    halt

print_char:
    pop_m 2046
    iret