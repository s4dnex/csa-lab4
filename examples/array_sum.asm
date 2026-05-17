.data
array:  .word 10
        .word 20
        .word 30
        .word 40
        .word 50
len:    .word 5
sum:    .word 0
i:      .word 0

.text
_start:
loop:
    push_m i
    push_m len
    lt
    jz print_sum

    push 2047
    push array
    push_m i
    add
    push_ind
    pop_ind

    push_m i
    push_m len
    push 1
    sub
    cmp
    call print_space
    jnz print_equals

    push 2046
    push 43
    pop_ind
    call print_space

    jmp after_sep

print_space:
    push 2046
    push 32
    pop_ind
    ret

print_equals:
    push 2046
    push 61
    pop_ind
    call print_space

after_sep:
    push_m sum
    push array
    push_m i
    add
    push_ind
    add
    pop_m sum

    push_m i
    push 1
    add
    pop_m i
    jmp loop

print_sum:
    push 2047
    push_m sum
    pop_ind
    halt