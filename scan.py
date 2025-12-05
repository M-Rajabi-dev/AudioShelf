import os

# اسم فایلی که لیست توش ذخیره میشه
output_file = "project_files.txt"

# پوشه هایی که نمیخوایم اسکن بشن (برای شلوغ نشدن لیست)
ignored_folders = {'.git', '.idea', '__pycache__', 'venv', 'env', 'dist', 'build', '.vscode'}

with open(output_file, "w", encoding="utf-8") as f:
    for root, dirs, files in os.walk("."):
        # حذف پوشه های مزاحم از لیست جستجو
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        
        for file in files:
            # نادیده گرفتن خود فایل اسکن و فایل خروجی
            if file in ["scan.py", output_file]:
                continue
                
            # ساخت آدرس نسبی فایل
            path = os.path.join(root, file)
            # حذف .\ اول آدرس برای تمیزی
            clean_path = path.replace(".\\", "")
            
            f.write(clean_path + "\n")

print(f"Done! List saved in {output_file}")