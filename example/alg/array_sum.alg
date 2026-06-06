let array = [10, 20, 30, 40, 50];
let n = len(array);
let sum = 0;
let i = 0;

while (i < n) {
    print(array[i]);
    if (i < n - 1) {
        print(" + ");
    } else {
        print(" = ");
    }
    sum = sum + array[i];
    i = i + 1;
}

print(sum);
