func banner() {
    print("=== alg demo ===\n");
}

banner();

// branching with comparison and else
let x = 7;
if (x % 2 == 0) {
    print("even\n");
} else {
    print("odd\n");
}

// nested arithmetic with precedence
let y = 2 + 3 * (x - 1);
print("y = ");
print(y);
putc(10);

// countdown loop
let n = 5;
while (n > 0) {
    print(n);
    putc(32);
    n = n - 1;
}
putc(10);
