## 0) Start in a clean Python environment (recommended)

If you currently have the pip wheel installed, remove it so you don’t accidentally import the non-CoCoA build:

```bash
python -m pip uninstall -y cvc5
```

(You can do this inside your pyenv/venv.)

---

## 1) Install system build dependencies (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
  git build-essential cmake pkg-config \
  python3-dev python3-pip \
  libgmp-dev \
  libantlr3c-dev antlr3 \
  libssl-dev \
  libreadline-dev
```

**Notes**
- Exact package names may vary slightly by distro.
- If `libantlr3c-dev` is unavailable, you can rely on `--auto-download` later.

---

## 2) Build and install CoCoALib (required for finite fields)

### 2.1 Get CoCoALib

```bash
mkdir -p ~/src
cd ~/src
git clone https://github.com/cocoa-official/CoCoALib.git
cd CoCoALib
```

### 2.2 Build and install (default prefix `/usr/local`)

```bash
./configure
make -j"$(nproc)"
sudo make install
```

### 2.3 Ensure the dynamic linker can find it

```bash
echo "/usr/local/lib" | sudo tee /etc/ld.so.conf.d/local.conf
sudo ldconfig
```

---

## 3) Build cvc5 with CoCoA support and Python bindings

### 3.1 Get cvc5

```bash
cd ~/src
git clone https://github.com/cvc5/cvc5.git
cd cvc5
```

### 3.2 (Optional but recommended) install Python build deps

```bash
python -m pip install -U pip
python -m pip install -U cython scikit-build pytest
```

### 3.3 Configure with CoCoA + Python bindings

- `--cocoa` enables finite-field support via CoCoA
- `--python-bindings` builds the Python API
- `--auto-download` fetches missing deps automatically

```bash
./configure.sh --cocoa --python-bindings --auto-download
```

### 3.4 Build and install

```bash
cd build
make -j"$(nproc)"
make check
sudo make install
```

After installation, the cvc5 binary and libraries are typically installed under `/usr/local`.

---

## 4) Quick finite-field sanity test

```bash
python - <<'PY'
from cvc5.pythonic import SolverFor, FiniteFieldSort, FiniteFieldElems, sat

p = 17
F = FiniteFieldSort(p)
x, y = FiniteFieldElems("x y", F)

s = SolverFor("QF_FF")
s.add(x * y == 1)
s.add(x == 2)

r = s.check()
print("result:", r)
print("model y:", s.model()[y])
assert r == sat
PY
```
