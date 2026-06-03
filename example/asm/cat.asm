.text
.org 0x0
trap_vector:
    jump process_trap

_start:
useless:
    jump useless

process_trap:
    pushm 65533
    dup
    push 0
    cmp
    beqz print_char

    halt

print_char:
    popm 65534
    iret
