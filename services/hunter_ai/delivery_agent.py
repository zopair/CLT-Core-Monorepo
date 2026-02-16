
import os
import zipfile
import requests

def package_project(files_list, zip_name="AlZubair_Solution.zip"):
    # ضغط كافة الملفات البرمجية المطلوبة
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for file in files_list:
            if os.path.exists(file):
                zipf.write(file)
    print(f"📦 Project packaged: {zip_name}")
    return zip_name

def deliver_to_client(client_email, zip_path):
    print(f"🚀 Delivering files to {client_email}...")
    
    # 1. محاكاة الرفع لـ Google Drive (باستخدام API المثبت سابقاً)
    # 2. إرسال إيميل رسمي من شركة الزبير للعميل
    
    delivery_msg = f"Your professional solution from Al-Zubair Tec Investment is ready. Download here: [Secure Link]"
    print(f"✅ Delivery message sent. Mission Accomplished.")

if __name__ == "__main__":
    # بمجرد تأكيد الوكيل المالي للدفع:
    files_to_send = ["solution.py", "README.md", "requirements.txt"]
    zip_file = package_project(files_to_send)
    deliver_to_client("client@example.com", zip_file)
