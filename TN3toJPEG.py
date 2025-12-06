import os
from PIL import Image, ImageFilter, ImageEnhance

input_folder = r"c:\Users\ayoub\Documents\Master\Yasmina"
output_folder = os.path.join(input_folder, "mejoradas")
os.makedirs(output_folder, exist_ok=True)

scale_factor = 4

for filename in os.listdir(input_folder):
    if filename.endswith(".tn3"):
        input_path = os.path.join(input_folder, filename)
        output_filename = os.path.splitext(filename)[0] + ".jpg"
        output_path = os.path.join(output_folder, output_filename)

        try:
            img = Image.open(input_path).convert("RGB")
            w, h = img.size
            new_w = w * scale_factor
            new_h = h * scale_factor

            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            img_sharpened = img_resized.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            enhancer = ImageEnhance.Contrast(img_sharpened)
            img_final = enhancer.enhance(1.2)

            img_final.save(output_path, "JPEG")
            print(f"✅ Mejorado y guardado: {output_filename}")

        except Exception as e:
            print(f"❌ Error con {filename}: {e}")