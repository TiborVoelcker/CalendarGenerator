__version__ = "1.0"

import logging
import os
import sys
from configparser import ConfigParser
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from babel.dates import format_date
from holidays.utils import country_holidays
from PIL import Image, ImageDraw, ImageFont

ANCHORS = Literal["lt", "lm", "lb", "mt", "mm", "mb", "rt", "rm", "rb"]


def resource_path(relative_path: str | os.PathLike) -> str:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base_path).joinpath(relative_path).resolve())


def scale_text(
    img: Image.Image,
    coords: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    scale: tuple[float, float] = (1, 1),
    anchor: ANCHORS = "lt",
    **kwargs,
):
    """Write text that is scalable."""
    l, t, r, b = font.getbbox(text)
    w, h = (r - l, b - t)
    temp_img = Image.new("RGBA", (w, h))

    ImageDraw.Draw(temp_img).text((-l, -t), text, font=font, **kwargs)

    new_size = (round(w * scale[0]), round(h * scale[1]))
    temp_img = temp_img.resize(new_size)

    a1, a2 = anchor
    x, y = coords
    w, h = temp_img.size
    if a1 == "l":
        pass
    elif a1 == "m":
        x = x - w / 2
    elif a1 == "r":
        x = x - w
    else:
        ValueError(f"bad anchor specified: {anchor}")
    if a2 == "t":
        pass
    elif a2 == "m":
        y = y - h / 2
    elif a2 == "b":
        y = y - h
    else:
        ValueError(f"bad anchor specified: {anchor}")

    logging.debug("Drawing %s at (%i, %i). Size: (%i, %i)", text, round(x), round(y), w, h)
    img.paste(temp_img, (round(x), round(y)), temp_img)


def main(year: int, output: Path):
    """Main function to generate borders for a full calendar."""

    def draw_month(month: date) -> Image.Image:
        """Draw the calendar border for this month."""
        logging.info("Drawing %s...", month.strftime("%B"))

        img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), color="white")  # create image
        d = ImageDraw.Draw(img)  # create drawing object

        # draw border
        border_coords = (BORDER, BORDER, CANVAS_WIDTH - BORDER, CANVAS_HEIGHT - BORDER_BOTTOM)
        d.rectangle(border_coords, fill=0)

        # draw month name
        footer_middle = CANVAS_HEIGHT - BORDER_BOTTOM / 2
        month_coords = (CANVAS_WIDTH - BORDER, footer_middle)
        scale_text(
            img,
            month_coords,
            format_date(month, "MMMM", locale="de_DE"),
            scale=(0.8, 1.4),
            fill=FONT_COLOR,
            font=fnt_big,
            anchor="rm",
        )

        # draw days
        drawn_holidays = []
        x = BORDER + DAYS_WIDTH / 2
        current_date = month.replace(day=1)
        while current_date.month == month.month:
            # make sundays and holidays bold
            font = fnt_bold if current_date in holidays_de or current_date.weekday() == 6 else fnt

            # save holidays for logging
            if font == fnt_bold:
                drawn_holidays.append(str(current_date.day))

            # draw day number
            scale_text(
                img,
                (x, footer_middle - DAYS_SPACING / 2),
                str(current_date.day),
                scale=(0.8, 1.4),
                fill=FONT_COLOR,
                font=font,
                anchor="mb",
            )
            # draw weekday
            scale_text(
                img,
                (x, footer_middle + DAYS_SPACING / 2),
                format_date(current_date, "E", locale="de_DE")[:-1].upper(),
                scale=(0.8, 1.4),
                fill=FONT_COLOR,
                font=font,
                anchor="mt",
            )
            x += DAYS_WIDTH
            current_date += timedelta(days=1)

        logging.info("Drawn holidays: %s", ", ".join(drawn_holidays))

        return img

    if not output.exists():
        logging.debug("Creating output directory %s", output)
        os.makedirs(output)
    elif not output.is_dir():
        logging.error("The provided path is not a directory")
        input("Press Enter to exit...")
        sys.exit(1)

    # config handeling
    config = ConfigParser(inline_comment_prefixes="#")
    logging.debug("Loading config file from '%s'...", resource_path("settings.ini"))
    config.read(resource_path("settings.ini"))

    font_file = resource_path(config["FONT"]["file"])
    font_file_bold = resource_path(config["FONT"]["file (bold)"])
    fnt = ImageFont.truetype(font_file, size=config["FONT"].getint("size"))
    fnt_bold = ImageFont.truetype(font_file_bold, size=config["FONT"].getint("size"))
    fnt_big = ImageFont.truetype(font_file_bold, size=config["FONT"].getint("size (big)"))

    FONT_COLOR = config["FONT"].get("color")
    CANVAS_WIDTH = config["CANVAS"].getint("width")
    CANVAS_HEIGHT = config["CANVAS"].getint("height")
    BORDER = config["BORDER"].getint("size")
    BORDER_BOTTOM = config.getint("BORDER", "size (bottom)")
    DAYS_SPACING = config["LAYOUT"].getint("days spacing")
    DAYS_WIDTH = config["LAYOUT"].getint("days width")

    # init holidays
    holidays_de = country_holidays(
        config["HOLIDAY"]["holiday country"], subdiv=config["HOLIDAY"]["holiday state"], years=year
    )

    for month in range(1, 13):
        img = draw_month(date(year, month, 1))
        img.save(output / f"{year}_{month}.png")

    input("Press Enter to exit...")
    sys.exit(0)


if __name__ == "__main__":

    def excepthook(exc_type, exc_value, traceback):
        exc_info = exc_type, exc_value, traceback
        if not issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            logging.error("Unhandled exception", exc_info=exc_info)

        input("Press Enter to exit...")
        sys.exit(1)

    sys.excepthook = excepthook

    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s: %(message)s")

    print(f"Calendar generator (Version: {__version__})")
    logging.debug("Python version: %s", sys.version)

    selected_year = date.today().year + 1
    selected_year = input(f"Enter year [{selected_year}]: ") or selected_year
    try:
        selected_year = int(selected_year)
    except ValueError as e:
        logging.error("Invalid year '%s'", selected_year)
        input("Press Enter to exit...")
        sys.exit(1)

    output_dir = Path.cwd() / "out"
    output_dir = input(f"Enter output folder [{output_dir}]: ") or output_dir
    try:
        output_dir = Path(output_dir)
    except ValueError as e:
        logging.error("Invalid output folder '%s'", output_dir)
        input("Press Enter to exit...")
        sys.exit(1)

    if any((output_dir / f"{selected_year}_{month}.png").exists() for month in range(1, 13)):
        ok = input("Some files will be overwritten! Continue?\nEnter (Y/N) [Y]: ") or "Y"
        if ok == "Y":
            pass
        elif ok == "N":
            logging.info("Cancelling.")
            input("Press Enter to exit...")
            sys.exit(1)
        else:
            logging.error("Invalid input. Cancelling.")
            input("Press Enter to exit...")
            sys.exit(1)

    main(selected_year, output_dir)
