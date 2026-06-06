.data
cur:    .word 1
sum:    .word 0
sum_sq: .word 0

.text
_start:
loop:
    pushm cur
    push 100
    gt
    bnez done

    pushm sum
    pushm cur
    add
    popm sum

    pushm cur
    dup
    mul
    pushm sum_sq
    add
    popm sum_sq

    pushm cur
    push 1
    add
    popm cur
    jump loop

done:
    pushm sum
    dup
    mul

    pushm sum_sq
    sub

    popm 65535

    halt
