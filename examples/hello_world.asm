.data
message:    .str "Hello, World!"

ptr:        .word 0

.text
_start:
    push message
    popm ptr

loop:
    pushm ptr
    pushi
    beqz end

    push 2046
    pushm ptr
    pushi
    popi

    pushm ptr
    push 1
    add
    popm ptr

    jump loop

end:
    halt