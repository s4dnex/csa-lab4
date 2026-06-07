let n = 100;
let i = 1;
let sum = 0;
let sqsum = 0;

// Euler problem 6: (sum of [1..n])^2 - (sum of squares of [1..n])
while (i <= n) {
    sum = sum + i;
    sqsum = sqsum + i * i;
    i = i + 1;
}

let result = sum * sum - sqsum;
print(result);
putc(10);
