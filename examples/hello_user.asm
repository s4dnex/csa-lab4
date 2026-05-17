.text
.org 0x0
trap_vector:
    jmp process_trap

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
    push_m 2045
    pop_m current_symb

    push_m current_symb
    push 10
    sub
    jz trap_end

    push_m current_symb
    push 0
    sub
    jz trap_end

    push name
    push_m name_len
    add
    push_m current_symb
    pop_ind

    push_m name_len
    push 1
    add
    pop_m name_len
    iret

trap_end:
    push 1
    pop_m input_done
    iret

_start:
    push question
    call print_str

wait_input:
    push_m input_done
    jz wait_input

    push hello_str
    call print_str

    push name
    push_m name_len
    call print_raw_str

    push end_str
    call print_str

    halt

print_str:
    pop_m str_ptr

print_str_loop:
    push_m str_ptr
    push_ind
    jz print_end

    push 2046
    push_m str_ptr
    push_ind
    pop_ind

    push_m str_ptr
    push 1
    add
    pop_m str_ptr

    jmp print_str_loop

print_raw_str:
    pop_m name_len
    pop_m str_ptr

print_raw_loop:
    push_m name_len
    jz print_end

    push 2046
    push_m str_ptr
    push_ind
    pop_ind

    push_m str_ptr
    push 1
    add
    pop_m str_ptr

    push_m name_len
    push 1
    sub
    pop_m name_len

    jmp print_raw_loop

print_end:
    ret