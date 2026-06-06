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
    pushm i
    pushm len
    lt
    beqz print_sum

    push 65535
    push array
    pushm i
    add
    pushi
    popi

    pushm i
    pushm len
    push 1
    sub
    cmp
    call print_space
    bnez print_equals

    push 65534
    push 43
    popi
    call print_space

    jump after_sep

print_space:
    push 65534
    push 32
    popi
    ret

print_equals:
    push 65534
    push 61
    popi
    call print_space

after_sep:
    pushm sum
    push array
    pushm i
    add
    pushi
    add
    popm sum

    pushm i
    push 1
    add
    popm i
    jump loop

print_sum:
    push 65535
    pushm sum
    popi
    halt
