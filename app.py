
import base64
import hashlib
import io
import json
import os
import tkinter as tk

from datetime import datetime, timezone
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

import fitz  # PyMuPDF


def add_signature_image(pdf_data: bytes, parent) -> bytes:
    """Chèn ảnh chữ ký vào PDF và trả về nội dung PDF mới."""
    if not messagebox.askyesno(
        "Ảnh chữ ký",
        "Bạn có muốn chèn ảnh chữ ký vào PDF trước khi ký không?",
        parent=parent,
    ):
        return pdf_data

    image_file = filedialog.askopenfilename(
        title="Chọn ảnh chữ ký",
        filetypes=[
            ("Ảnh PNG/JPG", "*.png *.jpg *.jpeg"),
            ("Tất cả file", "*.*")
        ]
    )
    if not image_file:
        raise ValueError("Chưa chọn ảnh chữ ký.")

    doc = None
    try:
        doc = fitz.open(stream=pdf_data, filetype="pdf")

        if doc.is_encrypted:
            raise ValueError(
                "PDF được mã hóa. Hãy mở khóa hợp lệ trước."
            )

        if len(doc) == 0:
            raise ValueError("PDF không có trang.")

        page_number = simpledialog.askinteger(
            "Trang PDF",
            f"Nhập số trang (1–{len(doc)}):",
            minvalue=1,
            maxvalue=len(doc),
        )
        if page_number is None:
            return

        page = doc[page_number - 1]

        width = simpledialog.askfloat(
            "Chiều rộng",
            "Chiều rộng ảnh chữ ký (đơn vị point):",
            initialvalue=150,
            minvalue=10,
        )
        if width is None:
            return

        height = simpledialog.askfloat(
            "Chiều cao",
            "Chiều cao ảnh chữ ký (đơn vị point):",
            initialvalue=55,
            minvalue=10,
        )
        if height is None:
            return

        if width > page.rect.width or height > page.rect.height:
            raise ValueError("Kích thước ảnh chữ ký lớn hơn trang PDF.")

        preview = tk.Toplevel(parent)
        preview.title("Chọn vị trí chữ ký")
        preview.transient(parent)
        preview.grab_set()

        # Chừa chỗ cho tiêu đề, hướng dẫn và nút xác nhận.
        max_width = min(900, parent.winfo_screenwidth() - 80)
        max_height = min(520, parent.winfo_screenheight() - 190)
        scale = min(
            max_width / page.rect.width,
            max_height / page.rect.height,
            1,
        )
        preview_width = max(1, int(page.rect.width * scale))
        preview_height = max(1, int(page.rect.height * scale))
        pixmap = page.get_pixmap(
            matrix=fitz.Matrix(scale, scale),
            alpha=False,
        )
        page_image = tk.PhotoImage(data=pixmap.tobytes("ppm"))

        ttk.Label(
            preview,
            text="Bấm vào vị trí muốn đặt góc trên-trái của chữ ký, sau đó xác nhận.",
            padding=8,
        ).pack()
        canvas = tk.Canvas(
            preview,
            width=preview_width,
            height=preview_height,
            highlightthickness=1,
            highlightbackground="#888888",
        )
        canvas.pack(padx=8)
        canvas.create_image(0, 0, image=page_image, anchor="nw")

        initial_x = max(0, page.rect.width - width - 40)
        initial_y = max(0, page.rect.height - height - 60)
        selected = {"x": initial_x, "y": initial_y, "confirmed": False}
        signature_box = None
        signature_label = None

        def draw_signature_box(event=None):
            nonlocal signature_box, signature_label
            if signature_box is not None:
                canvas.delete(signature_box)
            if signature_label is not None:
                canvas.delete(signature_label)
            left = selected["x"] * scale
            top = selected["y"] * scale
            right = left + width * scale
            bottom = top + height * scale
            signature_box = canvas.create_rectangle(
                left,
                top,
                right,
                bottom,
                outline="#d62828",
                width=2,
            )
            signature_label = canvas.create_text(
                left + 4,
                top + 4,
                text="Chữ ký",
                anchor="nw",
                fill="#d62828",
            )

        def choose_position(event):
            selected["x"] = min(
                max(0, event.x / scale),
                max(0, page.rect.width - width),
            )
            selected["y"] = min(
                max(0, event.y / scale),
                max(0, page.rect.height - height),
            )
            draw_signature_box()

        def confirm_position():
            selected["confirmed"] = True
            preview.destroy()

        canvas.bind("<Button-1>", choose_position)
        draw_signature_box()
        button_frame = ttk.Frame(preview, padding=(8, 0, 8, 8))
        button_frame.pack(fill="x")
        ttk.Button(
            button_frame,
            text="Xác nhận vị trí",
            command=confirm_position,
        ).pack(pady=8)
        preview.protocol("WM_DELETE_WINDOW", preview.destroy)
        preview.update_idletasks()
        preview.geometry(
            f"{preview.winfo_reqwidth()}x{preview.winfo_reqheight()}"
        )
        preview.wait_window()

        if not selected["confirmed"]:
            return pdf_data

        x = selected["x"]
        y = selected["y"]

        page.insert_image(
            fitz.Rect(x, y, x + width, y + height),
            filename=image_file,
            keep_proportion=True,
            overlay=True,
        )

        output = io.BytesIO()
        doc.save(output, garbage=3, deflate=True)
        return output.getvalue()

    except Exception as exc:
        raise ValueError(f"Không thể chèn ảnh chữ ký: {exc}") from exc
    finally:
        if doc is not None:
            doc.close()



APP_NAME = "USB Signer"
KEY_DIR_NAME = "keys"
PRIVATE_NAME = "private_key.pem"
PUBLIC_NAME = "public_key.pem"
SIGNATURE_SUFFIX = ".sig.json"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: dict) -> bytes:
    """Chuyển dữ liệu JSON về biểu diễn ổn định để ký."""
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def public_key_bytes(public_key) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def fingerprint(public_key) -> str:
    return sha256(public_key_bytes(public_key))


def load_trusted_public_key(key_dir: Path):
    path = key_dir / PUBLIC_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"Không tìm thấy khóa công khai:\n{path}"
        )

    return serialization.load_pem_public_key(path.read_bytes())


class USBSignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("USB Signer - Digital Signature Lab")
        self.root.geometry("720x490")
        self.root.minsize(620, 430)

        self.usb_path = tk.StringVar()
        self.status = tk.StringVar(
            value="Chưa chọn thư mục USB."
        )

        self.build_ui()

    @property
    def key_dir(self):
        if not self.usb_path.get():
            raise ValueError("Hãy chọn thư mục USB trước.")
        return Path(self.usb_path.get()) / KEY_DIR_NAME

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        ttk.Label(
            outer,
            text="USB SIGNER",
            font=("Segoe UI", 21, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            outer,
            text="Ký và xác minh PDF offline bằng Ed25519",
        ).pack(anchor="w", pady=(2, 18))

        usb_frame = ttk.LabelFrame(
            outer, text="1. Thư mục USB", padding=10
        )
        usb_frame.pack(fill="x", pady=5)

        ttk.Entry(
            usb_frame, textvariable=self.usb_path
        ).pack(side="left", fill="x", expand=True)

        ttk.Button(
            usb_frame,
            text="Chọn USB",
            command=self.choose_usb,
        ).pack(side="left", padx=(8, 0))

        key_frame = ttk.LabelFrame(
            outer, text="2. Quản lý khóa", padding=10
        )
        key_frame.pack(fill="x", pady=5)

        ttk.Button(
            key_frame,
            text="Tạo cặp khóa",
            command=self.create_keys,
        ).pack(side="left", padx=4)

        ttk.Button(
            key_frame,
            text="Kiểm tra khóa",
            command=self.check_keys,
        ).pack(side="left", padx=4)

        pdf_frame = ttk.LabelFrame(
            outer, text="3. PDF", padding=10
        )
        pdf_frame.pack(fill="x", pady=5)

        ttk.Button(
            pdf_frame,
            text="Ký PDF",
            command=self.sign_pdf,
        ).pack(side="left", padx=4)

        ttk.Button(
            pdf_frame,
            text="Xác minh chữ ký",
            command=self.verify_pdf,
        ).pack(side="left", padx=4)

        ttk.Label(
            outer,
            textvariable=self.status,
            wraplength=660,
        ).pack(anchor="w", pady=(18, 6))

        ttk.Label(
            outer,
            text=(
                "Ảnh chữ ký được chèn vào PDF trước khi ký. "
                "Kết quả gồm file .signed.pdf và chữ ký detached .sig.json; "
                "đây không phải chứng thư số được công nhận."
            ),
            wraplength=660,
        ).pack(anchor="w", pady=4)

    def choose_usb(self):
        path = filedialog.askdirectory(
            title="Chọn thư mục gốc của USB"
        )
        if path:
            self.usb_path.set(path)
            self.status.set(f"USB: {path}")

    def require_usb(self):
        if not self.usb_path.get():
            raise ValueError("Bạn chưa chọn thư mục USB.")

        path = Path(self.usb_path.get())
        if not path.is_dir():
            raise FileNotFoundError(
                "USB hoặc thư mục đã chọn không tồn tại."
            )
        return path

    def create_keys(self):
        try:
            usb = self.require_usb()
            key_dir = usb / KEY_DIR_NAME

            key_dir.mkdir(parents=True, exist_ok=True)
            private_path = key_dir / PRIVATE_NAME
            public_path = key_dir / PUBLIC_NAME

            # Không ghi đè khóa cũ, tránh mất quyền xác minh.
            if private_path.exists() or public_path.exists():
                messagebox.showwarning(
                    "Đã có khóa",
                    "Thư mục đã có file khóa. "
                    "Không tạo đè để tránh mất khóa cũ."
                )
                return

            password = simpledialog.askstring(
                "Mật khẩu khóa riêng",
                "Nhập mật khẩu mạnh để mã hóa khóa riêng:",
                show="*",
                parent=self.root,
            )
            if password is None:
                return
            if len(password) < 12:
                raise ValueError(
                    "Hãy dùng mật khẩu ít nhất 12 ký tự."
                )

            confirm = simpledialog.askstring(
                "Xác nhận mật khẩu",
                "Nhập lại mật khẩu:",
                show="*",
                parent=self.root,
            )
            if confirm != password:
                raise ValueError("Mật khẩu xác nhận không khớp.")

            private_key = Ed25519PrivateKey.generate()
            public_key = private_key.public_key()

            encrypted_private = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=(
                    serialization.BestAvailableEncryption(
                        password.encode("utf-8")
                    )
                ),
            )

            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )

            # Chỉ ghi file sau khi đã tạo đầy đủ dữ liệu.
            private_path.write_bytes(encrypted_private)
            try:
                public_path.write_bytes(public_pem)
            except Exception:
                private_path.unlink(missing_ok=True)
                raise

            self.status.set(
                "Đã tạo khóa. Hãy sao lưu an toàn và giữ bí mật "
                "mật khẩu khóa riêng."
            )
            messagebox.showinfo(
                "Thành công",
                f"Đã tạo cặp khóa tại:\n{key_dir}"
            )

        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))

    def check_keys(self):
        try:
            key_dir = self.require_usb() / KEY_DIR_NAME
            public_key = load_trusted_public_key(key_dir)

            self.status.set(
                "Khóa công khai hợp lệ. Fingerprint SHA-256: "
                + fingerprint(public_key)
            )
        except Exception as exc:
            messagebox.showerror("Lỗi", str(exc))

    def sign_pdf(self):
        try:
            key_dir = self.require_usb() / KEY_DIR_NAME
            private_path = key_dir / PRIVATE_NAME

            if not private_path.is_file():
                raise FileNotFoundError(
                    "Chưa có khóa riêng trên USB."
                )

            pdf_path = filedialog.askopenfilename(
                title="Chọn PDF cần ký",
                filetypes=[("PDF", "*.pdf")],
            )
            if not pdf_path:
                return

            path = Path(pdf_path)
            if path.stat().st_size == 0:
                raise ValueError("File PDF rỗng.")

            pdf_data = add_signature_image(
                path.read_bytes(),
                self.root,
            )

            password = simpledialog.askstring(
                "Mở khóa",
                "Nhập mật khẩu khóa riêng:",
                show="*",
                parent=self.root,
            )
            if password is None:
                return

            private_key = serialization.load_pem_private_key(
                private_path.read_bytes(),
                password=password.encode("utf-8"),
            )
            public_key = private_key.public_key()

            signed_path_text = filedialog.asksaveasfilename(
                title="Lưu PDF đã ký",
                initialdir=str(path.parent),
                initialfile=path.stem + ".signed.pdf",
                defaultextension=".signed.pdf",
                filetypes=[("Signed PDF", "*.signed.pdf")],
            )
            if not signed_path_text:
                return
            signed_path = Path(signed_path_text)

            if signed_path.suffixes[-2:] != [".signed", ".pdf"]:
                signed_path = signed_path.with_name(
                    signed_path.name.removesuffix(".pdf") + ".signed.pdf"
                )

            if signed_path.resolve() == path.resolve():
                raise ValueError(
                    "Hãy lưu thành file .signed.pdf mới để giữ nguyên PDF gốc."
                )

            payload = {
                "format": "usb-signer-detached-v1",
                "algorithm": "Ed25519",
                "filename": signed_path.name,
                "size_bytes": len(pdf_data),
                "sha256": sha256(pdf_data),
                "created_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "public_key_fingerprint": fingerprint(
                    public_key
                ),
            }

            signature = private_key.sign(
                canonical_json(payload)
            )

            envelope = {
                "payload": payload,
                "signature_base64": base64.b64encode(
                    signature
                ).decode("ascii"),
            }

            signed_path.write_bytes(pdf_data)

            output_path_text = filedialog.asksaveasfilename(
                title="Lưu file chữ ký",
                initialdir=str(path.parent),
                initialfile=signed_path.name + SIGNATURE_SUFFIX,
                defaultextension=".json",
                filetypes=[("Signature JSON", "*.json")],
            )
            if not output_path_text:
                return
            output_path = Path(output_path_text)

            output_path.write_text(
                json.dumps(
                    envelope,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            self.status.set(
                f"Đã ký PDF.\nPDF: {signed_path}\n"
                f"File chữ ký: {output_path}"
            )
            messagebox.showinfo(
                "Đã ký",
                f"Đã lưu PDF đã ký:\n{signed_path}\n\n"
                f"Đã tạo chữ ký detached:\n{output_path}"
            )

        except Exception as exc:
            messagebox.showerror("Không thể ký", str(exc))

    def verify_pdf(self):
        try:
            key_dir = self.require_usb() / KEY_DIR_NAME
            public_key = load_trusted_public_key(key_dir)

            pdf_path = filedialog.askopenfilename(
                title="Chọn PDF gốc",
                filetypes=[("PDF", "*.pdf")],
            )
            if not pdf_path:
                return

            sig_path = filedialog.askopenfilename(
                title="Chọn file chữ ký .sig.json",
                filetypes=[
                    ("Signature JSON", "*.json"),
                    ("All files", "*.*"),
                ],
            )
            if not sig_path:
                return

            envelope = json.loads(
                Path(sig_path).read_text(encoding="utf-8")
            )
            payload = envelope["payload"]

            if payload["format"] != "usb-signer-detached-v1":
                raise ValueError("Định dạng chữ ký không hỗ trợ.")

            if payload["algorithm"] != "Ed25519":
                raise ValueError("Thuật toán chữ ký không hỗ trợ.")

            # Ràng buộc chữ ký với khóa công khai tin cậy trên USB.
            if payload["public_key_fingerprint"] != fingerprint(
                public_key
            ):
                raise ValueError(
                    "Fingerprint không khớp khóa trên USB. "
                    "Không thể xác nhận đúng khóa ký."
                )

            pdf_data = Path(pdf_path).read_bytes()

            if len(pdf_data) != payload["size_bytes"]:
                raise ValueError(
                    "Kích thước PDF thay đổi. Xác minh thất bại."
                )

            if sha256(pdf_data) != payload["sha256"]:
                raise ValueError(
                    "Nội dung PDF đã thay đổi. "
                    "Xác minh thất bại."
                )

            signature = base64.b64decode(
                envelope["signature_base64"],
                validate=True,
            )

            public_key.verify(
                signature,
                canonical_json(payload),
            )

            messagebox.showinfo(
                "Xác minh thành công",
                "Chữ ký hợp lệ với khóa công khai trên USB.\n"
                "Nội dung PDF khớp với dữ liệu đã ký."
            )
            self.status.set("KẾT QUẢ: Chữ ký hợp lệ.")

        except InvalidSignature:
            messagebox.showerror(
                "Chữ ký không hợp lệ",
                "Chữ ký mật mã không khớp dữ liệu."
            )
        except Exception as exc:
            messagebox.showerror(
                "Xác minh thất bại", str(exc)
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = USBSignerApp(root)
    root.mainloop()
