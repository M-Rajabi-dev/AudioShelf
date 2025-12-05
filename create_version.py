# create_version.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import sys

COMPANY_NAME = "Mehdi Rajabi"
PRODUCT_NAME = "AudioShelf"
FILE_DESCRIPTION = "AudioShelf - Accessible Audiobook Player"
COPYRIGHT = "Copyright (c) 2025 Mehdi Rajabi"
INTERNAL_NAME = "AudioShelf.exe"
ORIGINAL_FILENAME = "AudioShelf.exe"

def generate_version_file(version_str):
    try:
        parts = [int(v) for v in version_str.split('.')]
        while len(parts) < 4:
            parts.append(0)
        ver_tuple = tuple(parts[:4])
    except:
        ver_tuple = (1, 0, 0, 0)
        version_str = "1.0.0.0"

    content = f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={ver_tuple},
    prodvers={ver_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'{COMPANY_NAME}'),
        StringStruct(u'FileDescription', u'{FILE_DESCRIPTION}'),
        StringStruct(u'FileVersion', u'{version_str}'),
        StringStruct(u'InternalName', u'{INTERNAL_NAME}'),
        StringStruct(u'LegalCopyright', u'{COPYRIGHT}'),
        StringStruct(u'OriginalFilename', u'{ORIGINAL_FILENAME}'),
        StringStruct(u'ProductName', u'{PRODUCT_NAME}'),
        StringStruct(u'ProductVersion', u'{version_str}')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    target_version = sys.argv[1] if len(sys.argv) > 1 else "1.0.0"
    generate_version_file(target_version)
