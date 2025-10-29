from urllib.parse import quote

raw_key = "f0f851acdbf651d0d64c379c7179f6fb76b47d32a8ac6a7c42f4a76dce"
encoded_key = quote(raw_key, safe="")
print(encoded_key)