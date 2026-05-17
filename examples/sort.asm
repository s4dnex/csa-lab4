.data
len:    .word 6
array:  .word 42
        .word 15
        .word 8
        .word 100
        .word 4
        .word 23

i:      .word 0
j:      .word 0
a:      .word 0
b:      .word 0

.text
_start:
    push_m len
    pop_m i

outer:
    push_m i
    jz print_loop

    push 0
    pop_m j

inner:
    push_m j
    push_m i
    push 1
    sub
    lt
    jz end_inner

    push array
    push_m j
    add
    push_ind
    pop_m a

    push array
    push_m j
    push 1
    add
    add
    push_ind
    pop_m b

    push_m a
    push_m b
    gt
    jz no_swap

    push array
    push_m j
    add
    push_m b
    pop_ind

    push array
    push_m j
    push 1
    add
    add
    push_m a
    pop_ind

no_swap:
    push_m j
    push 1
    add
    pop_m j
    jmp inner

end_inner:
    push_m i
    push 1
    sub
    pop_m i
    jmp outer

print_loop:
    push_m i
    push_m len
    lt
    jz end

    push 2047
    push array
    push_m i
    add
    push_ind
    pop_ind

    push 2046
    push 32
    pop_ind

    push_m i
    push 1
    add
    pop_m i
    jmp print_loop

end:
    halt