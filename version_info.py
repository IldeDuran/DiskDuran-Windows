"""Generate version info resource for PyInstaller."""

VERSION_INFO = """
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'OCiber'),
          StringStruct('FileDescription', 'DiskDuran - Analizador de disco'),
          StringStruct('FileVersion', '1.0.0.0'),
          StringStruct('InternalName', 'DiskDuran'),
          StringStruct('LegalCopyright', 'Copyright (c) 2024 OCiber'),
          StringStruct('OriginalFilename', 'DiskDuran.exe'),
          StringStruct('ProductName', 'DiskDuran'),
          StringStruct('ProductVersion', '1.0.0.0'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    with open("version_info.txt", "w") as f:
        f.write(VERSION_INFO.strip())
    print("version_info.txt generated")
