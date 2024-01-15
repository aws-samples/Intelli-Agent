# lite version of cleaning module refer to unstructure io
import re
from typing import Final, List

UNICODE_BULLETS: Final[List[str]] = [
    "\u0095",
    "\u2022",
    "\u2023",
    "\u2043",
    "\u3164",
    "\u204C",
    "\u204D",
    "\u2219",
    "\u25CB",
    "\u25CF",
    "\u25D8",
    "\u25E6",
    "\u2619",
    "\u2765",
    "\u2767",
    "\u29BE",
    "\u29BF",
    "\u002D",
    "",
    "\*",
    "\x95",
    "·",
]

BULLETS_PATTERN = "|".join(UNICODE_BULLETS)
UNICODE_BULLETS_RE = re.compile(f"(?:{BULLETS_PATTERN})(?!{BULLETS_PATTERN})")
# zero-width positive lookahead so bullet characters will not be removed when using .split()
UNICODE_BULLETS_RE_0W = re.compile(f"(?={BULLETS_PATTERN})(?<!{BULLETS_PATTERN})")
E_BULLET_PATTERN = re.compile(r"^e(?=\s)", re.MULTILINE)

REFERENCE_PATTERN = r"\[(?:[\d]+|[a-z]|[ivxlcdm])\]"
REFERENCE_PATTERN_RE = re.compile(REFERENCE_PATTERN)

ENUMERATED_BULLETS_RE = re.compile(r"(?:(?:\d{1,3}|[a-z][A-Z])\.?){1,3}")

PARAGRAPH_PATTERN = r"\s*\n\s*"  # noqa: W605 NOTE(harrell)

PARAGRAPH_PATTERN_RE = re.compile(
    f"((?:{BULLETS_PATTERN})|{PARAGRAPH_PATTERN})(?!{BULLETS_PATTERN}|$)",
)

DOUBLE_PARAGRAPH_PATTERN_RE = re.compile("(" + PARAGRAPH_PATTERN + "){2}")

def clean_non_ascii_chars(text) -> str:
    """Cleans non-ascii characters from unicode string.

    Example
    -------
    \x88This text contains non-ascii characters!\x88
        -> This text contains non-ascii characters!
    """
    en = text.encode("ascii", "ignore")
    return en.decode()

def clean_bullets(text: str) -> str:
    """Cleans unicode bullets from a section of text.

    Example
    -------
    ●  This is an excellent point! -> This is an excellent point!
    """
    search = UNICODE_BULLETS_RE.match(text)
    if search is None:
        return text

    cleaned_text = UNICODE_BULLETS_RE.sub("", text, 1)
    return cleaned_text.strip()

def clean_ordered_bullets(text) -> str:
    """Cleans the start of bulleted text sections up to three “sub-section”
    bullets accounting numeric and alphanumeric types.

    Example
    -------
    1.1 This is a very important point -> This is a very important point
    a.b This is a very important point -> This is a very important point
    """
    text_sp = text.split()
    text_cl = " ".join(text_sp[1:])
    if any(["." not in text_sp[0], ".." in text_sp[0]]):
        return text

    bullet = re.split(pattern=r"[\.]", string=text_sp[0])
    if not bullet[-1]:
        del bullet[-1]

    if len(bullet[0]) > 2:
        return text

    return text_cl

def clean_ligatures(text) -> str:
    """Replaces ligatures with their most likely equivalent characters.

    Example
    -------
    The beneﬁts -> The benefits
    High quality ﬁnancial -> High quality financial
    """
    ligatures_map = {
        "æ": "ae",
        "Æ": "AE",
        "ﬀ": "ff",
        "ﬁ": "fi",
        "ﬂ": "fl",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
        "ﬅ": "ft",
        "ʪ": "ls",
        "œ": "oe",
        "Œ": "OE",
        "ȹ": "qp",
        "ﬆ": "st",
        "ʦ": "ts",
    }
    cleaned_text: str = text
    for k, v in ligatures_map.items():
        cleaned_text = cleaned_text.replace(k, v)

    return cleaned_text

def group_bullet_paragraph(paragraph: str) -> list:
    """Groups paragraphs with bullets that have line breaks for visual/formatting purposes.
    For example:

    '''○ The big red fox
    is walking down the lane.

    ○ At the end of the lane
    the fox met a friendly bear.'''

    Gets converted to

    '''○ The big red fox is walking down the lane.
    ○ At the end of the land the fox met a bear.'''
    """
    clean_paragraphs = []
    # pytesseract converts some bullet points to standalone "e" characters.
    # Substitute "e" with bullets since they are later used in partition_text
    # to determine list element type.
    paragraph = (re.sub(E_BULLET_PATTERN, "·", paragraph)).strip()

    bullet_paras = re.split(UNICODE_BULLETS_RE_0W, paragraph)
    for bullet in bullet_paras:
        if bullet:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", bullet))
    return clean_paragraphs

def group_broken_paragraphs(
    text: str,
    line_split: re.Pattern[str] = PARAGRAPH_PATTERN_RE,
    paragraph_split: re.Pattern[str] = DOUBLE_PARAGRAPH_PATTERN_RE,
) -> str:
    """Groups paragraphs that have line breaks for visual/formatting purposes.
    For example:

    '''The big red fox
    is walking down the lane.

    At the end of the lane
    the fox met a bear.'''

    Gets converted to

    '''The big red fox is walking down the lane.
    At the end of the land the fox met a bear.'''
    """
    paragraphs = paragraph_split.split(text)
    clean_paragraphs = []
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
        # NOTE(robinson) - This block is to account for lines like the following that shouldn't be
        # grouped together, but aren't separated by a double line break.
        #     Apache License
        #     Version 2.0, January 2004
        #     http://www.apache.org/licenses/
        para_split = line_split.split(paragraph)
        all_lines_short = all(len(line.strip().split(" ")) < 5 for line in para_split)
        # pytesseract converts some bullet points to standalone "e" characters
        if UNICODE_BULLETS_RE.match(paragraph.strip()) or E_BULLET_PATTERN.match(paragraph.strip()):
            clean_paragraphs.extend(group_bullet_paragraph(paragraph))
        elif all_lines_short:
            clean_paragraphs.extend([line for line in para_split if line.strip()])
        else:
            clean_paragraphs.append(re.sub(PARAGRAPH_PATTERN, " ", paragraph))

    return "\n\n".join(clean_paragraphs)

def remove_duplicate_sections(text: str) -> str:
    # Split the text into paragraphs
    paragraphs = text.split('\n\n')

    # Function to remove punctuation from a string
    def remove_punctuation(s):
        no_punc = re.sub(r'[^\w\s]', '', s)
        # revmoe extra spaces between words
        normal = re.sub(r'\s+', ' ', no_punc)
        return normal.lower()

    # Remove punctuation and convert paragraphs to lower case for comparison
    cleaned_paragraphs = [remove_punctuation(p) for p in paragraphs]

    # Remove duplicate paragraphs (considering punctuation and case-insensitivity)
    unique_paragraphs = []
    seen = set()
    for original, cleaned in zip(paragraphs, cleaned_paragraphs):
        if cleaned not in seen:
            unique_paragraphs.append(original)
            seen.add(cleaned)

    # Join the unique paragraphs back into a single text
    cleaned_text = '\n\n'.join(unique_paragraphs)

    return cleaned_text