.text
.org 0x0
trap_vector:
    jump process_trap

.data
question:       .str "What is your name? "
hello_str:      .str "Hello, "
end_str:        .str "!"

name_len:       .word 0
input_done:     .word 0
current_symb:   .word 0
str_ptr:        .word 0
name:           .word 0

.text
.org 0x150
process_trap:
    pushm 65533
    popm current_symb

    pushm current_symb
    push 10
    sub
    beqz trap_end

    pushm current_symb
    push 0
    sub
    beqz trap_end

    push name
    pushm name_len
    add
    pushm current_symb
    popi

    pushm name_len
    push 1
    add
    popm name_len
    iret

trap_end:
    push 1
    popm input_done
    iret

_start:
    ei
    push question
    call print_str

wait_input:
    pushm input_done
    beqz wait_input

    push hello_str
    call print_str

    push name
    pushm name_len
    call print_raw_str

    push end_str
    call print_str

    halt

print_str:
    popm str_ptr

print_str_loop:
    pushm str_ptr
    pushi
    beqz print_end

    push 65534
    pushm str_ptr
    pushi
    popi

    pushm str_ptr
    push 1
    add
    popm str_ptr

    jump print_str_loop

print_raw_str:
    popm name_len
    popm str_ptr

print_raw_loop:
    pushm name_len
    beqz print_end

    push 65534
    pushm str_ptr
    pushi
    popi

    pushm str_ptr
    push 1
    add
    popm str_ptr

    pushm name_len
    push 1
    sub
    popm name_len

    jump print_raw_loop

print_end:
    ret
