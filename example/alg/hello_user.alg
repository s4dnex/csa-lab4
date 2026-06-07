let name = [0, 0, 0, 0, 0, 0, 0, 0]; // kostyl'
let name_len = 0;
let done = 0;

interrupt {
    let c = input();
    if (c == 10) {          // newline ends the name
        done = 1;
    } else if (c == 0) {    // null also ends the name
        done = 1;
    } else {
        name[name_len] = c;
        name_len = name_len + 1;
    }
}

print("What is your name? ");
while (done == 0) {
}

print("Hello, ");
let i = 0;
while (i < name_len) {
    putc(name[i]);
    i = i + 1;
}
print("!");
