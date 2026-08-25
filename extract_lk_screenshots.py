# -*- coding: utf-8 -*-
"""Извлекает скриншоты из PDF-инструкции ЛК (Сандов Фитнес/БАЗА-ЗНАНИЙ/
ИНСТРУКЦИИ-1С/Инструкция для ЛК.pdf) как отдельные PNG-файлы — по одному
на встроенное растровое изображение. Цены/названия тарифов на этих
скриншотах устарели (подтверждено Ольгой 25.08.2026), используются
только сами картинки интерфейса для наглядности шагов."""
import pymupdf
import os

SRC = r"D:\Проекты\Сандов Фитнес\БАЗА-ЗНАНИЙ\ИНСТРУКЦИИ-1С\Инструкция для ЛК.pdf"
OUT_DIR = r"D:\Проекты\sandow-wiki\lk_screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

doc = pymupdf.open(SRC)
count = 0
for page_num in range(len(doc)):
    page = doc[page_num]
    images = page.get_images(full=True)
    for img_index, img in enumerate(images):
        xref = img[0]
        base = doc.extract_image(xref)
        ext = base["ext"]
        data = base["image"]
        count += 1
        fname = f"p{page_num+1:02d}_img{img_index+1}.{ext}"
        path = os.path.join(OUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(data)
        print(f"{fname}: {len(data)} bytes, {base.get('width')}x{base.get('height')}")

print(f"\nВсего извлечено: {count} изображений в {OUT_DIR}")
