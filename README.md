# USB Signer — Offline PDF Signing & Verification

A lightweight Windows desktop application built with **Python** and **Tkinter** for signing and verifying PDF files offline. It uses **Ed25519** public-key cryptography and stores the key pair in a selected USB-drive folder.

> **Important:** This is an educational/personal cryptographic signing tool. It does **not** create a certificate-based digital signature embedded in the PDF and is **not** a legally recognized digital-signature service by itself.

## Features

- **Offline workflow:** Sign and verify files locally without requiring a cloud service.
- **Ed25519 signatures:** Sign signature metadata using an Ed25519 private key.
- **Encrypted private key:** Protect the private key with a password when creating the key pair.
- **USB-based key storage:** Store `private_key.pem` and `public_key.pem` in a `keys/` directory on the selected USB drive.
- **PDF integrity checks:** Record the PDF byte length and SHA-256 hash, then verify them later.
- **Signature image placement:** Optionally insert a PNG/JPG signature image into a selected PDF page before signing.
- **Position preview:** Choose where the signature image appears on the page.
- **Detached signature file:** Save signature metadata separately as a JSON file.
- **Key fingerprint check:** Bind verification to the public key stored on the selected USB drive.
- **Simple GUI:** Use file dialogs and buttons instead of command-line commands.

## How it works

1. Create an Ed25519 key pair.
2. Optionally insert a signature image into the PDF.
3. The app calculates the PDF's SHA-256 hash and records its size and metadata.
4. The app signs the canonicalized metadata with the private key.
5. The PDF is saved as a separate `.signed.pdf` file, and the detached signature envelope is saved as JSON.
6. To verify, select the PDF, the JSON signature file, and the USB folder containing the trusted public key. The app checks the key fingerprint, file size, hash, and cryptographic signature.

The JSON signature file uses the format identifier `usb-signer-detached-v1` and the `Ed25519` algorithm.

## Requirements

- Windows with Python 3.10 or newer recommended
- A USB drive or local folder for key storage
- Python packages:
  - `cryptography`
  - `PyMuPDF` (`fitz`)

`tkinter` is included with most standard Windows Python installations.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/usb-signer.git
cd usb-signer
```

Replace `YOUR_USERNAME/usb-signer` with your actual GitHub repository path.

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Activate it in Command Prompt:

```bat
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install cryptography pymupdf
```

### 4. Run the application

Save the Python application as `app.py`, then run:

```bash
python app.py
```

## Usage

### 1. Select the USB folder

Click **Chọn USB** and select the root folder of your USB drive (for example, `E:\`). The application will use a `keys/` folder inside it.

### 2. Create a key pair

Click **Tạo cặp khóa** and enter a strong password of at least 12 characters, then confirm it.

The app creates:

```text
USB/
└── keys/
    ├── private_key.pem
    └── public_key.pem
```

The private key is encrypted with the password. The app will not overwrite existing key files.

### 3. Sign a PDF

1. Click **Ký PDF** and select the PDF file.
2. Choose whether to insert a signature image.
3. If you choose to insert one, select a PNG/JPG image, the target page, image dimensions, and placement.
4. Enter the private-key password.
5. Choose where to save the resulting `.signed.pdf` file.
6. Choose where to save the detached `.sig.json` signature file.

Keep the signed PDF and its matching JSON signature file together.

### 4. Verify a PDF

1. Select the USB folder that contains the trusted public key.
2. Click **Xác minh chữ ký**.
3. Select the PDF file to verify.
4. Select the corresponding `.sig.json` file.
5. The app reports whether the PDF content and signature match the trusted public key.

**Do not edit or re-save the signed PDF after signing.** Even a small change can change its hash and cause verification to fail.

## Suggested repository structure

```text
usb-signer/
├── app.py
├── README.md
├── requirements.txt
├── .gitignore
└── keys/                 # Runtime key storage; do not commit real keys
```

Create a `requirements.txt` file:

```text
cryptography
PyMuPDF
```

Suggested `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
keys/
*.pem
*.sig.json
*.signed.pdf
.env
```

> Keep private keys, passwords, personal documents, and real signature files out of public repositories.

## Security notes and limitations

- **Not a certificate-based PDF digital signature:** The app creates a detached Ed25519 signature over metadata containing the PDF's hash. It does not embed a certificate-based signature into the PDF or establish a trusted identity through a certificate authority.
- **The signature image is visual only:** An image of a handwritten signature is not, by itself, proof of identity or cryptographic authenticity.
- **Protect the USB drive:** Anyone who obtains the encrypted private-key file and guesses its password may be able to use it. Use a strong, unique password and keep a secure backup.
- **Keep the public key trustworthy:** Verification relies on the public key on the selected USB drive. If an attacker replaces that key and the signature metadata together, the app alone does not provide an independent trust anchor. Compare the SHA-256 fingerprint through a trusted channel when appropriate.
- **Detached file required:** Verification needs both the PDF and its matching `.sig.json` file.
- **Local testing recommended:** Test with copies of non-sensitive PDFs before relying on the application for important files.
- **Not a substitute for a recognized signing provider:** For legal, organizational, or regulated workflows, use a signing solution that meets the applicable requirements.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'cryptography'`**  
  Run `python -m pip install cryptography`.

- **`ModuleNotFoundError: No module named 'fitz'`**  
  Install PyMuPDF with `python -m pip install pymupdf`.

- **The signature fails verification**  
  Make sure you selected the exact PDF produced during signing and the matching JSON file. Do not modify or re-save the PDF after signing.

- **The key password is rejected**  
  Re-enter the password used when the key pair was created. The application cannot recover a forgotten password.

- **The USB drive letter changes**  
  Select the USB folder again in the application. The app does not permanently remember the selected path.

## Roadmap ideas

- Add automated tests for key generation, signing, and verification.
- Add clearer validation for malformed signature files.
- Package the application as a Windows executable.
- Improve backup and recovery guidance for keys.
- Add a signed manifest/export workflow for easier file sharing.

## License

No license has been specified yet. Add a `LICENSE` file before presenting this project as open source. If you choose a license, make sure it matches how you want others to use, modify, and distribute the code.

---

**Built with:** Python · Tkinter · `cryptography` · PyMuPDF · Ed25519
