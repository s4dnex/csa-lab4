.data
cur:    .word 1
sum:    .word 0
sum_sq: .word 0

.text
_start:
loop:
    push_m cur
    push 100
    gt
    jnz done

    push_m sum
    push_m cur
    add
    pop_m sum

    push_m cur
    dup
    mul
    push_m sum_sq
    add
    pop_m sum_sq

    push_m cur
    push 1
    add
    pop_m cur
    jmp loop

done:
    push_m sum
    dup
    mul

    push_m sum_sq
    sub

    push 2047
    pop_ind

    halt