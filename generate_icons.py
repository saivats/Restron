from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

STATIC_DIR = Path(__file__).resolve().parent / "static"

BACKGROUND_COLOR = (13, 10, 6)
CIRCLE_COLOR = (232, 133, 26)
LETTER_COLOR = (13, 10, 6)


def generate_icon(size, output_path):
    img = Image.new("RGBA", (size, size), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)

    padding = int(size * 0.1)
    circle_bbox = [padding, padding, size - padding, size - padding]
    draw.ellipse(circle_bbox, fill=CIRCLE_COLOR)

    font_size = int(size * 0.5)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    text = "R"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (size - text_width) // 2
    text_y = (size - text_height) // 2 - text_bbox[1]

    draw.text((text_x, text_y), text, fill=LETTER_COLOR, font=font)

    img.save(output_path, "PNG")
    print(f"Generated {output_path}")


if __name__ == "__main__":
    generate_icon(192, STATIC_DIR / "icon-192.png")
    generate_icon(512, STATIC_DIR / "icon-512.png")
