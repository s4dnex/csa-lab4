.data
message:    .str "Hello, World!"

ptr:        .word 0

.text
_start:
    push message
    pop_m ptr

loop:
    push_m ptr
    push_ind
    jz end

    push 2046
    push_m ptr
    push_ind
    pop_ind

    push_m ptr
    push 1
    add
    pop_m ptr

    jmp loop

end:
    halt