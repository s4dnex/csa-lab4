let a_lo = -1;   // 0x00000000_FFFFFFFF = 4294967295
let a_hi = 0; 
let b_lo = 2;
let b_hi = 0; 
let c_lo = 1;    // 0x00000001_00000001 = 4294967297
let c_hi = 1; 
let d_lo = 2;
let d_hi = 0; 
let e = 100000;
let f = 100000;
let res_lo = 0;
let res_hi = 0; 

func print_result() {
    print(res_hi);
    print(" ");
    print(res_lo);
    print(" ");
}

print("4294967295 + 2 = ");
res_lo = a_lo + b_lo;          // carry set
res_hi = addc(a_hi, b_hi);     // add carry
print_result();

print("4294967297 - 2 = ");
res_lo = c_lo - d_lo;          // borrow set
res_hi = subc(c_hi, d_hi);     // subtract borrow
print_result();

print("100000 * 100000 = ");
res_lo = e * f;                // low bits of product
res_hi = mulh(e, f);           // high bits of product
print_result();
