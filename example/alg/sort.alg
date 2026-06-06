let array = [42, 15, 8, 100, 4, 23];
let n = len(array);

let i = n;
// Bubble sort
while (i > 0) {
    let j = 0;
    while (j < i - 1) {
        if (array[j] > array[j + 1]) {
            let tmp = array[j];
            array[j] = array[j + 1];
            array[j + 1] = tmp;
        }
        j = j + 1;
    }
    i = i - 1;
}

let k = 0;
while (k < n) {
    print(array[k]);
    putc(32);
    k = k + 1;
}
