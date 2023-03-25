**2023-03-25 22:36:58**

**Question:** write a c++ function to check if a number is prime or not

**Answer:** Here's a C++ function to check if a given number is prime or not:

```cpp
bool isPrime(int n) {
    if (n <= 1) {
        return false;
    }
    for (int i = 2; i <= sqrt(n); i++) {
        if (n % i == 0) {
            return false;
        }
    }
    return true;
}
```

This function takes an integer `n` as input and returns a boolean value indicating whether `n` is a prime number or not. 

The function first checks if `n` is less than or equal to 1, in which case it returns `false` since 1 and all numbers less than 1 are not prime