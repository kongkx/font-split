import sys
import os
import argparse
from typing import Tuple, List
from fontTools import ttLib
from fontTools.ttLib import TTFont
from fontTools.varLib.mutator import instantiateVariableFont
from fontTools.ttLib.tables._f_v_a_r import NamedInstance
from fontTools.ttLib.tables._n_a_m_e import NameRecord


def camelString(text: str):
    return text.replace(' ', '')

def sortNamingTable(names: List[NameRecord]) -> List[NameRecord]:
    """
    Parameters:
        names (List[NameRecord]): Naming table
    Returns:
        The sorted naming table.
        Based on FontConfig:
        - https://gitlab.freedesktop.org/fontconfig/fontconfig/-/blob/d863f6778915f7dd224c98c814247ec292904e30/src/fcfreetype.c#L1127-1140
    """

    def isEnglish(name: NameRecord) -> bool:
        # From: https://gitlab.freedesktop.org/fontconfig/fontconfig/-/blob/d863f6778915f7dd224c98c814247ec292904e30/src/fcfreetype.c#L1111-1125
        return (name.platformID, name.langID) in ((1, 0), (3, 0x409))

    # From: https://github.com/freetype/freetype/blob/b98dd169a1823485e35b3007ce707a6712dcd525/include/freetype/ttnameid.h#L86-L91
    PLATFORM_ID_APPLE_UNICODE = 0
    PLATFORM_ID_MACINTOSH = 1
    PLATFORM_ID_ISO = 2
    PLATFORM_ID_MICROSOFT = 3
    # From:	https://gitlab.freedesktop.org/fontconfig/fontconfig/-/blob/d863f6778915f7dd224c98c814247ec292904e30/src/fcfreetype.c#L1078
    PLATFORM_ID_ORDER = [
        PLATFORM_ID_MICROSOFT,
        PLATFORM_ID_APPLE_UNICODE,
        PLATFORM_ID_MACINTOSH,
        PLATFORM_ID_ISO,
    ]

    return sorted(names, key=lambda name: (PLATFORM_ID_ORDER.index(name.platformID), name.nameID, name.platEncID, -isEnglish(name), name.langID))


def getFirstDecodedName(nameID: int, names: List[NameRecord]) -> str:
    """
    Parameters:
        names (List[NameRecord]): Naming table
    Returns:
        The first decoded name.
    """

    names = sortNamingTable(names)

    for name in names:
        if name.nameID != nameID:
            continue
        try:
            unistr = name.toUnicode()
        except UnicodeDecodeError:
            continue

        return unistr

def splitNamedInstance(font: TTFont, output_dir: str) -> List[Tuple[str, str]]:
    """
    Parameters:
        font (TTFont): A font
    Returns:
        An dictionnary. The key is the font name and the value an NamedInstance
        The dictionnary support the R/B/I/BI family model: https://learn.microsoft.com/en-us/typography/opentype/spec/stat#alternate-font-family-models
    """

    if "fvar" not in font:
        raise Exception("The font is not an Variable Font.")

    # Read the note about the R/B/I/BI model: https://learn.microsoft.com/en-us/typography/opentype/spec/stat#alternate-font-family-models
    # INVALID_STYLE = ("regular", "bold", "italic", "oblique")

    family_name = getFirstDecodedName(16, font['name'].names)

    # If nameID 16 is None, try nameID 1https://learn.microsoft.com/en-us/typography/opentype/spec/otvaroverview#terminology
    if family_name is None:
        family_name = getFirstDecodedName(1, font['name'].names)

    instances_info: List[Tuple[str, str]] = []
    for instance in font["fvar"].instances:

        instance_name = getFirstDecodedName(instance.subfamilyNameID, font['name'].names)

        font_name = f"{family_name} {instance_name}"
        postscript_name = camelString(family_name) + '-' + camelString(instance_name)

        # instance_font = instantiateVariableFont(font, instance.coordinates)

        # name_table = instance_font['name']

        # langID: int
        # platformID: int
        # platEncID: int
        # # Take "Arial Black" as reference.
        # for record in name_table.names:
        #     if record.nameID == 1: # family name
        #         name_table.setName(font_name, record.nameID, record.platformID, record.platEncID, record.langID)
        #         platEncID = record.platEncID
        #         platformID = record.platformID
        #         langID = record.langID
        #     if record.nameID == 2: # style name
        #         name_table.setName('Regular', record.nameID, record.platformID, record.platEncID, record.langID)
        #     if record.nameID == 4: # full name
        #         name_table.setName(font_name, record.nameID, record.platformID, record.platEncID, record.langID)
        #     if record.nameID == 6: # PostScript Name
        #         name_table.setName(postscript_name, record.nameID, record.platformID, record.platEncID, record.langID)


        # name_table.setName(family_name, 16, platformID, platEncID, langID)
        # name_table.setName(instance_name, 17, platformID, platEncID, langID)

        # output_path = os.path.join(output_dir, f"{font_name}.ttf")
        # instance_font.save(output_path)

        # print(font_name + ' saved')
        instances_info.append((font_name, postscript_name))

    return instances_info

def generateSampleHtml(instances_info: List[Tuple[str, str]], output_dir: str):
    html_content = """
<!DOCTYPE html>
<html>
<head>
  <style>
  .example {
    font-size: 20px;
    margin-bottom: 16px;
  }
  </style>
</head>
<body>
"""

    for font_name, postscript_name in instances_info:
        html_content += f'  <div class="example" style="font-family:\'{font_name}\', \'{postscript_name}\'">{font_name}</div>\n'

    html_content += """
</body>
</html>
"""
    html_path = os.path.join(output_dir, "sample.html")
    with open(html_path, "w", encoding="utf-8") as html_file:
        html_file.write(html_content)

    print("Sample HTML generated at", html_path)


def main():

    parser = argparse.ArgumentParser(description='Process a variable font.')
    parser.add_argument('font_path', type=str, help='The path to the variable font file')
    parser.add_argument('output_dir', type=str, help='The directory to save the output font files')

    args = parser.parse_args()

    font_path = args.font_path
    output_dir = args.output_dir

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    font = ttLib.TTFont(font_path)

    names = splitNamedInstance(font, output_dir)

    generateSampleHtml(names, output_dir)


if __name__ == "__main__":
    sys.exit(main())
