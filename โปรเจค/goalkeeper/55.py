import tkinter as tk
from tkinter import ttk
from tkinter import messagebox, filedialog, simpledialog
from PIL import Image, ImageTk
import os
import json
import time
import sqlite3 
import shutil 
import webbrowser 
from datetime import datetime 
import pandas as pd # <--- (ใหม่) สำหรับ Sales Dashboard
from reportlab.pdfgen import canvas 
from reportlab.lib.pagesizes import A4 
from reportlab.pdfbase import pdfmetrics 
from reportlab.pdfbase.ttfonts import TTFont 
from reportlab.lib.utils import ImageReader 
from reportlab.lib.units import inch 

# ----------------------------------------------------------------------
# 📌 (อัปเดต) ธีมและสไตล์ (Theme & Styles) - ย้ายมาไว้ Global
# ----------------------------------------------------------------------
THEME = {
    "bg_primary": "#2C3E50",     # พื้นหลังหลัก (เข้มสุด)
    "bg_secondary": "#34495E",  # พื้นหลังรอง (เมนูข้าง, กรอบล็อกอิน)
    "bg_list": "#4A6278",       # พื้นหลังตาราง/ลิสต์ (เข้มน้อย)
    "text_primary": "#ECF0F1",  # สีตัวอักษรหลัก (สว่าง)
    "text_secondary": "#BDC3C7", # สีตัวอักษรรอง (เทา)
    "accent_blue": "#3498DB",    # สีเน้น (ฟ้า)
    "accent_green": "#2ECC71",   # สีเน้น (เขียว)
    "accent_orange": "#F39C12",  # สีเน้น (ส้ม)
    "accent_red": "#E74C3C",     # สีเน้น (แดง)
    "accent_select": "#5DADE2",   # สีตอนเลือกในตาราง
}

FONT_TITLE = ("Arial", 22, "bold")
FONT_HEADING = ("Arial", 18, "bold")
FONT_BUTTON = ("Arial", 12, "bold")
FONT_BODY = ("Arial", 11)
FONT_TREEVIEW = ("Arial", 10)
FONT_TREEVIEW_HEADING = ("Arial", 11, "bold")

# ----------------------------------------------------------------------
# 📌 Global Variables and Data Files
# ----------------------------------------------------------------------

# 🔑 ข้อมูลผู้ใช้ที่ล็อกอินปัจจุบัน
CURRENT_USER_DATA = {}

# 💾 (ใหม่) ชื่อไฟล์ดาต้าเบส
DB_FILE = "shop.db"

# 🛒 ตะกร้าสินค้า
cart = [] 
product_win = None  

root = None 
entry_username = None
entry_password = None

product_quantity_vars = {} 

# (ใหม่) ตัวแปรสำหรับตรวจสอบว่าลงทะเบียนฟอนต์ PDF หรือยัง
THAI_FONT_REGISTERED = False

# ----------------------------------------------------------------------
# 💾 (ใหม่) ฟังก์ชันจัดการดาต้าเบส SQLite
# ----------------------------------------------------------------------

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        profile_pic_path TEXT,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        address TEXT
    )
    """)
    # (อัปเดต) เพิ่ม category
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price TEXT NOT NULL,
        img TEXT,
        category TEXT 
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        total REAL,
        items_json TEXT, 
        slip_path TEXT,
        status TEXT,
        timestamp TEXT,
        receipt_path TEXT 
    )
    """)
    
    try:
        cursor.execute("ALTER TABLE orders ADD COLUMN receipt_path TEXT")
    except sqlite3.OperationalError:
        pass 

    # (อัปเดต) เพิ่ม category column ถ้ายังไม่มี
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN category TEXT")
        print("เพิ่มคอลัมน์ category ในตาราง products แล้ว")
    except sqlite3.OperationalError:
        pass 

    conn.commit()
    conn.close()

def save_user(username, password, profile_pic_path="", full_name="", email="", phone="", address=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO users 
    (username, password, profile_pic_path, full_name, email, phone, address)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, password, profile_pic_path, full_name, email, phone, address))
    conn.commit()
    conn.close()


def load_user_data():
    """(ใหม่) อ่านข้อมูลผู้ใช้คนเดียวที่บันทึกไว้จาก DB"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users LIMIT 1")
    user_row = cursor.fetchone()
    conn.close()
    if user_row:
        user_data = dict(user_row)
        if 'profile_pic_path' in user_data:
            user_data['path'] = user_data.pop('profile_pic_path')
        return user_data
    return None

def load_user_by_username(username):
    """(ใหม่) อ่านข้อมูลผู้ใช้ที่ระบุจาก DB"""
    if not username:
        return {} 
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        user_data = dict(user_row)
        if 'profile_pic_path' in user_data:
            user_data['path'] = user_data.pop('profile_pic_path')
        return user_data
    
    print(f"Warning: ไม่พบข้อมูลผู้ใช้สำหรับ username '{username}' ในการสร้าง PDF")
    return {} 

def load_user_for_reset(username, email):
    """(ใหม่) ตรวจสอบ User จาก Username และ Email"""
    if not username or not email:
        return None
        
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE username = ? AND email = ?", (username, email))
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        return dict(user_row)
    return None

def load_products():
    """(ใหม่) โหลดรายการสินค้าจากตาราง products"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products")
    product_rows = cursor.fetchall()
    products = [dict(row) for row in product_rows]
    
    if not products:
        # (อัปเดต) เพิ่ม category
        default_products = [
            {"name": "ถุงมือผู้รักษาประตู Pro1", "price": "1,200฿", "img": "images/zzzzzz.jpg", "category": "NIKE"},
            {"name": "ถุงมือผู้รักษาประตู Pro2", "price": "1,500฿", "img": "images/zzzzz.jpg", "category": "ADIDAS"},
            {"name": "ถุงมือผู้รักษาประตู Pro3", "price": "1,800฿", "img": "images/zzzz.jpg", "category": "PUMA"},
            {"name": "ถุงมือผู้รักษาประตู Pro4", "price": "2,000฿", "img": "images/zzz.jpg", "category": "Reusch"},
            {"name": "ถุงมือผู้รักษาประตู Champion", "price": "2,500฿", "img": "images/y.jpg", "category": "NIKE"},
            {"name": "ถุงมือผู้รักษาประตู Supreme", "price": "2,800฿", "img": "images/R.jpg", "category": "ADIDAS"},
            {"name": "ถุงมือผู้รักษาประตู Pro1 (สีดำ)", "price": "1,200฿", "img": "images/RR.jpg", "category": "PUMA"},
            {"name": "ถุงมือผู้รักษาประตู Pro2 (สีฟ้า)", "price": "1,500฿", "img": "images/RRR.jpg", "category": "Reusch"},
            {"name": "ถุงมือผู้รักษาประตู Pro3 (สีส้ม)", "price": "1,800฿", "img": "images/pppppppp.jpg", "category": "NIKE"},
            {"name": "ถุงมือผู้รักษาประตู Pro4 (สีเขียว)", "price": "2,000฿", "img": "images/pppppp.jpg", "category": "ADIDAS"},
            {"name": "ถุงมือผู้รักษาประตู Elite", "price": "2,200฿", "img": "images/ppppp.jpg", "category": "PUMA"},
            {"name": "ถุงมือผู้รักษาประตู Champion (ลายใหม่)", "price": "2,500฿", "img": "images/pppp.jpg", "category": "Reusch"},
            {"name": "ถุงมือผู้รักษาประตู Supreme (ลายไฟ)", "price": "2,800฿", "img": "images/AAAA.jpg", "category": "NIKE"},
        ]
        for p in default_products:
            # (อัปเดต) เพิ่ม category
            cursor.execute("INSERT INTO products (name, price, img, category) VALUES (?, ?, ?, ?)", 
                           (p['name'], p['price'], p['img'], p.get('category', ''))) 
        conn.commit()
        cursor.execute("SELECT * FROM products")
        product_rows = cursor.fetchall()
        products = [dict(row) for row in product_rows]

    conn.close()
    return products

# ----------------------------------------------------------------------
# 🔑 ฟังก์ชันล็อกอินและรีเซ็ตรหัสผ่าน (แก้ไข)
# ----------------------------------------------------------------------

def login_user():
    global CURRENT_USER_DATA, root, entry_username, entry_password 
    
    if not entry_username or not entry_password:
        messagebox.showerror("ผิดพลาด", "Entry widgets ไม่ได้ถูกกำหนดค่า (Global error)")
        return

    username = entry_username.get()
    password = entry_password.get()
    
    if username == "admin" and password == "1234":
        CURRENT_USER_DATA = {"username": "admin", "full_name": "Administrator"} 
        messagebox.showinfo("สำเร็จ", "เข้าสู่ระบบในฐานะแอดมิน 🎉")
        root.destroy() 
        open_admin_dashboard()
        return

    user_data = load_user_by_username(username) 
    
    if not user_data:
        messagebox.showerror("ผิดพลาด", "ไม่พบชื่อผู้ใช้นี้ในระบบ ❌")
        return
        
    if password == user_data["password"]:
        CURRENT_USER_DATA = user_data 
        messagebox.showinfo("สำเร็จ", f"เข้าสู่ระบบสำเร็จ 🎉\nยินดีต้อนรับคุณ {user_data.get('full_name', username)}")
        root.destroy() 
        open_product_page()
    else:
        messagebox.showerror("ผิดพลาด", "รหัสผ่านไม่ถูกต้อง ❌")

def reset_password(fp_win, email_entry, username_entry, newpass_entry):
    input_email = email_entry.get().strip()
    input_username = username_entry.get().strip() 
    new_password = newpass_entry.get()

    user_data = load_user_for_reset(input_username, input_email) 

    if user_data:
        if not new_password:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกรหัสผ่านใหม่")
            return
            
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", 
                       (new_password, input_username))
        conn.commit()
        conn.close()
        
        messagebox.showinfo("สำเร็จ", "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว ✅\nกรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")
        fp_win.destroy()
    else:
        messagebox.showerror("ผิดพลาด", "ชื่อผู้ใช้ หรือ อีเมลไม่ถูกต้อง ❌")


def forgot_password_page():
    if not root or not root.winfo_exists():
        print("หน้าต่าง Login (root) ไม่ได้เปิดอยู่")
        return
        
    fp_win = tk.Toplevel(root) 
    fp_win.title("ลืมรหัสผ่าน | Goalkeeper Pro Shop")
    fp_win.geometry("450x450")
    fp_win.resizable(False, False)
    fp_win.configure(bg=THEME["bg_secondary"]) 
    
    tk.Label(fp_win, text="รีเซ็ตรหัสผ่าน", 
             font=FONT_HEADING, 
             fg=THEME["text_primary"], 
             bg=THEME["bg_secondary"]).pack(pady=20)
    
    label_style = {"bg": THEME["bg_secondary"], "fg": THEME["text_secondary"], "font": FONT_BODY} 
    entry_style = {"width": 35, "font": FONT_BODY, "relief": "flat", "bd": 0,
                   "bg": THEME["bg_list"], "fg": THEME["text_primary"], "insertbackground":THEME["text_primary"]}
                   
    tk.Label(fp_win, text="อีเมล", **label_style).pack(pady=(10, 3))
    entry_email_fp = tk.Entry(fp_win, **entry_style)
    entry_email_fp.pack(pady=3, ipady=4) 

    tk.Label(fp_win, text="ชื่อผู้ใช้ (Username)", **label_style).pack(pady=(10, 3))
    entry_username_fp = tk.Entry(fp_win, **entry_style)
    entry_username_fp.pack(pady=3, ipady=4) 
    
    tk.Label(fp_win, text="รหัสผ่านใหม่", **label_style).pack(pady=(10, 3))
    entry_new_pass_fp = tk.Entry(fp_win, show="•", **entry_style)
    entry_new_pass_fp.pack(pady=3, ipady=4) 
    
    tk.Button(fp_win, 
              text="ยืนยันการเปลี่ยนรหัส", 
              command=lambda: reset_password(fp_win, entry_email_fp, entry_username_fp, entry_new_pass_fp),
              bg=THEME["accent_red"], 
              fg=THEME["text_primary"], 
              font=FONT_BUTTON,
              width=25,
              relief="flat", bd=0).pack(pady=30, ipady=5) 
              
    fp_win.protocol("WM_DELETE_WINDOW", fp_win.destroy)

# ----------------------------------------------------------------------
# 👤 หน้าสมัครสมาชิก (Scrollable) (แก้ไขเล็กน้อย)
# ----------------------------------------------------------------------
def register_page():
    if not root or not root.winfo_exists():
        print("หน้าต่าง Login (root) ไม่ได้เปิดอยู่")
        return

    path_profile_pic = ""
    
    def upload_profile_pic():
        nonlocal path_profile_pic
        
        file_path = filedialog.askopenfilename(
            defaultextension=".jpg",
            filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )
        
        if file_path:
            path_profile_pic = file_path
            try:
                img = Image.open(path_profile_pic)
                img = img.resize((200, 200)) 
                
                photo = ImageTk.PhotoImage(img) 
                
                profile_pic_label.config(image=photo, width=200, height=200) 
                profile_pic_label.image = photo 
                profile_pic_label.config(text="")
                
                messagebox.showinfo("อัปโหลดสำเร็จ", "เลือกรูปโปรไฟล์เรียบร้อย")
            except Exception as e:
                profile_pic_label.config(text="[ไฟล์เสียหาย]", image=None, width=25, height=10)
                path_profile_pic = "" 
                messagebox.showerror("ผิดพลาด", f"ไม่สามารถโหลดภาพได้: {e}")
        else:
            pass 


    def register_user():
        full_name = entry_fullname.get()
        email = entry_email.get()
        new_user = entry_new_user.get()
        new_pass = entry_new_pass.get()
        phone = entry_phone.get() 
        address = entry_address.get("1.0", tk.END).strip() 
        
        if not (full_name and email and new_user and new_pass and phone and address): 
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกข้อมูลให้ครบถ้วน")
            return
        
        existing_user = load_user_by_username(new_user)
        if existing_user:
            messagebox.showwarning("แจ้งเตือน", "ชื่อผู้ใช้นี้ถูกใช้งานแล้ว กรุณาใช้ชื่ออื่น")
            return
            
        save_user( 
            username=new_user, 
            password=new_pass, 
            profile_pic_path=path_profile_pic,
            full_name=full_name,
            email=email,
            phone=phone, 
            address=address 
        ) 
        messagebox.showinfo("สำเร็จ", "สมัครสมาชิกเรียบร้อย ✅")
        reg_win.destroy()

    reg_win = tk.Toplevel(root) 
    reg_win.title("สมัครสมาชิก | Goalkeeper Pro Shop")
    reg_win.geometry("550x700") 
    reg_win.resizable(False, False)

    main_canvas = tk.Canvas(reg_win, highlightthickness=0, bg=THEME["bg_primary"]) 
    main_canvas.pack(side="left", fill="both", expand=True)
    
    v_scrollbar = tk.Scrollbar(reg_win, orient="vertical", command=main_canvas.yview)
    v_scrollbar.pack(side="right", fill="y")
    
    main_canvas.configure(yscrollcommand=v_scrollbar.set)
    
    scrollable_frame = tk.Frame(main_canvas, bg=THEME["bg_primary"]) 
    
    main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def on_frame_configure(event):
        main_canvas.configure(scrollregion=main_canvas.bbox("all"))

    scrollable_frame.bind("<Configure>", on_frame_configure)
    
    # ------------------- เนื้อหาแบบฟอร์ม -------------------
    form_frame = tk.Frame(scrollable_frame, 
                          bg=THEME["bg_secondary"], 
                          padx=30, 
                          pady=20, 
                          relief="raised", 
                          bd=4, 
                          highlightbackground="#5D6D7E", 
                          highlightthickness=2) 
    
    form_frame.pack(padx=80, pady=50) 
    
    tk.Label(form_frame, text="สมัครสมาชิก", 
             font=FONT_HEADING, 
             fg=THEME["text_primary"], 
             bg=THEME["bg_secondary"]).pack(pady=10) 

    profile_frame = tk.Frame(form_frame, bg=THEME["bg_secondary"])
    profile_frame.pack(pady=10)
    
    profile_pic_label = tk.Label(profile_frame, text="[No Image]", 
                                 bg=THEME["bg_list"], fg=THEME["text_primary"], 
                                 width=25, height=10, relief="ridge") 
    profile_pic_label.pack(side="top", pady=5)
    
    tk.Button(profile_frame, text="อัปโหลดรูปโปรไฟล์ 👤", command=upload_profile_pic,
              bg=THEME["accent_blue"], fg=THEME["text_primary"], 
              font=("Arial", 10, "bold"), width=20,
              relief="flat", bd=0).pack(side="top", pady=5, ipady=3) 

    label_style = {"bg": THEME["bg_secondary"], "fg": THEME["text_secondary"], "font": FONT_BODY} 
    entry_style = {"width": 35, "font": FONT_BODY, "relief": "flat", "bd": 0,
                   "bg": THEME["bg_list"], "fg": THEME["text_primary"], "insertbackground":THEME["text_primary"]}

    tk.Label(form_frame, text="ชื่อ - นามสกุล", **label_style).pack(pady=(10, 3))
    entry_fullname = tk.Entry(form_frame, **entry_style)
    entry_fullname.pack(pady=3, ipady=4) 

    tk.Label(form_frame, text="อีเมล", **label_style).pack(pady=(10, 3))
    entry_email = tk.Entry(form_frame, **entry_style)
    entry_email.pack(pady=3, ipady=4)
    
    tk.Label(form_frame, text="เบอร์โทรศัพท์ 📞", **label_style).pack(pady=(10, 3))
    entry_phone = tk.Entry(form_frame, **entry_style)
    entry_phone.pack(pady=3, ipady=4)

    tk.Label(form_frame, text="ที่อยู่จัดส่ง 🏠", **label_style).pack(pady=(10, 3))
    entry_address = tk.Text(form_frame, width=35, height=4, font=FONT_BODY,
                            relief="flat", bd=0, bg=THEME["bg_list"], fg=THEME["text_primary"], 
                            insertbackground=THEME["text_primary"])
    entry_address.pack(pady=3)

    tk.Label(form_frame, text="ชื่อผู้ใช้", **label_style).pack(pady=(10, 3))
    entry_new_user = tk.Entry(form_frame, **entry_style)
    entry_new_user.pack(pady=3, ipady=4)

    tk.Label(form_frame, text="รหัสผ่าน", **label_style).pack(pady=(10, 3))
    entry_new_pass = tk.Entry(form_frame, show="•", **entry_style)
    entry_new_pass.pack(pady=3, ipady=4)

    tk.Button(form_frame, text="สมัครสมาชิก", command=register_user,
              bg=THEME["accent_green"], 
              fg=THEME["text_primary"], 
              font=FONT_BUTTON,
              width=25,
              relief="flat", bd=0,
              activebackground="#27AE60", 
              activeforeground=THEME["text_primary"]).pack(pady=20, ipady=5) 
              
    reg_win.update_idletasks()
    main_canvas.config(scrollregion=main_canvas.bbox("all"))

    reg_win.protocol("WM_DELETE_WINDOW", reg_win.destroy)

# ----------------------------------------------------------------------
# 🛒 ฟังก์ชันสินค้าและตะกร้า (หน้าลูกค้า)
# ----------------------------------------------------------------------

def open_qr_code_page(parent_win, total_amount):
    qr_win = tk.Toplevel(parent_win)
    qr_win.title("ชำระเงิน | QR Code")
    qr_win.geometry("450x650")
    qr_win.resizable(False, False)
    qr_win.configure(bg="#F0F0F0")
    
    qr_win.transient(parent_win)
    qr_win.grab_set()
    
    slip_status = tk.StringVar(value="ยังไม่ได้อัปโหลดสลิป 📤")
    uploaded_file_path = "" 
    
    def upload_slip():
        nonlocal uploaded_file_path
        file_path = filedialog.askopenfilename(
            defaultextension=".jpg",
            filetypes=[("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*")]
        )
        
        if file_path:
            uploaded_file_path = file_path 
            file_name = os.path.basename(file_path)
            slip_status.set(f"สลิปที่เลือก: {file_name}")
            upload_label.config(fg="#4CAF50")
            messagebox.showinfo("อัปโหลดสำเร็จ", f"เลือกสลิป {file_name} เรียบร้อย")
        else:
            slip_status.set("ยังไม่ได้อัปโหลดสลิป 📤")
            upload_label.config(fg="red")

    tk.Label(qr_win, text="ชำระเงินและแจ้งสลิป", font=("Arial", 20, "bold"), bg="#F0F0F0").pack(pady=10)
    
    tk.Label(qr_win, text=f"ยอดรวมสุทธิ: {total_amount:,.2f} บาท", 
             font=("Arial", 14, "bold"), fg="#f44336", bg="#F0F0F0").pack(pady=5)

    try:
        img = Image.open("images/1187687d-6059-427f-96c5-fc5076921b7d.jpg") 
        img = img.resize((300, 300))
        qr_photo = ImageTk.PhotoImage(img)

        qr_label = tk.Label(qr_win, image=qr_photo, bg="#F0F0F0")
        qr_label.image = qr_photo
        qr_label.pack(pady=10)
    except FileNotFoundError:
        tk.Label(qr_win, text="❌ ไม่พบไฟล์ QR Code", fg="red", bg="#F0F0F0").pack(pady=10)
    
    upload_frame = tk.Frame(qr_win, bg="#F0F0F0")
    upload_frame.pack(pady=15)

    tk.Button(upload_frame, text="📸 อัปโหลดสลิป", command=upload_slip,
              bg="#1E88E5", fg="white", font=("Arial", 12, "bold"), width=15).pack(side="left", padx=10)

    upload_label = tk.Label(upload_frame, textvariable=slip_status, 
                            font=("Arial", 10), fg="red", bg="#F0F0F0")
    upload_label.pack(side="left", padx=5)

    def complete_payment():
        if not uploaded_file_path:
            messagebox.showwarning("แจ้งเตือน", "กรุณาอัปโหลดสลิปโอนเงินก่อน 🧾")
            return
            
        try:
            timestamp_str = time.strftime("%Y%m%d_%H%M%S")
            original_extension = os.path.splitext(uploaded_file_path)[1]
            
            slips_dir = "slips"
            new_relative_path = os.path.join(slips_dir, f"slip_{timestamp_str}{original_extension}")
            
            shutil.copy(uploaded_file_path, new_relative_path) 
            
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถบันทึกไฟล์สลิปได้: {e}")
            return

        save_order(total_amount, new_relative_path) 
            
        global cart
        global product_win
        
        cart = []
        
        messagebox.showinfo("เสร็จสิ้น", "แจ้งชำระเงินเรียบร้อยแล้ว ✅\nขอบคุณที่อุดหนุนครับ!")
        
        qr_win.destroy() 
        parent_win.destroy() 

        if product_win and product_win.winfo_exists():
            product_win.lift()
            product_win.focus_force()
        

    tk.Button(qr_win, text="ยืนยันการชำระเงิน", command=complete_payment,
              bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), width=25).pack(pady=15)
              
    tk.Label(qr_win, text="ขอบคุณที่อุดหนุนครับ! 🙏", font=("Arial", 12), bg="#F0F0F0").pack(pady=5)
    
#
# 🔽🔽🔽 (อัปเดตล่าสุด) ฟังก์ชันนี้ถูกยกเครื่องใหม่ทั้งหมด 🔽🔽🔽
#
def open_cart_page():
    if not cart:
        messagebox.showinfo("ตะกร้าว่าง", "ยังไม่มีสินค้าในตะกร้า 🛒")
        return

    global CURRENT_USER_DATA 

    cart_win = tk.Toplevel(product_win)
    cart_win.title("ตะกร้าสินค้าและยืนยันการสั่งซื้อ | Goalkeeper Pro Shop")
    cart_win.state('zoomed') 
    
    BG_COLOR = THEME["bg_primary"]
    SECONDARY_BG = THEME["bg_secondary"]
    LIST_BG = THEME["bg_list"]
    TEXT_COLOR = THEME["text_primary"]
    TEXT_SECONDARY = THEME["text_secondary"]
    
    cart_win.configure(bg=BG_COLOR)
    
    # (ใหม่) ตัวแปรสำหรับแสดงยอดรวม (เพื่ออัปเดต)
    subtotal_var = tk.StringVar()
    vat_var = tk.StringVar()
    grand_total_var = tk.StringVar()

    tk.Label(cart_win, text="🛍️ ตะกร้าสินค้าและยืนยันการสั่งซื้อ", 
             font=FONT_TITLE, 
             bg=BG_COLOR, 
             fg=TEXT_COLOR).pack(pady=20)

    main_cart_frame = tk.Frame(cart_win, bg=BG_COLOR)
    main_cart_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # --- 1. ส่วนซ้าย: ข้อมูลผู้ซื้อ ---
    user_info_frame = tk.Frame(main_cart_frame, bg=SECONDARY_BG, bd=2, relief="ridge", width=450)
    user_info_frame.pack(side="left", fill="y", padx=10, pady=10)
    user_info_frame.pack_propagate(False) 

    tk.Label(user_info_frame, text="ข้อมูลผู้สั่งซื้อ 👤", 
             font=FONT_HEADING, 
             bg=SECONDARY_BG, fg=TEXT_COLOR).pack(pady=15, padx=20, anchor="w")

    details_frame = tk.Frame(user_info_frame, bg=SECONDARY_BG)
    details_frame.pack(fill="x", padx=20, pady=5, anchor="n")

    tk.Label(details_frame, text="ชื่อ-นามสกุล:", 
             font=FONT_BUTTON, 
             bg=SECONDARY_BG, fg=TEXT_SECONDARY, anchor="w").pack(fill="x")
    tk.Label(details_frame, text=CURRENT_USER_DATA.get('full_name', 'N/A'), 
             font=FONT_BODY, 
             bg=SECONDARY_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", pady=(0, 15))

    tk.Label(details_frame, text="เบอร์โทรศัพท์:", 
             font=FONT_BUTTON, 
             bg=SECONDARY_BG, fg=TEXT_SECONDARY, anchor="w").pack(fill="x")
    tk.Label(details_frame, text=CURRENT_USER_DATA.get('phone', 'N/A'), 
             font=FONT_BODY, 
             bg=SECONDARY_BG, fg=TEXT_COLOR, anchor="w").pack(fill="x", pady=(0, 15))

    tk.Label(details_frame, text="ที่อยู่จัดส่ง:", 
             font=FONT_BUTTON, 
             bg=SECONDARY_BG, fg=TEXT_SECONDARY, anchor="w").pack(fill="x")
    
    address_text = tk.Text(details_frame, 
                           font=FONT_BODY, 
                           bg=SECONDARY_BG, fg=TEXT_COLOR, 
                           wrap=tk.WORD, height=5, bd=0, highlightthickness=0)
    address_text.insert(tk.END, CURRENT_USER_DATA.get('address', 'N/A'))
    address_text.config(state=tk.DISABLED) 
    address_text.pack(fill="x", pady=(0, 15))


    # --- 2. ส่วนขวา: รายการสินค้า ---
    list_container = tk.Frame(main_cart_frame, bg=BG_COLOR)
    list_container.pack(side="right", fill="both", expand=True, padx=10, pady=10)
    
    cart_canvas = tk.Canvas(list_container, bg=BG_COLOR, highlightthickness=0)
    v_scrollbar = tk.Scrollbar(list_container, orient="vertical", command=cart_canvas.yview)
    v_scrollbar.pack(side="right", fill="y")
    
    cart_canvas.pack(side="left", fill="both", expand=True)
    cart_canvas.configure(yscrollcommand=v_scrollbar.set)
    
    items_frame = tk.Frame(cart_canvas, bg=BG_COLOR)
    
    def on_items_frame_configure(event):
        cart_canvas.configure(scrollregion=cart_canvas.bbox("all"))

    items_frame_id = cart_canvas.create_window((0, 0), window=items_frame, anchor="nw")
    items_frame.bind("<Configure>", on_items_frame_configure) 

    def on_canvas_configure(event):
        canvas_width = event.width
        cart_canvas.itemconfigure(items_frame_id, width=canvas_width)

    cart_canvas.bind("<Configure>", on_canvas_configure) 
    
    # --- 3. ส่วนล่าง: ยอดรวมและปุ่ม ---
    bottom_frame = tk.Frame(cart_win, bg=BG_COLOR)
    bottom_frame.pack(fill="x", pady=20, padx=40)
    
    price_summary_frame = tk.Frame(bottom_frame, bg=BG_COLOR)
    price_summary_frame.pack(side="left", padx=20)

    tk.Label(price_summary_frame, text=f"ยอดรวม (Subtotal):", 
             font=FONT_BODY, 
             bg=BG_COLOR, 
             fg=TEXT_COLOR, anchor="e").pack(fill="x", anchor="e")
    tk.Label(price_summary_frame, textvariable=subtotal_var, # <--- (ใหม่)
             font=FONT_BODY, 
             bg=BG_COLOR, 
             fg=TEXT_COLOR, anchor="e").pack(fill="x", anchor="e")
             
    tk.Label(price_summary_frame, text=f"ภาษีมูลค่าเพิ่ม (VAT 7%):", 
             font=FONT_BODY, 
             bg=BG_COLOR, 
             fg=TEXT_COLOR, anchor="e").pack(fill="x", anchor="e")
    tk.Label(price_summary_frame, textvariable=vat_var, # <--- (ใหม่)
             font=FONT_BODY, 
             bg=BG_COLOR, 
             fg=TEXT_COLOR, anchor="e").pack(fill="x", anchor="e")

    tk.Label(price_summary_frame, text=f"ยอดรวมสุทธิ:", 
             font=FONT_HEADING, 
             bg=BG_COLOR, 
             fg=THEME["accent_orange"], anchor="e").pack(fill="x", anchor="e")
    tk.Label(price_summary_frame, textvariable=grand_total_var, # <--- (ใหม่)
             font=FONT_HEADING, 
             bg=BG_COLOR, 
             fg=THEME["accent_orange"], anchor="e").pack(fill="x", anchor="e")

    # (ใหม่) เก็บยอดรวมสุทธิสำหรับส่งไปหน้า QR
    current_grand_total = tk.DoubleVar()

    # (ใหม่) ปุ่มชำระเงิน
    pay_button = tk.Button(bottom_frame, text="ยืนยันการชำระเงิน", 
              bg=THEME["accent_green"], fg=TEXT_COLOR,
              font=FONT_HEADING, 
              relief="flat",
              pady=10, padx=20,
              command=lambda: open_qr_code_page(cart_win, current_grand_total.get()))
    pay_button.pack(side="right", padx=20)
    

    # --- 4. (ใหม่) ฟังก์ชันสำหรับสร้าง/ลบ/อัปเดต รายการในตะกร้า ---
    def rebuild_cart_display():
        global cart
        
        # ล้างของเก่าใน frame
        for widget in items_frame.winfo_children():
            widget.destroy()
            
        total_price = 0
        
        if not cart:
             tk.Label(items_frame, text="... ตะกร้าว่างเปล่า ...",
                      font=FONT_HEADING, bg=BG_COLOR, 
                      fg=TEXT_SECONDARY).pack(pady=50)

        # วาดใหม่
        for idx, item in enumerate(cart):
            price_str = item["price"].replace("฿", "").replace(",", "").strip()
            try:
                price_val = int(price_str)
                subtotal = price_val * item['quantity']
                total_price += subtotal
            except ValueError:
                price_val = 0
                subtotal = 0
                
            item_frame = tk.Frame(items_frame, bg=LIST_BG, bd=1, relief="ridge")
            item_frame.pack(fill="x", pady=5, padx=5) 
            
            left_details_frame = tk.Frame(item_frame, bg=LIST_BG)
            left_details_frame.pack(side="left", padx=10, pady=10, fill="x", expand=True)

            # (อัปเดต) แสดงไซส์
            tk.Label(left_details_frame, text=f"{item['name']} (Size: {item.get('size', 'N/A')})", 
                     bg=LIST_BG, fg=TEXT_COLOR, 
                     font=FONT_BUTTON, anchor="w").pack(fill="x")
            
            tk.Label(left_details_frame, text=f"({item['price']} / ชิ้น)", 
                     bg=LIST_BG, fg=TEXT_SECONDARY, 
                     font=FONT_BODY, anchor="w").pack(fill="x")

            right_details_frame = tk.Frame(item_frame, bg=LIST_BG)
            right_details_frame.pack(side="right", padx=10, pady=10)

            # (ใหม่) ปุ่ม <
            tk.Button(right_details_frame, text="<", 
                      font=("Arial", 10, "bold"), width=3, 
                      bg=THEME["bg_secondary"], fg=THEME["text_primary"], 
                      relief="flat", bd=0, 
                      activebackground=THEME["bg_list"],
                      command=lambda i=idx: decrement_cart_item(i) # <--- (ใหม่)
                      ).pack(side="left", ipady=2) 

            tk.Label(right_details_frame, text=f"x {item['quantity']}", 
                     bg=LIST_BG, fg=TEXT_COLOR, 
                     font=FONT_HEADING, width=4).pack(side="left", padx=10) # <--- (ใหม่) เพิ่ม width

            # (ใหม่) ปุ่ม >
            tk.Button(right_details_frame, text=">", 
                      font=("Arial", 10, "bold"), width=3,
                      bg=THEME["bg_secondary"], fg=THEME["text_primary"], 
                      relief="flat", bd=0,
                      activebackground=THEME["bg_list"], 
                      command=lambda i=idx: increment_cart_item(i) # <--- (ใหม่)
                      ).pack(side="left", ipady=2) 

            tk.Label(right_details_frame, text=f"รวม: {subtotal:,.0f}฿", 
                     bg=LIST_BG, fg=THEME["accent_orange"], 
                     font=FONT_BUTTON, width=10).pack(side="left", padx=20) # <--- (ใหม่) เพิ่ม width

            def remove_item(i=idx):
                cart.pop(i)
                rebuild_cart_display() # <--- (แก้ไข)

            tk.Button(right_details_frame, text="ลบ", 
                      bg=THEME["accent_red"], fg=TEXT_COLOR, 
                      command=remove_item, 
                      relief="flat", font=("Arial", 10, "bold")).pack(side="right", padx=10)
        
        # (ใหม่) อัปเดตยอดรวม
        subtotal_price = total_price
        vat_amount = subtotal_price * 0.07
        grand_total = subtotal_price + vat_amount
        
        subtotal_var.set(f"{subtotal_price:,.2f} ฿")
        vat_var.set(f"{vat_amount:,.2f} ฿")
        grand_total_var.set(f"{grand_total:,.2f} ฿")
        current_grand_total.set(grand_total) # เก็บค่าตัวเลข
        
        # (ใหม่) ปิด/เปิด ปุ่มชำระเงิน
        if not cart:
            pay_button.config(state=tk.DISABLED, bg=THEME["bg_list"])
        else:
            pay_button.config(state=tk.NORMAL, bg=THEME["accent_green"])

    # --- (ใหม่) 5. ฟังก์ชันสำหรับปุ่ม < > ---
    def increment_cart_item(index):
        global cart
        cart[index]['quantity'] += 1
        rebuild_cart_display()

    def decrement_cart_item(index):
        global cart
        cart[index]['quantity'] -= 1
        if cart[index]['quantity'] <= 0:
            cart.pop(index)
        rebuild_cart_display()
        
    # --- 6. โหลดครั้งแรก ---
    rebuild_cart_display()
    
    cart_win.protocol("WM_DELETE_WINDOW", cart_win.destroy)

#
# 🔽🔽🔽 (อัปเดตล่าสุด) ฟังก์ชันนี้ถูกแก้ไขให้เพิ่ม "เลือกไซส์" 🔽🔽🔽
#
def open_product_page():
    
    def increment_quantity(product_id):
        global product_quantity_vars
        current_qty = product_quantity_vars[product_id].get()
        product_quantity_vars[product_id].set(current_qty + 1)

    def decrement_quantity(product_id):
        global product_quantity_vars
        current_qty = product_quantity_vars[product_id].get()
        if current_qty > 0:
            product_quantity_vars[product_id].set(current_qty - 1)

    # (อัปเดต) ฟังก์ชันเพิ่มลงตะกร้า (รับ size_var)
    def add_product_to_cart(product_id, products_list, quantity_var, size_var):
        global cart
        
        quantity = quantity_var.get()
        size = size_var.get() # <--- (ใหม่)
        
        if quantity == 0:
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกจำนวนสินค้าอย่างน้อย 1 ชิ้น")
            return
            
        if size == "เลือกไซส์": # <--- (ใหม่)
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกไซส์")
            return

        # (อัปเดต) ค้นหาโดยใช้ id และ size
        existing_item = next((item for item in cart if item["id"] == product_id and item["size"] == size), None)
        product = next(p for p in products_list if p["id"] == product_id)
        
        if existing_item:
            existing_item["quantity"] += quantity
        else:
            cart_item = {
                "id": product["id"],
                "name": product["name"],
                "price": product["price"],
                "img": product["img"],
                "quantity": quantity,
                "size": size # <--- (ใหม่)
            }
            cart.append(cart_item)
            
        messagebox.showinfo("เพิ่มลงตะกร้า", f"เพิ่ม {product['name']} (ไซส์ {size}, จำนวน {quantity} ชิ้น) ลงตะกร้าแล้ว ✅")
        
        # (อัปเดต) รีเซ็ตทั้งคู่
        quantity_var.set(0)
        size_var.set("เลือกไซส์")

    def open_order_history_page():
        open_order_history(product_win) 

    def open_profile_page_local():
        open_profile_page(product_win)
        
    global product_win, product_quantity_vars, CURRENT_USER_DATA
    product_win = tk.Tk()
    product_win.title("สินค้า | Goalkeeper Pro Shop")
    product_win.state('zoomed') 
    
    CARD_BG_COLOR = THEME["bg_secondary"]
    CARD_WIDTH = 160 
    CARD_HEIGHT = 320 # <--- (อัปเดต) เพิ่มความสูง
    CARD_PADDING_X = 10

    product_win.configure(bg=THEME["bg_primary"])

    # Top Bar 
    top_bar = tk.Frame(product_win, bg=THEME["bg_secondary"], height=120) 
    top_bar.pack(fill="x")

    welcome_label = tk.Label(top_bar, text="🧤สินค้า Goalkeeper Pro Shop",
                             bg=THEME["bg_secondary"], 
                             fg=THEME["text_primary"], 
                             font=FONT_HEADING) 
    welcome_label.pack(side="left", padx=30, pady=30)
    
    
    tk.Button(top_bar, text="ดูตะกร้า 🛒", bg=THEME["accent_orange"], fg=THEME["text_primary"], 
              font=FONT_BUTTON,
              relief="flat",
              activebackground="#E67E22",
              command=open_cart_page).pack(side="right", padx=(10, 30), pady=30, ipady=5) 

    tk.Button(top_bar, text="คำสั่งซื้อของฉัน 🧾", bg=THEME["accent_blue"], fg=THEME["text_primary"], 
              font=FONT_BUTTON,
              relief="flat",
              activebackground="#2980B9",
              command=open_order_history_page).pack(side="right", padx=10, pady=30, ipady=5) 

    tk.Button(top_bar, text=f"👤 {CURRENT_USER_DATA.get('username', 'Profile')}", 
              bg=THEME["bg_list"], fg=THEME["text_primary"], 
              font=FONT_BUTTON,
              relief="flat",
              activebackground=THEME["accent_select"],
              command=open_profile_page_local 
              ).pack(side="right", padx=10, pady=30, ipady=5) 

    # (ใหม่) ตัวแปรสำหรับ Combobox
    category_var = tk.StringVar(value="All")
    
    # (ใหม่) กรอบสำหรับตัวกรอง (หมวดหมู่ + ค้นหา)
    filter_bar_frame = tk.Frame(top_bar, bg=THEME["bg_secondary"])
    filter_bar_frame.pack(fill="x", expand=True, padx=20) 
    
    tk.Label(filter_bar_frame, text="หมวดหมู่:", 
             font=FONT_BODY, bg=THEME["bg_secondary"], 
             fg=THEME["text_secondary"]).pack(side="left")
             
    category_combo = ttk.Combobox(filter_bar_frame, textvariable=category_var, 
                                  values=["All", "NIKE", "ADIDAS", "PUMA", "Reusch"], 
                                  width=12, font=FONT_BODY, state="readonly")
    category_combo.pack(side="left", padx=10)

    search_var = tk.StringVar()
    search_entry = tk.Entry(filter_bar_frame, textvariable=search_var, 
                            font=FONT_BODY, width=30,
                            bg=THEME["bg_list"], fg=THEME["text_primary"],
                            relief="flat", insertbackground=THEME["text_primary"])
    search_entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(10, 10))
    
    def search_and_filter():
        """(ใหม่) ฟังก์ชันที่เรียกโดยปุ่มค้นหาและ Enter"""
        populate_products(search_var.get(), category_var.get())
        
    search_button = tk.Button(filter_bar_frame, text="ค้นหา 🔎", 
                              font=FONT_BUTTON,
                              bg=THEME["accent_blue"], fg=THEME["text_primary"],
                              relief="flat", 
                              command=search_and_filter
                              )
    search_button.pack(side="right", ipady=2, padx=5)
    
    search_entry.bind("<Return>", lambda event: search_and_filter())
    
    # Main Frame และ Canvas
    main_frame = tk.Frame(product_win, bg=THEME["bg_primary"])
    main_frame.pack(fill="both", expand=True, padx=10, pady=(10, 60))

    canvas = tk.Canvas(main_frame, bg=THEME["bg_primary"], highlightthickness=0)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview) 
    canvas.configure(yscrollcommand=scrollbar.set)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    products_frame = tk.Frame(canvas, bg=THEME["bg_primary"])
    
    products_frame_window_id = canvas.create_window((0, 0), window=products_frame, anchor="nw")

    # (อัปเดต) ย้ายการสร้าง widget ทั้งหมดมาไว้ในฟังก์ชันนี้
    def populate_products(filter_term=None, filter_category="All"):
        global product_card_widgets, image_refs, product_quantity_vars
        
        # 1. ล้างของเก่า
        for widget in products_frame.winfo_children():
            widget.destroy()
            
        product_card_widgets.clear() 
        image_refs.clear()
        product_quantity_vars.clear() 

        # 2. โหลดและกรองข้อมูล
        products = load_products() 
        
        if filter_term:
            products = [p for p in products if filter_term.lower() in p['name'].lower()]
        
        if filter_category and filter_category != "All":
            products = [p for p in products if p.get('category') and p['category'].lower() == filter_category.lower()]
            
        if not products:
             tk.Label(products_frame, text="ไม่พบสินค้าที่ตรงกับการค้นหา",
                      font=FONT_HEADING, bg=THEME["bg_primary"], 
                      fg=THEME["text_secondary"]).pack(pady=50)

        # 3. (ย้ายมา) สร้างการ์ดสินค้าใหม่
        for p in products:
            product_id = p['id']
            
            if product_id not in product_quantity_vars:
                product_quantity_vars[product_id] = tk.IntVar(value=0)
            
            # (ใหม่) สร้าง size_var *เฉพาะ* ภายใน loop นี้
            size_var = tk.StringVar(value="เลือกไซส์")

            frame = tk.Frame(products_frame, bg=CARD_BG_COLOR, bd=2, relief="raised", 
                             width=CARD_WIDTH, height=CARD_HEIGHT,
                             highlightbackground="#5D6D7E", highlightthickness=1)
            
            frame.grid_propagate(False)

            try:
                img = Image.open(p["img"])
                img = img.resize((120, 120))
                photo = ImageTk.PhotoImage(img)
                image_refs.append(photo)
                tk.Label(frame, image=photo, bg=CARD_BG_COLOR).pack(pady=5)
            except:
                tk.Label(frame, text="[No Image]", bg=CARD_BG_COLOR, fg=THEME["accent_red"], height=8).pack(pady=5) 

            tk.Label(frame, text=p["name"], font=("Arial", 10, "bold"), 
                     bg=CARD_BG_COLOR, fg=THEME["text_primary"], 
                     wraplength=140).pack(pady=1)
            
            tk.Label(frame, text=p["price"], font=("Arial", 11), fg=THEME["accent_orange"], 
                     bg=CARD_BG_COLOR).pack(pady=1)
            
            # --- (ใหม่) เพิ่มช่องเลือกไซส์ ---
            size_frame = tk.Frame(frame, bg=CARD_BG_COLOR)
            size_frame.pack(pady=5)
            tk.Label(size_frame, text="ไซส์:", font=("Arial", 10), bg=CARD_BG_COLOR, fg=THEME["text_secondary"]).pack(side="left")
            size_combo = ttk.Combobox(size_frame, textvariable=size_var, 
                                      values=["6", "7", "8", "9", "10"], 
                                      width=8, font=("Arial", 10), state="readonly")
            size_combo.pack(side="left", padx=5)
            
            # --- (อัปเดต) ส่วนควบคุมจำนวนสินค้า (ปุ่มสีเทา) ---
            qty_frame = tk.Frame(frame, bg=THEME["bg_list"]) 
            qty_frame.pack(pady=5)
            
            tk.Button(qty_frame, text="<", 
                      font=("Arial", 10, "bold"), width=3, 
                      bg=THEME["bg_list"], fg=THEME["text_primary"], 
                      relief="flat", bd=0, 
                      activebackground=THEME["bg_secondary"], 
                      activeforeground=THEME["text_primary"],
                      command=lambda pid=product_id: decrement_quantity(pid)
                      ).pack(side="left", ipady=2) 

            tk.Label(qty_frame, textvariable=product_quantity_vars[product_id], 
                     font=("Arial", 10, "bold"), 
                     width=3, 
                     bg=THEME["bg_list"], 
                     fg=THEME["text_primary"]
                     ).pack(side="left", ipady=2) 

            tk.Button(qty_frame, text=">", 
                      font=("Arial", 10, "bold"), width=3,
                      bg=THEME["bg_list"], fg=THEME["text_primary"], 
                      relief="flat", bd=0,
                      activebackground=THEME["bg_secondary"], 
                      activeforeground=THEME["text_primary"],
                      command=lambda pid=product_id: increment_quantity(pid)
                      ).pack(side="left", ipady=2) 
            
            # (อัปเดต) ส่ง q_var และ s_var เข้าไป
            tk.Button(frame, text="เพิ่มลงตะกร้า", 
                      bg=THEME["accent_blue"], fg=THEME["text_primary"], 
                      font=("Arial", 11, "bold"),
                      relief="flat",
                      activebackground="#27AE60",
                      command=lambda pid=product_id, prod_list=products, q_var=product_quantity_vars[product_id], s_var=size_var: add_product_to_cart(pid, prod_list, q_var, s_var)
                      ).pack(pady=5, ipady=3) 
            
            product_card_widgets.append(frame) 
        
        # 4. (ใหม่) สั่งให้ reflow อัปเดตทันที
        products_frame.update_idletasks()
        canvas.update_idletasks()
        
        class DummyEvent:
            def __init__(self, width):
                self.width = width
        
        canvas_width = canvas.winfo_width()
        if canvas_width <= 1:
            canvas_width = product_win.winfo_width() - 50 
            
        reflow_products(DummyEvent(canvas_width)) 
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_frame_configure_for_scroll(event):
        """(ใหม่) อัปเดต Scrollregion เท่านั้น"""
        canvas.configure(scrollregion=canvas.bbox("all"))

    products_frame.bind("<Configure>", on_frame_configure_for_scroll)
    

    def reflow_products(event):
        """
        (อัปเดต) จัดเรียงสินค้าใหม่ (ที่อยู่ใน product_card_widgets)
        """
        canvas_width = event.width
        total_card_width = CARD_WIDTH + (CARD_PADDING_X * 2) 
        
        if canvas_width < total_card_width:
            new_columns = 1
        else:
            new_columns = canvas_width // total_card_width
        
        required_width = new_columns * total_card_width
        x_padding = (canvas_width - required_width) // 2
        if x_padding < 0:
            x_padding = 0
            
        canvas.coords(products_frame_window_id, x_padding, 0)
        
        current_cols = products_frame.grid_size()[0]
        for col_index in range(current_cols):
            products_frame.grid_columnconfigure(col_index, weight=0)
            
        for i, card_widget in enumerate(product_card_widgets):
            row = i // new_columns
            col = i % new_columns
            card_widget.grid(row=row, column=col, padx=CARD_PADDING_X, pady=10, sticky="n")

    canvas.bind("<Configure>", reflow_products) 

    def _on_mousewheel(event):
        if product_win.winfo_height() > products_frame.winfo_height():
             return
        if event.num == 5 or event.delta == -120:
            canvas.yview_scroll(1, "unit")
        if event.num == 4 or event.delta == 120:
            canvas.yview_scroll(-1, "unit")
    
    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    image_refs = []
    product_card_widgets = [] 
    product_quantity_vars.clear() 

    def logout_user_and_restart():
        product_win.destroy()
        start_login_page() 

    exit_btn = tk.Button(product_win, text="ออกจากระบบ", bg=THEME["accent_red"], fg=THEME["text_primary"], 
                         font=FONT_BUTTON, 
                         relief="flat",
                         command=logout_user_and_restart, 
                         activebackground="#C0392B")
    exit_btn.place(relx=1.0, rely=1.0, anchor="se", x=-10, y=-10)

    # (อัปเดต) เรียก populate_products() ครั้งแรก (แบบไม่กรอง)
    populate_products()

    product_win.mainloop()
    
#
# 🔽🔽🔽 (อัปเดตล่าสุด) นี่คือฟังก์ชันใหม่ทั้งหมดสำหรับหน้า "คำสั่งซื้อของฉัน" 🔽🔽🔽
#
def open_order_history(parent):
    """(ใหม่) สร้างหน้าต่างประวัติการสั่งซื้อของ User"""
    
    history_win = tk.Toplevel(parent)
    history_win.title("คำสั่งซื้อของฉัน | Goalkeeper Pro Shop")
    history_win.state('zoomed')
    history_win.configure(bg=THEME["bg_primary"])

    # 1. โหลดข้อมูลเฉพาะของ User นี้
    try:
        username = CURRENT_USER_DATA['username']
        user_orders = load_orders_by_user(username)
    except Exception as e:
        messagebox.showerror("Error", f"ไม่สามารถโหลดข้อมูลผู้ใช้ได้: {e}")
        history_win.destroy()
        return

    tk.Label(history_win, text="🧾 คำสั่งซื้อของฉัน", 
             font=FONT_TITLE, 
             bg=THEME["bg_primary"], 
             fg=THEME["text_primary"]).pack(pady=20)
             
    # --- สร้าง Canvas และ Scrollbar ---
    list_container = tk.Frame(history_win, bg=THEME["bg_primary"])
    list_container.pack(fill="both", expand=True, padx=30, pady=10)
    
    hist_canvas = tk.Canvas(list_container, bg=THEME["bg_primary"], highlightthickness=0)
    v_scrollbar = tk.Scrollbar(list_container, orient="vertical", command=hist_canvas.yview)
    v_scrollbar.pack(side="right", fill="y")
    
    hist_canvas.pack(side="left", fill="both", expand=True)
    hist_canvas.configure(yscrollcommand=v_scrollbar.set)
    
    # Frame ภายใน Canvas ที่จะบรรจุการ์ด
    orders_frame = tk.Frame(hist_canvas, bg=THEME["bg_primary"])
    
    def on_orders_frame_configure(event):
        hist_canvas.configure(scrollregion=hist_canvas.bbox("all"))

    orders_frame_id = hist_canvas.create_window((0, 0), window=orders_frame, anchor="n") 
    orders_frame.bind("<Configure>", on_orders_frame_configure) 

    def on_hist_canvas_configure(event):
        canvas_width = event.width
        target_width = min(canvas_width, 900) 
        frame_width = target_width
        x_pos = (canvas_width - frame_width) // 2
        if x_pos < 0:
            x_pos = 0
        hist_canvas.itemconfigure(orders_frame_id, width=target_width) 
        hist_canvas.coords(orders_frame_id, x_pos, 0)

    hist_canvas.bind("<Configure>", on_hist_canvas_configure) 
    
    def open_pdf_receipt(pdf_path):
        """(ใหม่) ฟังก์ชันสำหรับเปิด PDF"""
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("ไม่พบไฟล์", "ไม่พบไฟล์ PDF ใบเสร็จ\n(แอดมินยังไม่ได้ยืนยันออเดอร์นี้)")
            return
        
        try:
            if os.name == 'nt': # Windows
                os.startfile(pdf_path)
            else:
                webbrowser.open(pdf_path)
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"ไม่สามารถเปิดไฟล์ PDF ได้: {e}")

    # --- 2. วนลูปสร้างการ์ดออเดอร์ ---
    if not user_orders:
        tk.Label(orders_frame, text="คุณยังไม่มีคำสั่งซื้อ", 
                 font=FONT_HEADING, 
                 bg=THEME["bg_primary"], 
                 fg=THEME["text_secondary"]).pack(pady=50)
    
    for order in user_orders:
        card_frame = tk.Frame(orders_frame, bg=THEME["bg_secondary"], bd=2, relief="ridge") 
        card_frame.pack(pady=10, fill="x")

        card_frame.grid_columnconfigure(0, weight=1) 
        card_frame.grid_columnconfigure(1, weight=0) 

        # Frame ซ้าย: ข้อมูล
        left_frame = tk.Frame(card_frame, bg=THEME["bg_secondary"])
        left_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=15)
        
        # Frame ขวา: สถานะและปุ่ม
        right_frame = tk.Frame(card_frame, bg=THEME["bg_secondary"])
        right_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=15)

        # -- ข้อมูลด้านซ้าย --
        tk.Label(left_frame, text=f"Order ID: #{order['id']}", 
                 font=FONT_HEADING, 
                 bg=THEME["bg_secondary"], fg=THEME["text_primary"], anchor="w").pack(fill="x")
        
        tk.Label(left_frame, text=f"วันที่สั่งซื้อ: {order['timestamp']}", 
                 font=FONT_BODY, 
                 bg=THEME["bg_secondary"], fg=THEME["text_secondary"], anchor="w").pack(fill="x")
        
        tk.Label(left_frame, text=f"ยอดรวมสุทธิ: {order['total']:,.2f} ฿", 
                 font=FONT_BUTTON, 
                 bg=THEME["bg_secondary"], fg=THEME["accent_orange"], anchor="w").pack(fill="x", pady=5)
                 
        # -- ข้อมูลด้านขวา (สถานะและปุ่ม) --
        if order['status'] == "Confirmed":
            tk.Label(right_frame, text="✔ ยืนยันแล้ว", 
                     font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["accent_green"]).pack(pady=5)
            
            tk.Button(right_frame, text="ดูใบเสร็จ PDF", 
                      font=FONT_BUTTON,
                      bg=THEME["accent_blue"], fg=THEME["text_primary"],
                      relief="flat",
                      command=lambda p=order.get('receipt_path'): open_pdf_receipt(p)
                      ).pack(pady=5, ipady=5)
                      
        else: # "Pending"
            tk.Label(right_frame, text="⏳ รอดำเนินการ", 
                     font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["accent_orange"]).pack(pady=5)
            
            tk.Label(right_frame, text="(แอดมินกำลังตรวจสอบ)", 
                     font=FONT_BODY, 
                     bg=THEME["bg_secondary"], fg=THEME["text_secondary"]).pack(pady=5)

#
# 🔽🔽🔽 (อัปเดตล่าสุด) นี่คือฟังก์ชันใหม่สำหรับแสดงหน้าโปรไฟล์ 🔽🔽🔽
#
def open_profile_page(parent):
    """(อัปเดต) สร้างหน้าต่างแสดงข้อมูลโปรไฟล์ของ User (ดีไซน์ใหม่)"""
    
    global CURRENT_USER_DATA # เข้าถึงข้อมูลผู้ใช้ที่ล็อกอิน

    profile_win = tk.Toplevel(parent)
    profile_win.title(f"โปรไฟล์ของ {CURRENT_USER_DATA.get('username', '')}")
    profile_win.geometry("900x550") # <--- (แก้ไข) ปรับขนาด
    profile_win.configure(bg=THEME["bg_primary"])
    profile_win.resizable(True, True) # <--- (แก้ไข) ทำให้ปรับขนาดได้
    profile_win.transient(parent)
    profile_win.grab_set()

    tk.Label(profile_win, text="👤 โปรไฟล์ของฉัน", 
             font=FONT_TITLE, # <--- (แก้ไข) ใช้ฟอนต์ใหญ่
             bg=THEME["bg_primary"], 
             fg=THEME["text_primary"]).pack(pady=20)

    # (ใหม่) ใช้ PanedWindow เพื่อแบ่งหน้าจอ
    main_pane = tk.PanedWindow(profile_win, orient=tk.HORIZONTAL, bg=THEME["bg_primary"], sashrelief=tk.RAISED, sashwidth=4)
    main_pane.pack(fill="both", expand=True, padx=20, pady=10)

    # --- 1. ส่วนซ้าย (รูปภาพ) ---
    left_pane = tk.Frame(main_pane, bg=THEME["bg_secondary"], relief="ridge", bd=2)
    main_pane.add(left_pane, width=350) # กำหนดความกว้างเริ่มต้น
    left_pane.pack_propagate(False) # ไม่ให้ Frame หด

    profile_pic_label = tk.Label(left_pane, text="[No Image]", 
                                 bg=THEME["bg_list"], fg=THEME["text_primary"], 
                                 relief="ridge")
    profile_pic_label.pack(expand=True, padx=20, pady=20) # <--- (แก้ไข) ใช้ expand=True เพื่อจัดกลาง

    try:
        img_path = CURRENT_USER_DATA.get('path', '')
        if not img_path or not os.path.exists(img_path):
            raise FileNotFoundError("ไม่พบรูปโปรไฟล์")
            
        img = Image.open(img_path)
        img = img.resize((250, 250)) # <--- (แก้ไข) ขยายรูปให้ใหญ่ขึ้น
        photo = ImageTk.PhotoImage(img) 
        
        profile_pic_label.config(image=photo, text="", width=250, height=250) 
        profile_pic_label.image = photo 
    except Exception as e:
        print(f"Error loading profile pic: {e}")
        profile_pic_label.config(font=FONT_HEADING) # <--- (แก้ไข) ถ้าไม่มีรูป ให้ฟอนต์ใหญ่ขึ้น
        
    # --- 2. ส่วนขวา (ข้อมูล) ---
    right_pane = tk.Frame(main_pane, bg=THEME["bg_secondary"], relief="ridge", bd=2)
    main_pane.add(right_pane)

    # (ใหม่) ส่วนหัว (ชื่อ-นามสกุล และ Username)
    header_frame = tk.Frame(right_pane, bg=THEME["bg_secondary"])
    header_frame.pack(pady=(20, 10), padx=30, fill="x")

    tk.Label(header_frame, text=CURRENT_USER_DATA.get('full_name', 'N/A'), 
             font=FONT_TITLE, # <--- (ใหม่) ใช้ฟอนต์ใหญ่
             bg=THEME["bg_secondary"], fg=THEME["text_primary"],
             anchor="w"
             ).pack(fill="x")

    tk.Label(header_frame, text=f"@{CURRENT_USER_DATA.get('username', 'N/A')}", 
             font=FONT_HEADING, 
             bg=THEME["bg_secondary"], fg=THEME["text_secondary"], # <--- (ใหม่) ใช้สีรอง
             anchor="w"
             ).pack(fill="x")

    ttk.Separator(right_pane, orient=tk.HORIZONTAL).pack(fill="x", padx=20, pady=10)

    # (ใหม่) ส่วนรายละเอียด (Grid)
    details_frame = tk.Frame(right_pane, bg=THEME["bg_secondary"])
    details_frame.pack(fill="both", expand=True, padx=30, pady=10)

    # Helper styles
    label_style = {"font": FONT_BUTTON, "bg": THEME["bg_secondary"], "fg": THEME["text_secondary"], "anchor": "ne"}
    data_style = {"font": FONT_BODY, "bg": THEME["bg_secondary"], "fg": THEME["text_primary"], "anchor": "nw"}

    details_frame.grid_columnconfigure(0, weight=1) # คอลัมน์หัวข้อ
    details_frame.grid_columnconfigure(1, weight=3) # คอลัมน์ข้อมูล (ให้กว้างกว่า)

    # --- อีเมล ---
    tk.Label(details_frame, text="อีเมล:", **label_style).grid(row=0, column=0, sticky="ne", padx=10, pady=5)
    tk.Label(details_frame, text=CURRENT_USER_DATA.get('email', 'N/A'), **data_style).grid(row=0, column=1, sticky="nw", padx=10, pady=5)
    
    # --- เบอร์โทร ---
    tk.Label(details_frame, text="เบอร์โทร:", **label_style).grid(row=1, column=0, sticky="ne", padx=10, pady=5)
    tk.Label(details_frame, text=CURRENT_USER_DATA.get('phone', 'N/A'), **data_style).grid(row=1, column=1, sticky="nw", padx=10, pady=5)

    # --- ที่อยู่ (ใช้ Label แทน Text) ---
    tk.Label(details_frame, text="ที่อยู่:", **label_style).grid(row=2, column=0, sticky="ne", padx=10, pady=5)
    tk.Label(details_frame, text=CURRENT_USER_DATA.get('address', 'N/A'), 
             wraplength=400, # <--- (แก้ไข) ทำให้ตัดคำ
             justify=tk.LEFT,
             **data_style).grid(row=2, column=1, sticky="nw", padx=10, pady=5)

    # --- ปุ่มปิด ---
    tk.Button(right_pane, text="ปิดหน้าต่าง", 
              command=profile_win.destroy,
              font=FONT_BUTTON,
              bg=THEME["accent_red"], fg=THEME["text_primary"],
              relief="flat"
              ).pack(side="bottom", pady=20, ipady=5)

# ----------------------------------------------------------------------
# 📋 (ใหม่) ฟังก์ชันจัดการคำสั่งซื้อ (เชื่อมต่อ DB)
# ----------------------------------------------------------------------

def save_order(total_amount, slip_path):
    global CURRENT_USER_DATA
    username_to_save = CURRENT_USER_DATA.get('username', 'Unknown User')
    items_json = json.dumps(cart)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO orders (username, total, items_json, slip_path, status, timestamp, receipt_path)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username_to_save, total_amount, items_json, slip_path, "Pending", timestamp, None))
    conn.commit()
    conn.close()
        
def load_orders():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders ORDER BY id DESC") 
    order_rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for row in order_rows:
        order_dict = dict(row)
        try:
            order_dict['items'] = json.loads(order_dict['items_json'])
        except (json.JSONDecodeError, TypeError):
            order_dict['items'] = [] 
        orders.append(order_dict)
    return orders

# (ใหม่) โหลดออเดอร์เฉพาะ User
def load_orders_by_user(username):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE username = ? ORDER BY id DESC", (username,))
    order_rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for row in order_rows:
        order_dict = dict(row)
        try:
            order_dict['items'] = json.loads(order_dict['items_json'])
        except (json.JSONDecodeError, TypeError):
            order_dict['items'] = []
        orders.append(order_dict)
    return orders

def load_confirmed_orders():
    """(ใหม่) โหลดเฉพาะออเดอร์ที่ 'Confirmed' (สำหรับหน้า Sales Dashboard)"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM orders WHERE status = 'Confirmed'") 
    order_rows = cursor.fetchall()
    conn.close()
    
    orders = []
    for row in order_rows:
        order_dict = dict(row)
        try:
            order_dict['items'] = json.loads(order_dict['items_json'])
        except (json.JSONDecodeError, TypeError):
            order_dict['items'] = [] 
        orders.append(order_dict)
    return orders

def update_order_status(order_id, new_status, receipt_path=None):
    """(อัปเดต) อัปเดตสถานะและที่อยู่ไฟล์ PDF"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if receipt_path:
        cursor.execute("UPDATE orders SET status = ?, receipt_path = ? WHERE id = ?", 
                       (new_status, receipt_path, order_id))
    else:
        cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id))
        
    conn.commit()
    conn.close()


# ----------------------------------------------------------------------
# 👑 หน้าผู้ดูแลระบบ (Admin Dashboard) - (ปรับปรุงใหม่สำหรับ DB)
# ----------------------------------------------------------------------

def register_thai_font():
    """(ใหม่) ลงทะเบียนฟอนต์ไทยสำหรับ ReportLab"""
    global THAI_FONT_REGISTERED
    if THAI_FONT_REGISTERED:
        return True
        
    font_path = "Sarabun-Regular.ttf" 
    if not os.path.exists(font_path):
        messagebox.showerror("Font Error", 
                             f"ไม่พบไฟล์ฟอนต์ '{font_path}'\n"
                             "กรุณาดาวน์โหลดฟอนต์ Sarabun-Regular.ttf\n"
                             "แล้ววางไว้ในโฟลเดอร์เดียวกับโปรแกรม")
        return False
        
    try:
        pdfmetrics.registerFont(TTFont('ThaiFont', font_path))
        THAI_FONT_REGISTERED = True
        return True
    except Exception as e:
        messagebox.showerror("Font Error", f"ไม่สามารถลงทะเบียนฟอนต์ได้: {e}")
        return False

def generate_order_pdf(order_id):
    """(อัปเดต) สร้างไฟล์ PDF สำหรับออเดอร์ที่เลือก (แก้ไขบั๊ก)"""
    
    if not register_thai_font():
        return None 

    orders = load_orders() 
    order = next((o for o in orders if o['id'] == order_id), None)

    if not order:
        messagebox.showerror("Error", "ไม่พบข้อมูลออเดอร์")
        return None

    customer_username = order.get('username', '')
    user_data = load_user_by_username(customer_username) 
    
    pdf_filename = os.path.join("receipts", f"order_receipt_{order_id}.pdf")
    
    try:
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        width, height = A4
        
        # --- เริ่มเขียน PDF ---
        c.setFont('ThaiFont', 18)
        c.drawCentredString(width / 2.0, height - 1*inch, "ใบเสร็จรับเงิน / ใบสั่งซื้อ")
        
        c.setFont('ThaiFont', 12)
        c.drawString(inch, height - 1.5*inch, f"Goalkeeper Pro Shop")
        
        # ข้อมูลออเดอร์
        c.drawString(inch*5.5, height - 1.5*inch, f"Order ID: #{order['id']}")
        c.drawString(inch*5.5, height - 1.7*inch, f"วันที่: {order['timestamp']}")
        c.drawString(inch*5.5, height - 1.9*inch, f"สถานะ: {order['status']}")
        
        # ข้อมูลลูกค้า
        c.setFont('ThaiFont', 14)
        c.drawString(inch, height - 2.3*inch, "ข้อมูลลูกค้า:")
        c.setFont('ThaiFont', 12)
        
        text_object = c.beginText(inch * 1.2, height - 2.6*inch)
        text_object.setFont('ThaiFont', 12)
        text_object.textLine(f"ชื่อผู้ใช้: {order['username']}")
        text_object.textLine(f"ชื่อ-นามสกุล: {user_data.get('full_name', 'N/A')}")
        text_object.textLine(f"เบอร์โทร: {user_data.get('phone', 'N/A')}")
        text_object.textLine("ที่อยู่:")
        
        address_lines = user_data.get('address', 'N/A').split('\n')
        for line in address_lines:
             text_object.textLine(f"  {line.strip()}")
        c.drawText(text_object)
        
        # --- ตารางรายการสินค้า ---
        y = height - 4.5*inch
        c.setFont('ThaiFont', 14)
        c.drawString(inch, y, "รายการสินค้า")
        c.line(inch, y - 0.1*inch, width - inch, y - 0.1*inch)
        
        c.setFont('ThaiFont', 12)
        y -= 0.3*inch
        c.drawString(inch * 1.2, y, "ชื่อสินค้า")
        c.drawRightString(inch * 5.0, y, "จำนวน")
        c.drawRightString(inch * 6.2, y, "ราคา/หน่วย")
        c.drawRightString(inch * 7.5, y, "ราคารวม")
        
        y -= 0.1*inch

        for item in order['items']:
            y -= 0.3*inch
            price_str = item["price"].replace("฿", "").replace(",", "").strip()
            try:
                price_val = int(price_str)
                quantity = item.get('quantity', 1) 
                subtotal = price_val * quantity
            except ValueError:
                price_val = 0
                quantity = 1
                subtotal = 0
            
            # (อัปเดต) เพิ่ม Size
            item_name = f"{item['name']} (Size: {item.get('size', 'N/A')})"
            c.drawString(inch * 1.2, y, item_name)
            c.drawRightString(inch * 5.0, y, f"{quantity}")
            c.drawRightString(inch * 6.2, y, f"{price_val:,.0f} ฿")
            c.drawRightString(inch * 7.5, y, f"{subtotal:,.0f} ฿")

        # --- (อัปเดต) สรุปยอด (คำนวณ VAT ย้อนกลับ) ---
        y -= 0.3*inch
        c.line(inch * 4.5, y, width - inch, y) 
        y -= 0.3*inch
        
        grand_total = order['total']
        subtotal = grand_total / 1.07
        vat_amount = grand_total - subtotal

        c.setFont('ThaiFont', 12) 
        c.drawRightString(inch * 6.2, y, "ยอดรวม (Subtotal):")
        c.drawRightString(inch * 7.5, y, f"{subtotal:,.2f} ฿")
        y -= 0.3*inch

        c.drawRightString(inch * 6.2, y, "ภาษีมูลค่าเพิ่ม (VAT 7%):")
        c.drawRightString(inch * 7.5, y, f"{vat_amount:,.2f} ฿")
        y -= 0.3*inch
        
        c.setFont('ThaiFont', 14) 
        c.drawRightString(inch * 6.2, y, "ยอดรวมสุทธิ (Grand Total):")
        c.setFont('ThaiFont', 16) 
        c.drawRightString(inch * 7.5, y, f"{grand_total:,.2f} ฿")
        
        # --- (ใหม่) หน้าที่ 2: แสดงสลิป ---
        c.showPage()
        c.setFont('ThaiFont', 16)
        c.drawCentredString(width / 2.0, height - 1*inch, "สลิปการชำระเงิน (Payment Slip)")
        
        slip_path = order.get('slip_path', '')
        if slip_path and os.path.exists(slip_path):
            try:
                c.drawImage(ImageReader(slip_path), inch, height - 7*inch, 
                            width=width-(2*inch), preserveAspectRatio=True, anchor='n')
            except Exception as e:
                c.setFont('ThaiFont', 12)
                c.drawCentredString(width / 2.0, height / 2.0, f"ไม่สามารถแสดงไฟล์สลิปได้: {e}")
        else:
            c.setFont('ThaiFont', 12)
            c.drawCentredString(width / 2.0, height / 2.0, "ไม่พบไฟล์สลิป")
            
        c.save()
        return pdf_filename
    
    except Exception as e:
        messagebox.showerror("PDF Error", f"เกิดข้อผิดพลาดในการสร้าง PDF: {e}")
        return None

def build_product_management(parent):
    tk.Label(parent, text="จัดการสินค้า 📦", font=FONT_TITLE, fg=THEME["text_primary"], bg=THEME["bg_primary"]).pack(pady=20)
    
    main_pane = tk.PanedWindow(parent, orient=tk.HORIZONTAL, bg=THEME["bg_primary"], sashrelief=tk.RAISED, sashwidth=4)
    main_pane.pack(fill="both", expand=True, padx=20, pady=10)

    # --- 1. ส่วนซ้าย (รายการสินค้าและปุ่ม) ---
    left_pane_frame = tk.Frame(main_pane, bg=THEME["bg_primary"])
    main_pane.add(left_pane_frame, width=850) 

    tree_frame = tk.Frame(left_pane_frame, bg=THEME["bg_primary"])
    tree_frame.pack(pady=10, padx=10, fill="both", expand=True)

    # (อัปเดต) เพิ่ม category
    cols = ("id", "name", "price", "category", "image") 
    products_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=15)
    
    products_tree.heading("id", text="ID")
    products_tree.heading("name", text="ชื่อสินค้า")
    products_tree.heading("price", text="ราคา")
    products_tree.heading("category", text="หมวดหมู่") # (ใหม่)
    products_tree.heading("image", text="ไฟล์รูปภาพ")
    
    products_tree.column("id", width=50, anchor="center") 
    products_tree.column("name", width=350)
    products_tree.column("price", width=100, anchor="e") 
    products_tree.column("category", width=100, anchor="center") # (ใหม่)
    products_tree.column("image", width=200)
    
    scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=products_tree.yview)
    products_tree.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side="right", fill="y")
    products_tree.pack(side="left", fill="both", expand=True)

    btn_frame = tk.Frame(left_pane_frame, bg=THEME["bg_primary"])
    btn_frame.pack(pady=20)
    
    # --- 2. ส่วนขวา (พรีวิวรูปภาพ) ---
    right_pane_frame = tk.Frame(main_pane, bg=THEME["bg_secondary"], relief=tk.SUNKEN, bd=2)
    main_pane.add(right_pane_frame)

    tk.Label(right_pane_frame, text="พรีวิวรูปภาพ", 
             font=FONT_HEADING, 
             fg=THEME["text_primary"], 
             bg=THEME["bg_secondary"]).pack(pady=10)

    product_image_label = tk.Label(right_pane_frame, 
                                   text="[เลือกสินค้าเพื่อดูรูปภาพ]",
                                   font=FONT_BODY,
                                   fg=THEME["text_secondary"],
                                   bg=THEME["bg_list"],
                                   width=40, height=20,
                                   relief=tk.GROOVE)
    product_image_label.pack(pady=10, padx=20, fill="both", expand=True)

    product_name_label = tk.Label(right_pane_frame, 
                                  text="",
                                  font=FONT_BUTTON,
                                  fg=THEME["text_primary"], 
                                  bg=THEME["bg_secondary"],
                                  wraplength=280) 
    product_name_label.pack(pady=5, padx=10)


    # --- 3. ฟังก์ชันการทำงาน (เชื่อมต่อ DB) ---

    def refresh_product_list():
        for item in products_tree.get_children():
            products_tree.delete(item)
        
        products = load_products() 
        for p in products:
            img_name = os.path.basename(p['img']) if p.get('img') and os.path.exists(p.get('img', '')) else 'N/A'
            # (อัปเดต) เพิ่ม category
            products_tree.insert("", tk.END, iid=p['id'], 
                                 values=(p['id'], p['name'], p['price'], p.get('category', 'N/A'), img_name))
        
        product_image_label.config(image=None, text="[เลือกสินค้าเพื่อดูรูปภาพ]")
        product_image_label.image = None
        product_name_label.config(text="")


    def get_selected_product_id():
        selected_item = products_tree.focus() 
        if not selected_item:
            return None
        return int(selected_item) 

    def on_product_select(event):
        product_id = get_selected_product_id()
        if product_id is None:
            return

        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("SELECT name, img FROM products WHERE id = ?", (product_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                product_image_label.config(image=None, text="❌ ไม่พบข้อมูลสินค้า")
                product_image_label.image = None
                product_name_label.config(text="")
                return

            product_name, img_path = row
            product_name_label.config(text=product_name)

            try:
                img = Image.open(img_path)
                
                img.thumbnail((300, 300)) 
                
                photo = ImageTk.PhotoImage(img)
                
                product_image_label.config(image=photo, text="")
                product_image_label.image = photo 
            
            except FileNotFoundError:
                product_image_label.config(image=None, text="❌ ไม่พบไฟล์รูปภาพ")
                product_image_label.image = None
            except Exception as e:
                print(f"Error loading image: {e}")
                product_image_label.config(image=None, text="[ไม่สามารถแสดงรูปภาพ]")
                product_image_label.image = None

        except Exception as e:
            messagebox.showerror("Database Error", f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")

    products_tree.bind("<<TreeviewSelect>>", on_product_select)


    def add_product():
        name = simpledialog.askstring("เพิ่มสินค้า", "ชื่อสินค้า:")
        if not name: return
        price = simpledialog.askstring("เพิ่มสินค้า", "ราคาสินค้า (เช่น 1500฿):")
        if not price: return
        # (อัปเดต) เพิ่ม category
        category = simpledialog.askstring("เพิ่มสินค้า", "หมวดหมู่ (NIKE, ADIDAS, PUMA, Reusch):")
        if not category: category = "" # ถ้าไม่กรอก ให้เป็นค่าว่าง
        
        img = filedialog.askopenfilename(title="เลือกไฟล์รูปภาพสินค้า", filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        # (อัปเดต) เพิ่ม category
        cursor.execute("INSERT INTO products (name, price, img, category) VALUES (?, ?, ?, ?)", 
                       (name, price, img if img else "", category))
        conn.commit()
        conn.close()
        
        refresh_product_list()
        messagebox.showinfo("สำเร็จ", "เพิ่มสินค้าเรียบร้อย")

    def edit_price():
        product_id = get_selected_product_id()
        if product_id is None: 
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกสินค้าที่ต้องการแก้ไข")
            return
            
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        current_product = dict(cursor.fetchone())
        
        new_price = simpledialog.askstring("แก้ไขราคา", f"ราคาสินค้าใหม่สำหรับ {current_product['name']}:", initialvalue=current_product['price'])
        
        if new_price and new_price != current_product['price']:
            cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
            conn.commit()
            conn.close()
            refresh_product_list()
            messagebox.showinfo("สำเร็จ", "แก้ไขราคาเรียบร้อย")
        else:
            conn.close()

    # (ใหม่) ฟังก์ชันแก้ไขหมวดหมู่
    def edit_category():
        product_id = get_selected_product_id()
        if product_id is None: 
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกสินค้าที่ต้องการแก้ไข")
            return
        
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        current_product = dict(cursor.fetchone())
        
        new_category = simpledialog.askstring("แก้ไขหมวดหมู่", f"หมวดหมู่ใหม่สำหรับ {current_product['name']}:", initialvalue=current_product.get('category', ''))
        
        if new_category is not None and new_category != current_product.get('category', ''):
            cursor.execute("UPDATE products SET category = ? WHERE id = ?", (new_category, product_id))
            conn.commit()
            conn.close()
            refresh_product_list()
            messagebox.showinfo("สำเร็จ", "แก้ไขหมวดหมู่เรียบร้อย")
        else:
            conn.close()

    def delete_product():
        product_id = get_selected_product_id()
        if product_id is None: 
            messagebox.showwarning("แจ้งเตือน", "กรุณาเลือกสินค้าที่ต้องการลบ")
            return
            
        if messagebox.askyesno("ยืนยันการลบ", f"คุณแน่ใจหรือไม่ที่จะลบสินค้า ID: {product_id}?"):
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
            conn.commit()
            conn.close()
            
            refresh_product_list()
            messagebox.showinfo("สำเร็จ", "ลบสินค้าเรียบร้อย")

    # --- 4. ปุ่มควบคุม (แพ็คลงใน btn_frame) ---
    button_config = {
        "font": FONT_BUTTON,
        "fg": THEME["text_primary"],
        "relief": "flat",
        "width": 15,
        "pady": 5
    }

    tk.Button(btn_frame, text="+ เพิ่มสินค้า", command=add_product, bg=THEME["accent_green"], **button_config).pack(side="left", padx=5)
    tk.Button(btn_frame, text="แก้ไขราคา ✏️", command=edit_price, bg=THEME["accent_orange"], **button_config).pack(side="left", padx=5)
    tk.Button(btn_frame, text="แก้ไขหมวดหมู่ 🗂️", command=edit_category, bg=THEME["accent_orange"], **button_config).pack(side="left", padx=5) # (ใหม่)
    tk.Button(btn_frame, text="- ลบสินค้า 🗑️", command=delete_product, bg=THEME["accent_red"], **button_config).pack(side="left", padx=5)
    tk.Button(btn_frame, text="🔄 รีเฟรช", command=refresh_product_list, bg=THEME["accent_blue"], **button_config).pack(side="left", padx=5)

    refresh_product_list()

#
# 🔽🔽🔽 (อัปเดตล่าสุด) ฟังก์ชันนี้ถูกยกเครื่องใหม่ 🔽🔽🔽
#
def build_order_management(parent):
    """(อัปเดต) สร้าง UI สำหรับจัดการคำสั่งซื้อ (Card Layout)"""
    
    # --- Frame หลัก ---
    tk.Label(parent, text="จัดการคำสั่งซื้อ 📋", font=FONT_TITLE, fg=THEME["text_primary"], bg=THEME["bg_primary"]).pack(pady=20)
    
    # --- ปุ่ม Refresh (ย้ายมาไว้บนสุด) ---
    refresh_frame = tk.Frame(parent, bg=THEME["bg_primary"])
    refresh_frame.pack(fill="x", padx=20)
    
    # --- Canvas และ Scrollbar ---
    list_container = tk.Frame(parent, bg=THEME["bg_primary"])
    list_container.pack(fill="both", expand=True, padx=20, pady=10)
    
    order_canvas = tk.Canvas(list_container, bg=THEME["bg_primary"], highlightthickness=0)
    v_scrollbar = tk.Scrollbar(list_container, orient="vertical", command=order_canvas.yview)
    v_scrollbar.pack(side="right", fill="y")
    
    order_canvas.pack(side="left", fill="both", expand=True)
    order_canvas.configure(yscrollcommand=v_scrollbar.set)
    
    orders_frame = tk.Frame(order_canvas, bg=THEME["bg_primary"])
    
    def on_orders_frame_configure(event):
        order_canvas.configure(scrollregion=order_canvas.bbox("all"))

    orders_frame_id = order_canvas.create_window((0, 0), window=orders_frame, anchor="n")
    orders_frame.bind("<Configure>", on_orders_frame_configure) 

    def on_order_canvas_configure(event):
        canvas_width = event.width
        target_width = min(canvas_width, 900) 
        frame_width = target_width
        x_pos = (canvas_width - frame_width) // 2
        if x_pos < 0:
            x_pos = 0
        order_canvas.itemconfigure(orders_frame_id, width=target_width)
        order_canvas.coords(orders_frame_id, x_pos, 0)

    order_canvas.bind("<Configure>", on_order_canvas_configure) 

    # --- (ย้ายมาเป็น Inner Function) ฟังก์ชันสำหรับปุ่ม ---
    def view_details(order_id):
        orders = load_orders() 
        order = next((o for o in orders if o['id'] == order_id), None)

        if order:
            # (อัปเดต) ดีไซน์หน้าต่าง Pop-up
            detail_win = tk.Toplevel(parent)
            detail_win.title(f"รายละเอียดคำสั่งซื้อ #{order['id']}")
            detail_win.geometry("900x600") 
            detail_win.configure(bg=THEME["bg_primary"]) 
            
            main_pane = tk.PanedWindow(detail_win, orient=tk.HORIZONTAL, bg=THEME["bg_primary"], sashrelief=tk.RAISED, sashwidth=4)
            main_pane.pack(fill="both", expand=True, padx=10, pady=10)

            # --- (ใหม่) ส่วนซ้าย: รายละเอียด ---
            details_frame = tk.Frame(main_pane, bg=THEME["bg_secondary"])
            main_pane.add(details_frame, width=450)

            tk.Label(details_frame, text=f"รายละเอียดออเดอร์ #{order['id']}", font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(pady=15, padx=20)
            
            info_grid = tk.Frame(details_frame, bg=THEME["bg_secondary"])
            info_grid.pack(padx=20, pady=10, fill="x")
            
            info_labels = {
                "User:": order['username'],
                "ยอดรวม:": f"{order['total']:,.2f} ฿",
                "สถานะ:": order['status'],
                "เวลาสั่งซื้อ:": order['timestamp'],
                "ไฟล์สลิป:": os.path.basename(order.get('slip_path', 'N/A'))
            }
            
            for i, (key, value) in enumerate(info_labels.items()):
                tk.Label(info_grid, text=key, font=FONT_BUTTON, bg=THEME["bg_secondary"], fg=THEME["text_secondary"], anchor="w").grid(row=i, column=0, sticky="w", padx=5, pady=2)
                tk.Label(info_grid, text=value, font=FONT_BODY, bg=THEME["bg_secondary"], fg=THEME["text_primary"], anchor="w").grid(row=i, column=1, sticky="w", padx=5, pady=2)
            
            ttk.Separator(details_frame, orient=tk.HORIZONTAL).pack(fill="x", padx=20, pady=10)

            tk.Label(details_frame, text="รายการสินค้า", font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(pady=5, padx=20)
            
            items_list_frame = tk.Frame(details_frame, bg=THEME["bg_list"], relief="sunken", bd=1)
            items_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            for item in order['items']:
                # (อัปเดต) เพิ่ม Size
                item_text = f"- {item['name']} (Size: {item.get('size', 'N/A')}) (x{item.get('quantity', 1)}) ({item['price']})"
                tk.Label(items_list_frame, text=item_text, font=FONT_BODY, 
                         bg=THEME["bg_list"], fg=THEME["text_primary"], anchor="w", justify=tk.LEFT).pack(anchor="w", padx=10, pady=2)
            
            # --- (ใหม่) ส่วนขวา: สลิป ---
            slip_frame = tk.Frame(main_pane, bg=THEME["bg_secondary"])
            main_pane.add(slip_frame)

            tk.Label(slip_frame, text="หลักฐานการโอน (Slip)", font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(pady=15, padx=20)
            
            slip_preview_label = tk.Label(slip_frame, bg=THEME["bg_list"], relief="sunken", bd=2)
            slip_preview_label.pack(padx=20, pady=10, fill="both", expand=True)
            
            try:
                if not order.get('slip_path') or not os.path.exists(order['slip_path']):
                    raise FileNotFoundError("ไม่พบไฟล์สลิป")
                    
                slip_img = Image.open(order['slip_path']) 
                slip_img.thumbnail((400, 400)) 
                slip_photo = ImageTk.PhotoImage(slip_img)
                
                slip_preview_label.config(image=slip_photo, text="")
                slip_preview_label.image = slip_photo 
                
            except FileNotFoundError:
                slip_preview_label.config(image=None, text="❌ ไม่พบไฟล์สลิป", fg=THEME["accent_red"], font=FONT_HEADING)
            except Exception as e:
                print(e)
                slip_preview_label.config(image=None, text="❌ ไม่สามารถแสดงไฟล์สลิปได้", fg=THEME["accent_red"], font=FONT_HEADING)
            
            detail_win.transient(parent) 
            detail_win.grab_set() 

    def confirm_order(order_id, refresh_callback): 
        orders = load_orders() 
        order = next((o for o in orders if o['id'] == order_id), None)
        if order and order['status'] == "Confirmed":
            messagebox.showinfo("แจ้งเตือน", f"คำสั่งซื้อ ID: {order_id} ได้รับการยืนยันแล้ว")
            return
            
        try:
            pdf_filename = generate_order_pdf(order_id)
            if pdf_filename is None: 
                return 
            
            if os.name == 'nt': 
                os.startfile(pdf_filename)
            else:
                webbrowser.open(pdf_filename)
            
        except Exception as e:
            messagebox.showerror("PDF Error", f"ไม่สามารถสร้างหรือเปิด PDF ได้: {e}")
            return 

        if messagebox.askyesno("ยืนยันคำสั่งซื้อ", 
                                f"ระบบได้สร้างและเปิดใบเสร็จ (PDF) สำหรับ ID: {order_id} แล้ว\n\n"
                                "คุณได้ตรวจสอบ PDF และสลิปการโอนเงินเรียบร้อยแล้วใช่หรือไม่?"):
            
            update_order_status(order_id, "Confirmed", receipt_path=pdf_filename) 
            refresh_callback() 
            messagebox.showinfo("สำเร็จ", f"คำสั่งซื้อ ID: {order_id} ได้รับการยืนยันแล้ว ✅")
    
    # --- (ใหม่) ฟังก์ชันหลักสำหรับสร้าง Card ---
    def populate_orders_frame():
        # ล้างของเก่า
        for widget in orders_frame.winfo_children():
            widget.destroy()
            
        orders = load_orders() 

        if not orders:
            tk.Label(orders_frame, text="ยังไม่มีคำสั่งซื้อ", 
                     font=FONT_HEADING, 
                     bg=THEME["bg_primary"], 
                     fg=THEME["text_secondary"]).pack(pady=50)
            return

        for order in orders:
            order_id = order['id']
            card_frame = tk.Frame(orders_frame, bg=THEME["bg_secondary"], bd=2, relief="ridge")
            card_frame.pack(pady=10, fill="x")

            card_frame.grid_columnconfigure(0, weight=1) # ข้อมูล
            card_frame.grid_columnconfigure(1, weight=1) # สินค้า
            card_frame.grid_columnconfigure(2, weight=0) # สถานะ/ปุ่ม

            # Frame ซ้าย: ข้อมูล
            left_frame = tk.Frame(card_frame, bg=THEME["bg_secondary"])
            left_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
            
            # Frame กลาง: รายการสินค้า
            middle_frame = tk.Frame(card_frame, bg=THEME["bg_secondary"])
            middle_frame.grid(row=0, column=1, sticky="nsew", padx=15, pady=15)
            
            # Frame ขวา: สถานะและปุ่ม
            right_frame = tk.Frame(card_frame, bg=THEME["bg_secondary"])
            right_frame.grid(row=0, column=2, sticky="nsew", padx=15, pady=15)

            # -- ข้อมูลด้านซ้าย --
            tk.Label(left_frame, text=f"Order ID: #{order_id}", 
                     font=FONT_HEADING, 
                     bg=THEME["bg_secondary"], fg=THEME["text_primary"], anchor="w").pack(fill="x")
            
            tk.Label(left_frame, text=f"User: {order['username']}", 
                     font=FONT_BODY, 
                     bg=THEME["bg_secondary"], fg=THEME["text_secondary"], anchor="w").pack(fill="x")
                     
            tk.Label(left_frame, text=f"วันที่: {order['timestamp']}", 
                     font=FONT_BODY, 
                     bg=THEME["bg_secondary"], fg=THEME["text_secondary"], anchor="w").pack(fill="x")
            
            tk.Label(left_frame, text=f"ยอดรวม: {order['total']:,.2f} ฿", 
                     font=FONT_BUTTON, 
                     bg=THEME["bg_secondary"], fg=THEME["accent_orange"], anchor="w").pack(fill="x", pady=5)
            
            # -- ข้อมูลตรงกลาง (รายการสินค้า) --
            tk.Label(middle_frame, text="รายการสินค้า:", 
                     font=FONT_BUTTON, 
                     bg=THEME["bg_secondary"], fg=THEME["text_secondary"], anchor="w").pack(fill="x")
            
            items_summary = ""
            for item in order['items']:
                # (อัปเดต) เพิ่ม Size
                items_summary += f"- {item['name']} (Size: {item.get('size', 'N/A')}) (x{item.get('quantity', 1)})\n"
                
            tk.Label(middle_frame, text=items_summary.strip(), 
                     font=FONT_BODY, 
                     bg=THEME["bg_secondary"], fg=THEME["text_primary"], anchor="w", justify=tk.LEFT).pack(fill="x", pady=5)
                     
            # -- ข้อมูลด้านขวา (สถานะและปุ่ม) --
            btn_details = tk.Button(right_frame, text="ดูรายละเอียด / สลิป 📄", 
                                    font=FONT_BUTTON,
                                    bg=THEME["accent_blue"], fg=THEME["text_primary"],
                                    relief="flat",
                                    command=lambda o_id=order_id: view_details(o_id)
                                    )
            btn_details.pack(pady=5, ipady=5, fill="x")

            if order['status'] == "Confirmed":
                tk.Label(right_frame, text="✔ ยืนยันแล้ว", 
                         font=FONT_HEADING, 
                         bg=THEME["bg_secondary"], fg=THEME["accent_green"]).pack(pady=5)
                
                btn_confirm = tk.Button(right_frame, text="สร้าง PDF อีกครั้ง", 
                                        font=FONT_BUTTON,
                                        bg=THEME["bg_list"], fg=THEME["text_secondary"], # สีเทา
                                        relief="flat",
                                        command=lambda o_id=order_id: confirm_order(o_id, populate_orders_frame)
                                        )
                btn_confirm.pack(pady=5, ipady=5, fill="x")
                          
            else: # "Pending"
                tk.Label(right_frame, text="⏳ รอดำเนินการ", 
                         font=FONT_HEADING, 
                         bg=THEME["bg_secondary"], fg=THEME["accent_orange"]).pack(pady=5)
                
                btn_confirm = tk.Button(right_frame, text="✅ ยืนยันและสร้าง PDF", 
                                        font=FONT_BUTTON,
                                        bg=THEME["accent_green"], fg=THEME["text_primary"],
                                        relief="flat",
                                        command=lambda o_id=order_id: confirm_order(o_id, populate_orders_frame)
                                        )
                btn_confirm.pack(pady=5, ipady=5, fill="x")

    # --- ปุ่ม Refresh (ผูกคำสั่ง) ---
    tk.Button(refresh_frame, text="🔄 รีเฟรช", 
              command=populate_orders_frame, # <--- ผูกคำสั่ง
              bg=THEME["accent_blue"], fg=THEME["text_primary"],
              font=FONT_BUTTON, relief="flat",
              width=15, pady=5).pack(side="right", padx=10)
              
    # --- โหลดข้อมูลครั้งแรก ---
    populate_orders_frame()

#
# 🔽🔽🔽 (อัปเดตล่าสุด) ฟังก์ชันนี้ถูกแก้ไขให้เลือก วัน/เดือน/ปี 🔽🔽🔽
#
def build_sales_dashboard(parent):
    """(ใหม่) สร้างหน้า UI สำหรับสรุปยอดขาย"""
    
    # --- Frame หลัก ---
    tk.Label(parent, text="📈 สรุปยอดขายและสถิติ", font=FONT_TITLE, fg=THEME["text_primary"], bg=THEME["bg_primary"]).pack(pady=20)

    # --- (ใหม่) 1. Filter Frame ---
    filter_frame = tk.Frame(parent, bg=THEME["bg_secondary"], relief="ridge", bd=2)
    filter_frame.pack(fill="x", pady=10, padx=20)

    # --- ตัวเลือก Year ---
    tk.Label(filter_frame, text="ปี:", font=FONT_BUTTON, bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(side="left", padx=(20,5))
    year_options = ["All"] + [str(y) for y in range(datetime.now().year, 2022, -1)]
    year_var = tk.StringVar(value=str(datetime.now().year)) # ค่าเริ่มต้น
    year_combo = ttk.Combobox(filter_frame, textvariable=year_var, values=year_options, width=8, font=FONT_BODY, state="readonly")
    year_combo.pack(side="left", padx=5)

    # --- ตัวเลือก Month ---
    tk.Label(filter_frame, text="เดือน:", font=FONT_BUTTON, bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(side="left", padx=(20,5))
    month_options = ["All"] + [f"{m:02d} - {datetime(2000, m, 1).strftime('%B')}" for m in range(1, 13)]
    month_var = tk.StringVar(value=f"{datetime.now().month:02d} - {datetime.now().strftime('%B')}") # ค่าเริ่มต้น
    month_combo = ttk.Combobox(filter_frame, textvariable=month_var, values=month_options, width=15, font=FONT_BODY, state="readonly")
    month_combo.pack(side="left", padx=5)

    # --- ตัวเลือก Day ---
    tk.Label(filter_frame, text="วัน:", font=FONT_BUTTON, bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(side="left", padx=(20,5))
    day_options = ["All"] + [str(d) for d in range(1, 32)]
    day_var = tk.StringVar(value=str(datetime.now().day)) # ค่าเริ่มต้น
    day_combo = ttk.Combobox(filter_frame, textvariable=day_var, values=day_options, width=5, font=FONT_BODY, state="readonly")
    day_combo.pack(side="left", padx=5)

    
    # --- 2. Stats Box Frame (กล่องเดียว) ---
    stats_frame = tk.Frame(parent, bg=THEME["bg_primary"])
    stats_frame.pack(fill="x", pady=10, padx=20)
    
    stats_frame.columnconfigure(0, weight=1)
    
    # --- Column: Selected ---
    selected_frame = tk.Frame(stats_frame, bg=THEME["bg_secondary"], relief="ridge", bd=2)
    selected_frame.grid(row=0, column=0, sticky="nsew", padx=10)
    
    tk.Label(selected_frame, text="สรุปยอดขายตามที่เลือก (เฉพาะออเดอร์ที่ยืนยันแล้ว)", font=FONT_HEADING, bg=THEME["bg_secondary"], fg=THEME["text_primary"]).pack(pady=10)
    
    # (ใหม่) StringVars สำหรับกล่องสรุป
    selected_revenue_var = tk.StringVar(value="0.00 ฿")
    selected_orders_var = tk.StringVar(value="0 ออเดอร์")
    selected_items_var = tk.StringVar(value="0 ชิ้น")
    
    tk.Label(selected_frame, textvariable=selected_revenue_var, font=FONT_TITLE, bg=THEME["bg_secondary"], fg=THEME["accent_green"]).pack(pady=5)
    tk.Label(selected_frame, textvariable=selected_orders_var, font=FONT_BODY, bg=THEME["bg_secondary"], fg=THEME["text_secondary"]).pack(pady=5)
    tk.Label(selected_frame, textvariable=selected_items_var, font=FONT_BODY, bg=THEME["bg_secondary"], fg=THEME["text_secondary"]).pack(pady=(0, 10))

    
    # --- 3. Best-seller Frame ---
    tk.Label(parent, text="📊 สินค้ายอดนิยม (ตามที่เลือก)", 
             font=FONT_HEADING, 
             bg=THEME["bg_primary"], 
             fg=THEME["text_primary"]).pack(pady=(20, 10))
             
    tree_frame = tk.Frame(parent, bg=THEME["bg_primary"])
    tree_frame.pack(fill="both", expand=True, pady=10, padx=30)
    
    cols = ("rank", "name", "quantity")
    bestseller_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
    
    bestseller_tree.heading("rank", text="อันดับ")
    bestseller_tree.heading("name", text="ชื่อสินค้า")
    bestseller_tree.heading("quantity", text="จำนวนที่ขายได้ (ชิ้น)")
    
    bestseller_tree.column("rank", width=50, anchor="center")
    bestseller_tree.column("name", width=600)
    bestseller_tree.column("quantity", width=150, anchor="center")
    
    bestseller_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=bestseller_tree.yview)
    bestseller_tree.configure(yscrollcommand=bestseller_scrollbar.set)
    
    bestseller_scrollbar.pack(side="right", fill="y")
    bestseller_tree.pack(side="left", fill="both", expand=True)
    
    # --- 4. Data Processing Function ---
    def refresh_sales_data():
        # (อัปเดต) 1. ดึงค่าจากตัวกรอง
        sel_year = year_var.get()
        sel_month = month_var.get()
        sel_day = day_var.get()
        
        # (อัปเดต) 2. โหลดเฉพาะออเดอร์ที่ยืนยันแล้ว
        confirmed_orders = load_confirmed_orders() 
        
        # (อัปเดต) 3. กรองออเดอร์ตามที่เลือก
        filtered_orders = []
        product_sales = {} # สำหรับจัดอันดับ
        
        total_rev = 0
        total_itm = 0

        for order in confirmed_orders:
            try:
                order_date = datetime.strptime(order['timestamp'], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
                
            # กรองตามปี
            if sel_year != "All" and order_date.year != int(sel_year):
                continue
            
            # กรองตามเดือน
            if sel_month != "All" and order_date.month != int(sel_month.split(' ')[0]):
                continue

            # กรองตามวัน
            if sel_day != "All" and order_date.day != int(sel_day):
                continue
                
            # ถ้าผ่านตัวกรองทั้งหมด
            filtered_orders.append(order)
            
            # --- 4. คำนวณสถิติจากรายการที่กรองแล้ว ---
            total_rev += order['total']
            
            for item in order['items']:
                qty = item.get('quantity', 1)
                total_itm += qty
                product_sales[item['name']] = product_sales.get(item['name'], 0) + qty
                
        # --- 5. Update Labels (กล่องสรุป) ---
        selected_revenue_var.set(f"{total_rev:,.2f} ฿")
        selected_orders_var.set(f"{len(filtered_orders)} ออเดอร์")
        selected_items_var.set(f"{total_itm} ชิ้น")
        
        # --- 6. Update Treeview (สินค้ายอดนิยม) ---
        bestseller_tree.delete(*bestseller_tree.get_children())
        sorted_products = sorted(product_sales.items(), key=lambda item: item[1], reverse=True)
        
        for i, (name, quantity) in enumerate(sorted_products):
            rank = i + 1
            bestseller_tree.insert("", "end", values=(rank, name, quantity))
            
    # --- ปุ่ม Refresh/ค้นหา (ผูกคำสั่ง) ---
    tk.Button(filter_frame, text="ค้นหา 🔎", 
              command=refresh_sales_data, # <--- ผูกคำสั่ง
              bg=THEME["accent_green"], fg=THEME["text_primary"],
              font=FONT_BUTTON, relief="flat",
              width=15, pady=5).pack(side="left", padx=20, ipady=5) # (อัปเดต) ปรับสไตล์
            
    # --- Initial Load ---
    refresh_sales_data()


# ----------------------------------------------------------------------
# 👑 หน้าผู้ดูแลระบบหลัก (Admin Dashboard Container)
# ----------------------------------------------------------------------
def open_admin_dashboard():
    admin_root = tk.Tk() 
    admin_root.title("👑 ผู้ดูแลระบบ | Goalkeeper Pro Shop")
    admin_root.state('zoomed') 
    admin_root.configure(bg=THEME["bg_primary"])

    style = ttk.Style()
    style.theme_use("default")
    style.configure("Treeview",
                    background=THEME["bg_list"],
                    foreground=THEME["text_primary"],
                    fieldbackground=THEME["bg_list"],
                    rowheight=25,
                    font=FONT_TREEVIEW)
    style.configure("Treeview.Heading",
                    background=THEME["bg_secondary"],
                    foreground=THEME["text_primary"],
                    font=FONT_TREEVIEW_HEADING,
                    relief="flat")
    style.map("Treeview", background=[('selected', THEME["accent_select"])])
    style.map("Treeview.Heading", background=[('active', THEME["bg_secondary"])])

    nav_frame = tk.Frame(admin_root, bg=THEME["bg_secondary"], width=250)
    nav_frame.pack(side="left", fill="y")
    nav_frame.pack_propagate(False) 

    tk.Label(nav_frame, text="GOALKEEPER PRO", font=FONT_TITLE, fg=THEME["text_primary"], bg=THEME["bg_secondary"]).pack(pady=20, padx=10)

    content_frame = tk.Frame(admin_root, bg=THEME["bg_primary"])
    content_frame.pack(side="right", fill="both", expand=True)

    def load_frame(frame_builder):
        for widget in content_frame.winfo_children():
            widget.destroy()
        frame_builder(content_frame)

    nav_buttons = [
        ("📈 สรุปยอดขาย", lambda: load_frame(build_sales_dashboard)), 
        ("จัดการสินค้า 📦", lambda: load_frame(build_product_management)),
        ("จัดการคำสั่งซื้อ 📋", lambda: load_frame(build_order_management))
    ]
    
    button_nav_config = {
        "font": FONT_BUTTON,
        "bg": THEME["bg_secondary"],
        "fg": THEME["text_primary"],
        "relief": "flat",
        "anchor": "w", 
        "padx": 20,
        "pady": 10
    }

    for (text, command) in nav_buttons:
        btn = tk.Button(nav_frame, text=text, command=command, **button_nav_config)
        btn.pack(fill="x", pady=5, padx=10)
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=THEME["accent_blue"]))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=THEME["bg_secondary"]))

    def logout_admin_and_restart():
        admin_root.destroy()
        start_login_page() 

    logout_btn = tk.Button(nav_frame, text="ออกจากระบบ 🚪", 
                           command=logout_admin_and_restart, 
                           font=FONT_BUTTON, bg=THEME["bg_secondary"], fg=THEME["text_primary"],
                           relief="flat", anchor="w", padx=20, pady=10)
    logout_btn.pack(side="bottom", fill="x", pady=10, padx=10)
    logout_btn.bind("<Enter>", lambda e: e.widget.config(bg=THEME["accent_red"]))
    logout_btn.bind("<Leave>", lambda e: e.widget.config(bg=THEME["bg_secondary"]))

    load_frame(build_sales_dashboard)

    admin_root.mainloop()


# ----------------------------------------------------------------------
# 🚀 (ใหม่) ฟังก์ชันสำหรับเริ่มหน้า Login
# ----------------------------------------------------------------------
def start_login_page():
    """
    (ใหม่) สร้างและแสดงหน้าต่างล็อกอิน
    """
    global root, entry_username, entry_password 

    root = tk.Tk()
    root.title("Goalkeeper Pro Shop - Login")
    root.configure(bg=THEME["bg_primary"]) 
    root.state('zoomed') 
    
    # --- 1. เพิ่มพื้นหลังหลัก (เต็มจอ) ---
    try:
        image_path = "background_login.jpg" 
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        img = Image.open(image_path)

        if hasattr(Image, "Resampling"):
            resample_method = Image.Resampling.LANCZOS
        else:
            resample_method = Image.LANCZOS
            
        img = img.resize((screen_width, screen_height), resample_method)
        
        root.background_image = ImageTk.PhotoImage(img)
        
        bg_label = tk.Label(root, image=root.background_image)
        bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    except FileNotFoundError:
        print(f"ไม่พบไฟล์พื้นหลัง '{image_path}'. ใช้สีพื้นหลัง #2C3E50 แทน")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการโหลดพื้นหลัง: {e}")
    # --- จบส่วนพื้นหลังหลัก ---

    # ----------------------------------------------------------------------
    # 🚀 2. สร้าง Frame Login Box (กลับเป็นสีเทาทึบเหมือนเดิม)
    # ----------------------------------------------------------------------
    
    FRAME_BG_SOLID_COLOR = THEME["bg_secondary"] 
    
    main_login_frame = tk.Frame(root,
                                padx=40, pady=30,
                                relief="raised", bd=5, 
                                highlightbackground="#5D6D7E",
                                highlightthickness=2,
                                bg=FRAME_BG_SOLID_COLOR) 
    main_login_frame.pack(expand=True)
    
    # --- 3. วาง Widget เนื้อหา ---
    
    tk.Label(main_login_frame, text="🧤 Goalkeeper Pro Shop 🧤",
             font=FONT_TITLE, 
             fg=THEME["text_primary"],
             bg=FRAME_BG_SOLID_COLOR).pack(pady=(10, 20)) 

    tk.Label(main_login_frame, text="เข้าสู่ระบบ",
             font=FONT_HEADING, 
             fg=THEME["text_primary"],
             bg=FRAME_BG_SOLID_COLOR).pack(pady=10) 

    # --- ช่องกรอกข้อมูล ---
    label_style = {"bg": FRAME_BG_SOLID_COLOR, "fg": THEME["text_secondary"], "font": FONT_BODY} 
    entry_style = {"width": 30, "font": FONT_BODY, "relief": "flat", "bd": 0,
                   "bg": THEME["bg_list"], "fg": THEME["text_primary"], "insertbackground": THEME["text_primary"]}

    tk.Label(main_login_frame, text="ชื่อผู้ใช้:", **label_style).pack(pady=(10, 3))
    entry_username = tk.Entry(main_login_frame, **entry_style)
    entry_username.pack(pady=5, ipady=4)

    tk.Label(main_login_frame, text="รหัสผ่าน:", **label_style).pack(pady=(10, 3))
    entry_password = tk.Entry(main_login_frame, show="•", **entry_style)
    entry_password.pack(pady=5, ipady=4)

    # --- ปุ่ม ---
    button_frame = tk.Frame(main_login_frame, bg=FRAME_BG_SOLID_COLOR) 
    button_frame.pack(pady=20)

    tk.Button(button_frame, text="เข้าสู่ระบบ",
              command=login_user,
              bg=THEME["accent_green"], 
              fg=THEME["text_primary"],
              font=FONT_BUTTON,
              width=12,
              relief="flat", bd=0,
              activebackground="#27AE60").pack(side="left", padx=10, ipady=5)

    tk.Button(button_frame, text="สมัครสมาชิก",
              command=register_page,
              bg=THEME["accent_blue"], 
              fg=THEME["text_primary"],
              font=FONT_BUTTON,
              width=12,
              relief="flat", bd=0,
              activebackground="#2980B9").pack(side="left", padx=10, ipady=5)

    # --- ลืมรหัสผ่าน ---
    tk.Button(main_login_frame, text="ลืมรหัสผ่าน?",
              command=forgot_password_page,
              bg=FRAME_BG_SOLID_COLOR, 
              fg=THEME["accent_red"], 
              font=("Arial", 10, "underline"),
              relief="flat",
              activebackground=FRAME_BG_SOLID_COLOR, 
              activeforeground="#C0392B",
              bd=0).pack(pady=10)

    # รันหน้าต่างล็อกอิน
    root.mainloop()


# ----------------------------------------------------------------------
# 🚀 (แก้ไข) ส่วนสำหรับรันโปรแกรม
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # 1. รันฟังก์ชันสร้าง DB และ ตาราง ก่อน
    setup_database()
    
    # (ใหม่) สร้างโฟลเดอร์ที่จำเป็น
    os.makedirs("slips", exist_ok=True) 
    os.makedirs("images", exist_ok=True) 
    os.makedirs("receipts", exist_ok=True) # <--- (ใหม่) สร้างโฟลเดอร์เก็บใบเสร็จ
    
    # 2. เริ่มหน้าล็อกอิน
    start_login_page()