interrupt {
    // get char
    let c = input();
    // check if null
    if (c == 0) {
        halt();
    }
    // print char
    putc(c);
}

while (1) {
}
