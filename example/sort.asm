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
    pushm len
    popm i

outer:
    pushm i
    beqz print_loop

    push 0
    popm j

inner:
    pushm j
    pushm i
    push 1
    sub
    lt
    beqz end_inner

    push array
    pushm j
    add
    pushi
    popm a

    push array
    pushm j
    push 1
    add
    add
    pushi
    popm b

    pushm a
    pushm b
    gt
    beqz no_swap

    push array
    pushm j
    add
    pushm b
    popi

    push array
    pushm j
    push 1
    add
    add
    pushm a
    popi

no_swap:
    pushm j
    push 1
    add
    popm j
    jump inner

end_inner:
    pushm i
    push 1
    sub
    popm i
    jump outer

print_loop:
    pushm i
    pushm len
    lt
    beqz end

    push 2047
    push array
    pushm i
    add
    pushi
    popi

    push 2046
    push 32
    popi

    pushm i
    push 1
    add
    popm i
    jump print_loop

end:
    halt